"""Walk-forward e metriche di validazione.

Ogni previsione qui dentro proviene da un modello che ha visto solo partite
antecedenti. Questo include la scelta di alpha, che e' un iperparametro e non
puo' essere calibrato guardando l'intero campione: a ogni data si sceglie
l'alpha che ha funzionato meglio **fino a quel momento**.

Lo stesso vale per i **due parametri che trasformano lambda in probabilita'**:
la dispersione `r` della NB2 e il tasso base con cui si confronta il Brier
score. Fino alla Fase 2 entrambi erano stimati sull'intero campione valutato —
non entrano nella previsione puntuale, ma entrano nel Brier, quindi in senso
stretto quel Brier non era fuori campione. `walkforward_r` e
`walkforward_base_rate` li ricostruiscono riga per riga sul solo passato: la
Fase 4 riporta le due versioni affiancate, cosi' si vede quanto valeva la
scorciatoia invece di doverlo assumere.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import baselines as bl, config, dispersion, model_team, walkforward as wf

ALPHA_GRID = (1.0, 3.0, 6.0, 12.0, 25.0, 50.0)

# Nomi e soglie condivisi da Fase 4 e Fase 5: stanno qui perche' i due report
# devono per forza riferirsi alle stesse cose.
MODEL_NAME = "Poisson ridge att/dif/casa"
BEST_BASELINE = "media squadra + campo"
LINES = (2.5, 3.5, 4.5, 5.5)


# ---------------------------------------------------------------- walk-forward
def walkforward_predict(df: pd.DataFrame, extra: tuple[str, ...] = (),
                        alphas: tuple[float, ...] = ALPHA_GRID,
                        half_life: float = config.HALF_LIFE_DAYS,
                        burn_in: int = config.BURN_IN_ROUND,
                        target: str = bl.TARGET) -> pd.DataFrame:
    """Previsioni fuori campione per ogni riga, con alpha scelto in corsa.

    `target` esiste per il blocco E3 e vale `sot` di default: le Fasi 1-6 non
    passano il parametro e ottengono quello che ottenevano prima, con un test che
    lo verifica. La colonna del bersaglio esce **sempre col proprio nome**, mai
    rinominata in `sot`, cosi' che due tabelle con bersagli diversi non possano
    essere confuse a valle.
    """
    teams = sorted(set(df["team"]))
    parts = []

    for as_of, train, test in wf.date_splits(df):
        lam = {}
        for a in alphas:
            m = model_team.TeamModel(alpha=a, half_life=half_life, extra=extra,
                                     target=target)
            m.fit(train, as_of=as_of, teams=teams)
            lam[a] = m.predict(test)

        block = test[["matchId", "date", "team", "opponent", "is_home",
                      "team_match_idx", target]].copy()
        for a in alphas:
            block[f"lam_{a}"] = lam[a]
        parts.append(block)

    out = pd.concat(parts, ignore_index=True).sort_values("date").reset_index(drop=True)
    out["eligible"] = wf.eligible(out, burn_in)

    # --- scelta di alpha: cumulativa e solo sul passato ---
    ll = {a: dispersion.nb2_loglik(out[target].to_numpy(),
                                   out[f"lam_{a}"].to_numpy(),
                                   dispersion.R_MAX) for a in alphas}
    ll = pd.DataFrame(ll)
    ll.loc[~out["eligible"].to_numpy()] = 0.0

    # A ogni data si associa il cumulato delle date **precedenti**: la data
    # corrente non entra nella scelta del proprio alpha.
    by_date = ll.groupby(out["date"].to_numpy()).sum().sort_index()
    prior = by_date.cumsum().shift(1).fillna(0.0)
    best = prior.idxmax(axis=1)
    best[prior.sum(axis=1) == 0] = alphas[len(alphas) // 2]

    out["alpha"] = out["date"].map(best).astype(float)
    lam_cols = np.column_stack([out[f"lam_{a}"].to_numpy() for a in alphas])
    pick = np.searchsorted(np.array(alphas), out["alpha"].to_numpy())
    out["lam"] = lam_cols[np.arange(len(out)), pick]
    return out


def walkforward_baselines(df: pd.DataFrame,
                          burn_in: int = config.BURN_IN_ROUND,
                          target: str = bl.TARGET) -> pd.DataFrame:
    """Stessi split, stesse regole, per ogni baseline."""
    parts = []
    for _, train, test in wf.date_splits(df):
        block = test[["matchId", "date", "team", "team_match_idx", target]].copy()
        for name, fn in bl.BASELINES.items():
            block[name] = fn(train, test, target=target)
        parts.append(block)
    out = pd.concat(parts, ignore_index=True)
    out["eligible"] = wf.eligible(out, burn_in)
    return out


# ------------------------------------------- parametri stimati solo sul passato
MIN_PRIOR = 60          # righe minime prima di stimare r o il tasso base


def walkforward_r(y: np.ndarray, lam: np.ndarray, dates: pd.Series,
                  min_prior: int = MIN_PRIOR,
                  fallback: float = dispersion.R_MAX) -> np.ndarray:
    """Dispersione NB2 stimata, per ogni data, sulle sole partite precedenti.

    Finche' il passato non raggiunge `min_prior` righe si resta sulla Poisson
    (`r = R_MAX`): con poche decine di osservazioni la stima di r e' pessima e
    fingere di conoscerla sarebbe peggio che non usarla.
    """
    y = np.asarray(y, dtype=float)
    lam = np.asarray(lam, dtype=float)
    d = pd.Series(pd.to_datetime(np.asarray(dates))).to_numpy()

    order = np.argsort(d, kind="stable")
    out = np.full(len(y), float(fallback))
    uniq = np.unique(d)

    for day in uniq:
        prior = order[d[order] < day]
        if len(prior) < min_prior:
            continue
        out[d == day] = dispersion.fit_r(y[prior], lam[prior])
    return out


def walkforward_base_rate(y: np.ndarray, dates: pd.Series,
                          line: float = config.OVER_LINE) -> np.ndarray:
    """Tasso base dell'evento Over, calcolato sulle sole partite precedenti.

    Il tasso base e' l'avversario del Brier score. Prenderlo dall'intero
    campione lo rende un avversario che conosce il futuro: piu' forte del
    dovuto, quindi conservativo per noi, ma comunque non fuori campione.

    Si usa sempre e solo il passato disponibile, per corto che sia; senza alcun
    precedente si usa 0.5, il valore non informativo. In nessun caso si ricade
    sulla media dell'intero campione.
    """
    y_bin = (np.asarray(y, dtype=float) > line).astype(float)
    d = pd.Series(pd.to_datetime(np.asarray(dates))).to_numpy()

    order = np.argsort(d, kind="stable")
    out = np.full(len(y_bin), 0.5)
    for day in np.unique(d):
        prior = order[d[order] < day]
        if len(prior):
            out[d == day] = y_bin[prior].mean()
    return out


# --------------------------------------------------------------------- metriche
def calibration_slope(y: np.ndarray, lam: np.ndarray) -> tuple[float, float]:
    """Pendenza di calibrazione con errore standard.

    Si stima la Poisson  log(mu) = a + b * log(lambda)  per Newton-Raphson.
    Un modello calibrato ha b = 1: b < 1 significa previsioni troppo estreme,
    b > 1 troppo compresse. L'errore standard viene dall'informazione di
    Fisher, il che permette il test contro 1.0.

    Con `lambda` costante la pendenza **non e' identificata** — non c'e' alcuna
    variazione su cui stimarla — e si ritorna `nan` invece di un numero
    prodotto da una matrice singolare. Attenzione: un lambda quasi costante da'
    un numero, ma con un errore standard enorme; va letto guardando anche la
    sharpness, non solo la pendenza.
    """
    y = np.asarray(y, dtype=float)
    z = np.log(np.clip(np.asarray(lam, dtype=float), 1e-9, None))
    if np.std(z) < 1e-12:
        return float("nan"), float("nan")

    Z = np.column_stack([np.ones(len(y)), z])
    b = np.array([0.0, 1.0])
    for _ in range(100):
        mu = np.exp(np.clip(Z @ b, -20, 20))
        g = Z.T @ (y - mu)
        H = Z.T @ (Z * mu[:, None])
        step = np.linalg.solve(H, g)
        b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    mu = np.exp(np.clip(Z @ b, -20, 20))
    cov = np.linalg.inv(Z.T @ (Z * mu[:, None]))
    return float(b[1]), float(np.sqrt(cov[1, 1]))


def brier(y_bin: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p) - np.asarray(y_bin, dtype=float)) ** 2))


REL_EDGES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0)


def reliability_table(y_bin: np.ndarray, p: np.ndarray,
                      edges=REL_EDGES) -> pd.DataFrame:
    """Tabella di affidabilita' per fasce di probabilita'.

    `se` e' l'errore standard binomiale della frequenza osservata: senza, uno
    scarto di 0.08 su una fascia da 30 partite si legge come miscalibrazione
    quando e' solo rumore. `z` e' lo scarto in unita' di errore standard.
    """
    df = pd.DataFrame({"p": np.asarray(p, dtype=float),
                       "y": np.asarray(y_bin, dtype=float)})
    df["bin"] = pd.cut(df["p"], list(edges), include_lowest=True)
    out = df.groupby("bin", observed=True).agg(
        n=("y", "size"), p_mean=("p", "mean"), freq=("y", "mean")).reset_index()
    out["diff"] = out["freq"] - out["p_mean"]
    out["se"] = np.sqrt(out["p_mean"] * (1 - out["p_mean"]) / out["n"])
    out["z"] = out["diff"] / out["se"].replace(0.0, np.nan)
    return out


def ece(y_bin: np.ndarray, p: np.ndarray, edges=REL_EDGES) -> float:
    """Errore di calibrazione atteso: |frequenza - probabilita'| pesato per n.

    Va letto **sempre** accanto al Brier: un modello che prevede il tasso base
    a tutti ha ECE quasi nullo ed e' inutile. L'ECE misura la calibrazione, non
    l'informativita'; la seconda sta nella risoluzione qui sotto.
    """
    t = reliability_table(y_bin, p, edges)
    return float(np.sum(t["n"] * t["diff"].abs()) / t["n"].sum())


def brier_decomposition(y_bin: np.ndarray, p: np.ndarray,
                        edges=REL_EDGES) -> dict:
    """Scomposizione di Murphy: Brier = affidabilita' - risoluzione + incertezza.

    * **affidabilita'** (piu' bassa e' meglio): quanto le frequenze osservate si
      scostano dalle probabilita' dichiarate. E' l'errore che si corregge
      ricalibrando.
    * **risoluzione** (piu' alta e' meglio): quanto le fasce di probabilita' si
      separano dal tasso base. E' l'unica parte che misura se il modello sa
      qualcosa; un baseline costante ha risoluzione zero per costruzione.
    * **incertezza**: varianza dell'evento, uguale per tutti i modelli sullo
      stesso campione. Non e' un merito ne' un demerito.

    L'identita' e' esatta solo a probabilita' discretizzate in fasce: `residuo`
    riporta lo scarto dovuto al binning, che va controllato prima di leggere i
    tre termini.
    """
    y_bin = np.asarray(y_bin, dtype=float)
    p = np.asarray(p, dtype=float)
    t = reliability_table(y_bin, p, edges)

    n = float(len(y_bin))
    base = float(y_bin.mean())
    rel = float(np.sum(t["n"] * (t["p_mean"] - t["freq"]) ** 2) / n)
    res = float(np.sum(t["n"] * (t["freq"] - base) ** 2) / n)
    unc = base * (1.0 - base)
    b = brier(y_bin, p)

    return {"brier": b, "affidabilita": rel, "risoluzione": res,
            "incertezza": unc, "residuo": b - (rel - res + unc), "n_fasce": len(t)}


# ------------------------------------------------ calibrazione della predittiva
def pit(y: np.ndarray, lam: np.ndarray, r=None,
        seed: int = config.SEED) -> np.ndarray:
    """PIT randomizzato per conteggi (Czado, Gneiting e Held).

    Per una variabile discreta la trasformata integrale di probabilita' non e'
    uniforme nemmeno con la predittiva giusta: F(y) salta. Si randomizza
    dentro il salto,

        u = F(y-1) + v * (F(y) - F(y-1)),   v ~ U(0,1)

    e allora u e' uniforme **se e solo se** l'intera distribuzione predittiva e'
    corretta, non solo la sua media. E' il controllo che la pendenza di
    calibrazione non fa: quella guarda soltanto il livello di lambda.
    """
    y = np.asarray(y, dtype=float)
    lo = dispersion.cdf(y - 1.0, lam, r)
    hi = dispersion.cdf(y, lam, r)
    v = np.random.default_rng(seed).uniform(0.0, 1.0, len(y))
    return lo + v * (hi - lo)


def pit_uniformity(u: np.ndarray, n_bins: int = 10) -> dict:
    """Test chi-quadro di uniformita' del PIT, con la tabella delle fasce.

    Sotto l'ipotesi di predittiva corretta i conteggi per fascia sono
    multinomiali uniformi. Un eccesso agli estremi significa predittiva troppo
    stretta (sottodispersione), un eccesso al centro troppo larga.
    """
    from scipy.stats import chi2

    u = np.asarray(u, dtype=float)
    counts, _ = np.histogram(np.clip(u, 0.0, 1.0), bins=n_bins, range=(0.0, 1.0))
    exp = len(u) / n_bins
    stat = float(np.sum((counts - exp) ** 2) / exp)
    return {"chi2": stat, "dof": n_bins - 1,
            "p_value": float(chi2.sf(stat, n_bins - 1)),
            "counts": counts, "expected": exp,
            "mean": float(u.mean()), "sd": float(u.std(ddof=1))}


def interval_coverage(y: np.ndarray, lam: np.ndarray, r=None,
                      levels=(0.5, 0.8, 0.95)) -> pd.DataFrame:
    """Copertura empirica degli intervalli di previsione centrali.

    Su conteggi la copertura e' **strutturalmente conservativa**: gli estremi
    dell'intervallo sono interi, quindi l'intervallo reale e' quasi sempre piu'
    largo del nominale. Una copertura sopra il nominale di pochi punti e'
    attesa; una sotto e' il segnale da leggere.
    """
    y = np.asarray(y, dtype=float)
    rows = []
    for lv in levels:
        a = (1.0 - lv) / 2.0
        lo = dispersion.ppf(a, lam, r)
        hi = dispersion.ppf(1.0 - a, lam, r)
        rows.append({"livello": lv,
                     "copertura": float(np.mean((y >= lo) & (y <= hi))),
                     "ampiezza_media": float(np.mean(hi - lo + 1))})
    return pd.DataFrame(rows)


def metrics(y: np.ndarray, lam: np.ndarray, r=None,
            line: float = config.OVER_LINE,
            base_rate=None) -> dict:
    """Blocco completo di metriche, con il tasso base sempre accanto al Brier.

    `r` e `base_rate` accettano sia uno scalare sia un vettore riga per riga:
    il secondo caso e' la versione walk-forward, in cui anche la dispersione e
    il tasso base vengono dal solo passato.

    `sharpness` (deviazione standard dei lambda previsti) sta accanto alla
    pendenza di calibrazione perche' le due vanno lette insieme: prevedere la
    media a tutti da' calibrazione perfetta e sharpness zero, cioe' nessuna
    informazione. Un modello va giudicato sulla sharpness **a parita' di
    calibrazione**.
    """
    y = np.asarray(y, dtype=float)
    lam = np.asarray(lam, dtype=float)

    slope, se = calibration_slope(y, lam)
    y_bin = (y > line).astype(float)
    p = dispersion.p_over(lam, line, r)
    base = np.broadcast_to(
        np.asarray(y_bin.mean() if base_rate is None else base_rate, dtype=float),
        y_bin.shape)

    return {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(y - lam))),
        "rmse": float(np.sqrt(np.mean((y - lam) ** 2))),
        "bias": float(np.mean(lam - y)),
        # Con lambda costante la correlazione non esiste (denominatore nullo):
        # `nan` e' l'unica risposta onesta, ed e' il limite del baseline piatto.
        "corr": float(np.corrcoef(lam, y)[0, 1]) if np.std(lam) > 0 else float("nan"),
        "sharpness": float(np.std(lam, ddof=1)),
        "calib_slope": slope,
        "calib_se": se,
        "calib_z_vs_1": (slope - 1.0) / se,
        "loglik_poisson": float(np.sum(dispersion.nb2_loglik(y, lam, dispersion.R_MAX))),
        "loglik_nb2": float(np.sum(dispersion.nb2_loglik(y, lam, r))) if r is not None
        else float(np.sum(dispersion.nb2_loglik(y, lam, dispersion.R_MAX))),
        "brier": brier(y_bin, p),
        "brier_base": brier(y_bin, base),
        "ece": ece(y_bin, p),
        "base_rate": float(np.mean(base)),
    }


# ------------------------------------------------------------------- confronti
def paired_t(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Somma e statistica t della differenza appaiata `a - b`.

    Appaiata sulla stessa partita: due modelli valutati sulle stesse righe
    sbagliano insieme sulle partite strane, e ignorarlo gonfia l'errore
    standard fino a rendere invisibile qualunque differenza.
    """
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    se = d.std(ddof=1) / np.sqrt(len(d))
    return float(d.sum()), float(d.mean() / se) if se > 0 else float("nan")


def compare_models(y: np.ndarray, preds: dict, dates: pd.Series | None = None,
                   r=None, line: float = config.OVER_LINE,
                   base_rate=None, reference: str | None = None
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tabella di metriche per piu' modelli sulle **stesse identiche righe**.

    `r` puo' essere un dizionario nome -> dispersione, cosi' ogni modello usa la
    propria: imporre a un baseline la dispersione stimata sui lambda del
    modello lo penalizzerebbe per un parametro che non e' suo.

    Ritorna (tabella delle metriche, tabella dei confronti appaiati contro
    `reference`, che di default e' il primo modello del dizionario).
    """
    y = np.asarray(y, dtype=float)
    names = list(preds)
    reference = reference or names[0]

    def r_of(name):
        return r.get(name) if isinstance(r, dict) else r

    tab = pd.DataFrame([
        dict(metrics(y, np.asarray(preds[n], dtype=float), r=r_of(n), line=line,
                     base_rate=base_rate), modello=n)
        for n in names]).set_index("modello")

    ref_lam = np.asarray(preds[reference], dtype=float)
    ref_ll = dispersion.nb2_loglik(y, ref_lam, r_of(reference)
                                   if r_of(reference) is not None else dispersion.R_MAX)
    ref_ae = np.abs(y - ref_lam)

    rows = []
    for n in names:
        if n == reference:
            continue
        lam = np.asarray(preds[n], dtype=float)
        rr = r_of(n) if r_of(n) is not None else dispersion.R_MAX
        d_ll, t_ll = paired_t(ref_ll, dispersion.nb2_loglik(y, lam, rr))
        d_ae, t_ae = paired_t(np.abs(y - lam), ref_ae)
        m_ae = d_ae / len(y)
        rows.append({"vs": n, "d_loglik": d_ll, "t_loglik": t_ll,
                     "d_mae": m_ae, "t_mae": t_ae,
                     # se = media / t: serve a disegnare l'intervallo, che e'
                     # il modo giusto di leggere un confronto appaiato.
                     "se_mae": abs(m_ae / t_ae) if t_ae else float("nan")})
    return tab, pd.DataFrame(rows)


# --------------------------------------- il blocco di valutazione, una volta sola
def evaluation_bundle(df: pd.DataFrame, wf_path=None, verbose: bool = True) -> dict:
    """Previsioni walk-forward, baseline e parametri dal passato, in un colpo.

    Fase 4 e Fase 5 devono guardare **gli stessi** numeri: se ognuna se li
    ricalcolasse per conto proprio, prima o poi divergerebbero e nessuna delle
    due se ne accorgerebbe. Da qui in poi c'e' una sola strada.

    `wf_path` e' la cache di Fase 2; se manca, il walk-forward viene ricalcolato.
    """
    if wf_path is not None and wf_path.exists():
        if verbose:
            print(f"  previsioni walk-forward da {wf_path.name}")
        ef = pd.read_parquet(wf_path)
    else:
        if verbose:
            print("  cache assente: ricalcolo walk-forward (~40 s)")
        out = walkforward_predict(df)
        ef = out[out.eligible]
    ef = ef.sort_values(["matchId", "team"]).reset_index(drop=True)

    y = ef["sot"].to_numpy(dtype=float)
    blw = walkforward_baselines(df)
    be = blw[blw.eligible].set_index(["matchId", "team"])
    key = pd.MultiIndex.from_frame(ef[["matchId", "team"]])
    if be.index.isin(key).sum() != len(ef):
        raise ValueError("baseline e modello valutati su righe diverse")

    preds = {MODEL_NAME: ef["lam"].to_numpy(dtype=float)}
    for name in be.columns.drop(["date", "team_match_idx", "sot", "eligible"],
                                errors="ignore"):
        preds[name] = be.loc[key, name].to_numpy(dtype=float)

    r_wf = {n: walkforward_r(y, lam, ef["date"]) for n, lam in preds.items()}
    r_full = {n: dispersion.fit_r(y, lam) for n, lam in preds.items()}
    base_wf = {ln: walkforward_base_rate(y, ef["date"], line=ln) for ln in LINES}

    tab, cmp_ = compare_models(y, preds, r=r_wf,
                               base_rate=base_wf[config.OVER_LINE])
    return {"ef": ef, "y": y, "preds": preds, "r_wf": r_wf, "r_full": r_full,
            "base_wf": base_wf, "tab": tab, "cmp": cmp_}


def metrics_by_segment(y: np.ndarray, lam: np.ndarray, seg: pd.Series,
                       r=None, line: float = config.OVER_LINE) -> pd.DataFrame:
    """Le stesse metriche, dentro ogni sottoinsieme di `seg`.

    Serve a scoprire se un MAE aggregato accettabile nasconde un segmento in
    cui il modello e' sistematicamente storto — tipicamente le squadre di
    vertice, che la ridge comprime verso il centro.
    """
    y = np.asarray(y, dtype=float)
    lam = np.asarray(lam, dtype=float)
    # `pd.Series(seg)` e non `np.asarray`: su un categorico ordinato conserva
    # l'ordine delle categorie, che altrimenti diventerebbe alfabetico.
    seg = pd.Series(seg).reset_index(drop=True)
    rr = np.broadcast_to(np.asarray(r if r is not None else dispersion.R_MAX,
                                    dtype=float), y.shape)

    rows = []
    for lv, idx in seg.groupby(seg, observed=True).groups.items():
        i = np.asarray(idx)
        rows.append(dict(metrics(y[i], lam[i], r=rr[i], line=line), segmento=str(lv)))
    return pd.DataFrame(rows).set_index("segmento")
