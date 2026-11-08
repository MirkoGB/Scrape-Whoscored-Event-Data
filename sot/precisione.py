# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V2 — lo strato della precisione, e la composizione.

    sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
    logit(p_ij) = mu_p + a_i + d_j + g_p * casa

**Non e' una previsione di `sot`, ed e' la distinzione piu' facile da
sbagliare.** Condizionare su `shots_ij` osservati non si puo' fare quando si
prevede: al momento della previsione i tentativi non sono ancora stati tirati.
La forma predittiva e' la **marginale composta**, e il suo concorrente non e' un
baseline stupido ma il **modello diretto sui tiri in porta gia' pubblicato dalla
Fase 2**. Se non lo batte, la gerarchia e' elegante e inutile.

LA COMPOSIZIONE, E QUANDO LA FORMA CHIUSA VALE
----------------------------------------------
Se `N ~ NB2(lam, r)` e `S | N ~ Bin(N, p)` con `p` **fisso data la riga**, allora
`S ~ NB2(lam*p, r)`: stesso `r`, media scalata. V0 lo ha verificato su dati
generati.

**Vale riga per riga anche quando `p` cambia fra righe**, purche' dentro la riga
sia un numero e non una variabile aleatoria — ed e' esattamente il caso di un
`p_ij` prodotto da un modello. La precisazione conta, perche' V0 aveva scritto
che la forma chiusa «non e' valida cosi' com'e'» avendo in mente un'altra cosa:
cio' che la rompe non e' che `p` vari **fra** squadre, ma che vari **dentro** la
squadra-partita, cioe' la sovradispersione residua che il modello non cattura.
V0 l'ha misurata (`rho` intraclasse 0,0083) e `pmf_composta` la tratta con la
convoluzione beta-binomiale, che e' la strada senza forma chiusa. Le due
coincidono a `rho = 0`, e un test lo pretende.

I LATI: DECISIONE DELL'UTENTE, NON ESITO DEL CRITERIO
-----------------------------------------------------
`tentativi.LATI_STRATO2` vale `("attacco", "difesa")` per **decisione
dell'utente del 2026-08-13**, mentre `tentativi.verdetto_strato2()` continua a
rispondere `["attacco"]`: sul lato difensivo il test di dispersione rifiuta ma
`tau` resta sotto il proprio MDE tarato. Il criterio **non e' stato riscritto**
per farlo tornare.

La decisione ha un argomento — la seconda strada, indipendente e piu' potente,
rifiuta nettamente (GLM, F = 2,83, p = 2,3e-06) — e ha un costo, che questo
modulo **misura invece di assumere**: `confronto_lati()` stima entrambe le
varianti e le mette una contro l'altra fuori campione. Un effetto sotto il MDE
del test primario puo' valere zero quando si prevede.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import config, tentativi as T, volume as VL

TARGET = T.TARGET_PRECISIONE      # `sot`, il numeratore
DENOM = T.TARGET                  # `shots`, il denominatore

CACHE = config.processed_league_dir() / "fase12_strato2.parquet"

#: Il criterio di adozione della gerarchia, **scritto prima** di guardare i
#: numeri, nella forma di `ricalibrazione.CRITERIO_ADOZIONE`.
CRITERIO_GERARCHIA = (
    "la gerarchia si adotta al posto del modello DIRETTO sui tiri in porta solo "
    "se (a) la marginale composta non perde in MAE appaiato oltre il proprio "
    "MDE, e (b) il segno del margine e' lo stesso in almeno 4 stagioni su 5. "
    "A parita' si tiene il modello diretto, che ha meno parti."
)

#: Alpha della ridge sullo strato 2. **Non si sceglie sul bersaglio**: e' il
#: centro della griglia gia' usata dal progetto (`validate.ALPHA_GRID`), e la
#: sensibilita' e' riportata da `sensibilita_alpha()` invece di essere
#: ottimizzata via.
ALPHA_PRECISIONE = 6.0


@dataclass
class ModelloPrecisione:
    """Binomiale con logit, effetti attacco/difesa/campo e ridge.

    **Non riusa `TeamModel`** e non e' una svista: li' la verosimiglianza e'
    Poisson con link log su un conteggio senza denominatore, qui e' binomiale
    con link logit su `k` successi in `n` prove. La struttura del disegno e' la
    stessa, la funzione obiettivo no. Duplicare quindici righe di costruzione
    delle dummy e' meno rischioso che rendere parametrico il cuore su cui
    poggiano undici fasi.

    Come in `TeamModel`, la ridge penalizza **solo** attacco e difesa: senza
    penalita' i due blocchi non sono identificabili separatamente
    dall'intercetta. `mu_p` e `gamma_p` restano non penalizzati.

    `lati` decide quali blocchi entrano. Con `("attacco",)` la difesa non ha
    dummy affatto — non e' azzerata a posteriori, il che darebbe gli stessi
    numeri ma renderebbe illeggibile il conteggio dei parametri.
    """

    alpha: float = ALPHA_PRECISIONE
    half_life: float = config.HALF_LIFE_DAYS
    lati: tuple[str, ...] = T.LATI_STRATO2

    teams_: list = field(default_factory=list, init=False)
    beta_: np.ndarray = field(default=None, init=False)
    mu_: float = field(default=None, init=False)

    # ------------------------------------------------------------------ design
    def _blocchi(self) -> tuple[bool, bool]:
        return "attacco" in self.lati, "difesa" in self.lati

    def _n_par(self) -> int:
        att, dif = self._blocchi()
        return 1 + len(self.teams_) * (int(att) + int(dif)) + 1

    def _design(self, df: pd.DataFrame) -> np.ndarray:
        n, n_t = len(df), len(self.teams_)
        att, dif = self._blocchi()
        X = np.zeros((n, self._n_par()))
        X[:, 0] = 1.0
        idx = {t: i for i, t in enumerate(self.teams_)}
        rows = np.arange(n)
        col = 1
        if att:
            a = df["team"].map(idx).to_numpy()
            ok = ~pd.isna(a)
            X[rows[ok], col + a[ok].astype(int)] = 1.0
            col += n_t
        if dif:
            d = df["opponent"].map(idx).to_numpy()
            ok = ~pd.isna(d)
            X[rows[ok], col + d[ok].astype(int)] = 1.0
            col += n_t
        X[:, col] = df["is_home"].to_numpy(dtype=float)
        return X

    def _penalty_mask(self) -> np.ndarray:
        p = np.zeros(self._n_par())
        n_t = len(self.teams_)
        att, dif = self._blocchi()
        p[1:1 + n_t * (int(att) + int(dif))] = 1.0
        return p

    def _weights(self, df: pd.DataFrame, as_of: pd.Timestamp) -> np.ndarray:
        age = (as_of - df["date"]).dt.total_seconds().to_numpy() / 86400.0
        return 0.5 ** (np.clip(age, 0.0, None) / self.half_life)

    # --------------------------------------------------------------------- fit
    def fit(self, df: pd.DataFrame, as_of: pd.Timestamp | None = None,
            teams: list | None = None) -> "ModelloPrecisione":
        d = df[df[DENOM] > 0]      # senza tentativi non c'e' una prova binomiale
        self.teams_ = list(teams) if teams is not None else sorted(
            set(df["team"]) | set(df["opponent"]))
        as_of = d["date"].max() if as_of is None else as_of

        X = self._design(d)
        k = d[TARGET].to_numpy(dtype=float)
        nn = d[DENOM].to_numpy(dtype=float)
        w = self._weights(d, as_of)
        pen = self._penalty_mask()

        def obj(b):
            eta = np.clip(X @ b, -30, 30)
            p = 1.0 / (1.0 + np.exp(-eta))
            ll = np.sum(w * (k * np.log(np.clip(p, 1e-12, 1))
                             + (nn - k) * np.log(np.clip(1 - p, 1e-12, 1))))
            grad = -(X.T @ (w * (k - nn * p)))
            return -ll + self.alpha * np.sum(pen * b ** 2), \
                grad + 2.0 * self.alpha * pen * b

        b0 = np.zeros(X.shape[1])
        tot = float(k.sum() / nn.sum())
        b0[0] = np.log(tot / (1 - tot))
        res = optimize.minimize(obj, b0, jac=True, method="L-BFGS-B",
                                options={"maxiter": 500, "ftol": 1e-12})
        self.beta_ = res.x
        self.mu_ = float(res.x[0])
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        eta = np.clip(self._design(df) @ self.beta_, -30, 30)
        return 1.0 / (1.0 + np.exp(-eta))


# --------------------------------------------------------------------------
# Walk-forward
# --------------------------------------------------------------------------
def _p_lega_passato(d: pd.DataFrame) -> np.ndarray:
    """La quota di campionato stimata sul **solo passato**, riga per riga.

    E' il baseline dello strato 2 e il ramo del collasso. Vincolo 1: la quota
    dell'intera stagione userebbe partite che al momento della previsione non
    erano state giocate.
    """
    d = d.sort_values("date")
    k = d[TARGET].to_numpy(dtype=float)
    n = d[DENOM].to_numpy(dtype=float)
    date = d["date"].to_numpy()
    out = np.full(len(d), np.nan)
    for i, oggi in enumerate(date):
        prima = date < oggi
        if prima.sum() >= 30 and n[prima].sum() > 0:
            out[i] = k[prima].sum() / n[prima].sum()
    return pd.Series(out, index=d.index).reindex(d.index).to_numpy()


def walkforward_precisione(stagioni=None, force: bool = False,
                           lati: tuple[str, ...] = None) -> pd.DataFrame:
    """Walk-forward dello strato 2, dentro la stagione come V1.

    Produce, per ogni riga valutabile: `p_hat` (il modello con i lati adottati),
    `p_hat_attacco` (la variante senza difesa, per misurare la decisione
    dell'utente), `p_lega` (il baseline), e il `lam` dello strato 1 gia' pronto.

    Riporta accanto anche `lam_sot_diretto`: il lambda del modello **diretto**
    sui tiri in porta, cioe' il concorrente leale della marginale composta.
    """
    if CACHE.is_file() and not force and lati is None:
        return pd.read_parquet(CACHE)

    from . import validate as V

    lati = T.LATI_STRATO2 if lati is None else tuple(lati)
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    wf1 = VL.walkforward_tiri()
    u = T.universo(stagioni)

    pezzi = []
    for st in stagioni:
        d = u[u["stagione"] == st].copy()

        # Il modello DIRETTO sui tiri in porta: e' la Fase 2 rifatta su questa
        # stagione, ed e' il concorrente contro cui la gerarchia si giustifica.
        diretto = V.walkforward_predict(d, target=TARGET)[
            ["matchId", "team", "lam"]].rename(columns={"lam": "lam_sot_diretto"})

        righe = []
        for oggi, train, test in V.wf.date_splits(d):
            if (train[DENOM] > 0).sum() < 30:
                continue
            teams = sorted(set(d["team"]) | set(d["opponent"]))
            m = ModelloPrecisione(lati=lati).fit(train, as_of=oggi, teams=teams)
            m_att = ModelloPrecisione(lati=("attacco",)).fit(train, as_of=oggi,
                                                             teams=teams)
            t = test.copy()
            t["p_hat"] = m.predict(test)
            t["p_hat_attacco"] = m_att.predict(test)
            righe.append(t)

        if not righe:
            continue
        out = pd.concat(righe, ignore_index=True)
        out["p_lega"] = _p_lega_passato(out)
        out = out.merge(diretto, on=["matchId", "team"], how="left")
        out["stagione"] = st
        pezzi.append(out)

    res = pd.concat(pezzi, ignore_index=True)

    # Lo strato 1 entra come dato: NON si ristima, altrimenti la validazione di
    # V1 non varrebbe piu' per il modello che V2 compone.
    k = wf1.set_index(["matchId", "team"])
    for c in ("lam", "eligible", "alpha"):
        res[c] = [k[c].get((mi, t), np.nan) for mi, t
                  in zip(res["matchId"], res["team"])]
    res["eligible"] = res["eligible"].fillna(False).astype(bool)
    res["lam_composto"] = res["lam"] * res["p_hat"]
    res["lam_composto_attacco"] = res["lam"] * res["p_hat_attacco"]
    res["lam_composto_lega"] = res["lam"] * res["p_lega"]

    if lati == T.LATI_STRATO2:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        res.to_parquet(CACHE, index=False)
    return res


def _valutabili(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    wf = walkforward_precisione() if wf is None else wf
    d = wf[wf["eligible"] & (wf[DENOM] > 0)].copy()
    return d.dropna(subset=["p_hat", "p_lega", "lam", "lam_sot_diretto"])


# --------------------------------------------------------------------------
# 1. Lo strato 2 come modello della QUOTA (non una previsione di `sot`)
# --------------------------------------------------------------------------
def valutazione_condizionata(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Lo strato 2 contro `p = p_lega`, **condizionando su `shots` osservati**.

    **QUESTA NON E' UNA PREVISIONE DI `sot`.** Al momento della previsione i
    tentativi non sono stati tirati, quindi nessuno di questi numeri e'
    ottenibile in avanti. Misura una cosa sola: se `p` sia prevedibile meglio di
    un numero unico. La previsione vera e' la marginale composta di §2.
    """
    from . import validate as V

    d = _valutabili(wf)
    k = d[TARGET].to_numpy(dtype=float)
    n = d[DENOM].to_numpy(dtype=float)

    righe = []
    for nome, p in (("strato 2 (attacco+difesa)", d["p_hat"].to_numpy()),
                    ("strato 2 (solo attacco)", d["p_hat_attacco"].to_numpy()),
                    ("p_lega (walk-forward)", d["p_lega"].to_numpy())):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        ll = np.sum(k * np.log(p) + (n - k) * np.log(1 - p))
        righe.append({
            "modello": nome,
            "n": len(d),
            "logverosimiglianza": float(ll),
            "ll_per_riga": float(ll / len(d)),
            "mae_quota": float(np.abs(k / n - p).mean()),
            "brier_quota": float(np.mean((k / n - p) ** 2)),
            "corr": float(np.corrcoef(k / n, p)[0, 1]),
        })
    out = pd.DataFrame(righe)
    base = out.loc[out["modello"].str.startswith("p_lega"), "ll_per_riga"].iloc[0]
    out["guadagno_per_riga"] = out["ll_per_riga"] - base

    # Il `t` appaiato contro il baseline, per cluster di partita come in V1.
    for i, nome in enumerate(out["modello"]):
        col = {"strato 2 (attacco+difesa)": "p_hat",
               "strato 2 (solo attacco)": "p_hat_attacco",
               "p_lega (walk-forward)": "p_lega"}[nome]
        p = np.clip(d[col].to_numpy(), 1e-9, 1 - 1e-9)
        pl = np.clip(d["p_lega"].to_numpy(), 1e-9, 1 - 1e-9)
        a = k * np.log(p) + (n - k) * np.log(1 - p)
        b = k * np.log(pl) + (n - k) * np.log(1 - pl)
        _s, t = V.paired_t(a, b, cluster=d["matchId"].to_numpy())
        out.loc[i, "t_vs_lega"] = t
    return out


def confronto_lati(wf: pd.DataFrame | None = None) -> dict:
    """Il costo della decisione dell'utente, **misurato invece che assunto**.

    La difesa e' entrata per decisione, non perche' il criterio la ammettesse:
    `tau` restava sotto il MDE tarato. Qui si guarda se, fuori campione, quel
    lato paghi — sulla quota e sulla marginale composta.
    """
    from . import validate as V

    d = _valutabili(wf)
    k = d[TARGET].to_numpy(dtype=float)
    n = d[DENOM].to_numpy(dtype=float)
    clu = d["matchId"].to_numpy()

    p2 = np.clip(d["p_hat"].to_numpy(), 1e-9, 1 - 1e-9)
    p1 = np.clip(d["p_hat_attacco"].to_numpy(), 1e-9, 1 - 1e-9)
    ll2 = k * np.log(p2) + (n - k) * np.log(1 - p2)
    ll1 = k * np.log(p1) + (n - k) * np.log(1 - p1)
    _s, t_quota = V.paired_t(ll2, ll1, cluster=clu)

    e2 = np.abs(k - d["lam_composto"].to_numpy())
    e1 = np.abs(k - d["lam_composto_attacco"].to_numpy())
    _s, t_mae = V.paired_t(e1, e2, cluster=clu)

    dd = ll2 - ll1
    dd_clu = pd.Series(dd).groupby(clu).mean()
    se = dd_clu.std(ddof=1) / np.sqrt(len(dd_clu))
    return {
        "lati_adottati": list(T.LATI_STRATO2),
        "guadagno_ll_per_riga": float(dd.mean()),
        "t_quota": t_quota,
        "mde_ll_per_riga": float((2.0 + stats.norm.ppf(0.80)) * se),
        "mae_composto_attacco": float(e1.mean()),
        "mae_composto_attacco_difesa": float(e2.mean()),
        "delta_mae": float((e1 - e2).mean()),
        "t_mae": t_mae,
        "la_difesa_paga": bool(t_quota > 2.0),
    }


def sensibilita_alpha(wf: pd.DataFrame | None = None,
                      alphas=(1.0, 3.0, 6.0, 12.0, 25.0)) -> pd.DataFrame:
    """Il verdetto dipende da `alpha`? Riportato invece che ottimizzato.

    Scegliere `alpha` sul bersaglio sarebbe un iperparametro adattato al
    campione su cui poi lo si valuta — vincolo 1. Qui si mostra la
    sensibilita' e si tiene il valore dichiarato.
    """
    from . import validate as V

    u = T.universo()
    wf1 = VL.walkforward_tiri()
    righe = []
    for a in alphas:
        d = u[u["stagione"] == config.SEASONS_STORICHE[-1]]
        pezzi = []
        for oggi, train, test in V.wf.date_splits(d):
            if (train[DENOM] > 0).sum() < 30:
                continue
            teams = sorted(set(d["team"]) | set(d["opponent"]))
            m = ModelloPrecisione(alpha=a).fit(train, as_of=oggi, teams=teams)
            t = test.copy()
            t["p_hat"] = m.predict(test)
            pezzi.append(t)
        o = pd.concat(pezzi, ignore_index=True)
        o = o[o[DENOM] > 0]
        k = o.set_index(["matchId", "team"])
        elig = np.array([bool(wf1.set_index(["matchId", "team"])["eligible"]
                              .get((mi, tt), False))
                         for mi, tt in zip(o["matchId"], o["team"])])
        o = o[elig]
        kk = o[TARGET].to_numpy(dtype=float)
        nn = o[DENOM].to_numpy(dtype=float)
        p = np.clip(o["p_hat"].to_numpy(), 1e-9, 1 - 1e-9)
        righe.append({
            "alpha": a, "n": len(o),
            "ll_per_riga": float((kk * np.log(p) + (nn - kk) * np.log(1 - p)).mean()),
            "mae_quota": float(np.abs(kk / nn - p).mean()),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# 2. La composizione — la forma predittiva vera
# --------------------------------------------------------------------------
def pmf_composta(lam: float, p: float, r: float, rho: float = 0.0,
                 n_max: int | None = None) -> np.ndarray:
    """PMF di `S` con `N ~ NB2(lam, r)` e `S|N ~ Bin(N, p)`.

    Due strade, e la scelta e' dichiarata dal parametro:

    * `rho = 0` — **forma chiusa**: `S ~ NB2(lam*p, r)`. Vale quando `p` e' un
      numero data la riga, che e' il caso di un `p` prodotto da un modello.
    * `rho > 0` — **convoluzione numerica** con `S|N ~ BetaBin(N, p, rho)`. La
      forma chiusa NON vale e la funzione si rifiuta di usarla: e' la
      sovradispersione residua della quota dentro la squadra-partita, che V0 ha
      misurato a 0,0083 e che nessun effetto di squadra cattura.
    """
    from scipy.stats import nbinom

    if rho < 0:
        raise ValueError(f"rho negativo: {rho}")
    n_max = int(lam + 12.0 * np.sqrt(lam + lam ** 2 / r) + 20) if n_max is None else n_max
    k = np.arange(n_max + 1)

    if rho == 0.0:
        lp = lam * p
        return nbinom.pmf(k, r, r / (r + lp))

    # Convoluzione: P(S=s) = sum_n P(N=n) * P(S=s | N=n), beta-binomiale.
    from scipy.special import betaln

    pn = nbinom.pmf(k, r, r / (r + lam))
    s_par = 1.0 / rho - 1.0
    a, b = p * s_par, (1.0 - p) * s_par
    out = np.zeros(n_max + 1)
    for n in k:
        if pn[n] < 1e-15:
            continue
        s = np.arange(n + 1)
        from scipy.special import gammaln
        logc = (gammaln(n + 1) - gammaln(s + 1) - gammaln(n - s + 1))
        lg = logc + betaln(s + a, n - s + b) - betaln(a, b)
        out[:n + 1] += pn[n] * np.exp(lg)
    return out


def marginale_composta(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """La gerarchia contro il modello DIRETTO sui tiri in porta.

    **E' il confronto che decide se la gerarchia serve.** Il concorrente non e'
    un baseline stupido: e' il modello che la Fase 2 ha gia' pubblicato,
    riaddestrato sulle stesse cinque stagioni e sullo stesso perimetro.

    **`r` e' ricostruito walk-forward su `sot`**, come in ogni altra validazione
    del progetto, e **non ereditato dallo strato 1**. Ereditarlo sarebbe la
    scelta piu' coerente con la gerarchia — il thinning prevede lo *stesso* `r` —
    ma renderebbe la validazione dipendente da un'assunzione che
    `rapporto_dispersioni()` mette alla prova e che i dati **rifiutano**
    (rapporto 1,63, IC95 [1,15, 2,80]). Usare qui il `r` dello strato 1
    imporrebbe una predittiva troppo larga sulle code e farebbe apparire la
    gerarchia peggiore per una ragione che non e' il suo lambda.
    """
    from . import validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    r = V.walkforward_r(y, d["lam_composto"].to_numpy(), d["date"])
    base = V.walkforward_base_rate(y, d["date"], line=config.OVER_LINE)

    candidati = {
        "gerarchia (composta)": d["lam_composto"].to_numpy(),
        "gerarchia (solo attacco)": d["lam_composto_attacco"].to_numpy(),
        "gerarchia con p_lega": d["lam_composto_lega"].to_numpy(),
        "modello DIRETTO su sot": d["lam_sot_diretto"].to_numpy(),
    }
    righe = []
    for nome, lam in candidati.items():
        righe.append({"modello": nome,
                      **V.metrics(y, lam, r=r, line=config.OVER_LINE,
                                  base_rate=base)})
    return pd.DataFrame(righe)


def confronto_col_diretto(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il margine della gerarchia sul diretto, col `t` per cluster e il MDE."""
    from . import validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    clu = d["matchId"].to_numpy()
    e_dir = np.abs(y - d["lam_sot_diretto"].to_numpy())

    righe = []
    for nome, col in (("gerarchia (composta)", "lam_composto"),
                      ("gerarchia (solo attacco)", "lam_composto_attacco"),
                      ("gerarchia con p_lega", "lam_composto_lega")):
        e = np.abs(y - d[col].to_numpy())
        _s, t = V.paired_t(e_dir, e, cluster=clu)
        dd = pd.Series(e_dir - e).groupby(clu).mean()
        se = dd.std(ddof=1) / np.sqrt(len(dd))
        righe.append({
            "variante": nome,
            "mae": float(e.mean()),
            "mae_diretto": float(e_dir.mean()),
            "delta_mae": float((e_dir - e).mean()),
            "t_per_cluster": t,
            "mde": float((2.0 + stats.norm.ppf(0.80)) * se),
        })
    out = pd.DataFrame(righe)
    out["batte_il_diretto"] = out["t_per_cluster"] > 2.0
    out["dentro_il_mde"] = out["delta_mae"].abs() < out["mde"]
    return out


def per_stagione(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il segno del margine sul diretto, stagione per stagione.

    Serve al criterio: quattro stagioni su cinque con lo stesso segno.
    """
    d = _valutabili(wf)
    righe = []
    for st, g in d.groupby("stagione"):
        y = g[TARGET].to_numpy(dtype=float)
        e_g = np.abs(y - g["lam_composto"].to_numpy())
        e_d = np.abs(y - g["lam_sot_diretto"].to_numpy())
        righe.append({"stagione": st, "n": len(g),
                      "mae_gerarchia": float(e_g.mean()),
                      "mae_diretto": float(e_d.mean()),
                      "delta": float((e_d - e_g).mean()),
                      "gerarchia_vince": bool(e_g.mean() < e_d.mean())})
    return pd.DataFrame(righe)


def rapporto_dispersioni(wf: pd.DataFrame | None = None,
                         n_boot: int = 1000) -> dict:
    """`r` stimata su `shots` contro `r` stimata su `sot`, stesse righe.

    **E' la coerenza della gerarchia resa un numero.** Sotto il thinning con `p`
    fisso data la riga le due devono essere **uguali**; `r_sot < r_shots` e' la
    firma di variabilita' della quota che il modello non cattura.

    Deve concordare con V0: se V0 dice che la quota varia fra squadre e il
    rapporto dice 1, o se V0 dice di no e il rapporto dice 0,5, una delle due
    misure e' sbagliata e va detto invece di scegliere la piu' comoda.
    """
    from . import dispersion as D

    d = _valutabili(wf)
    r_shots = D.fit_r(d[DENOM].to_numpy(dtype=float), d["lam"].to_numpy())
    r_sot = D.fit_r(d[TARGET].to_numpy(dtype=float), d["lam_composto"].to_numpy())

    rng = np.random.default_rng(config.SEED)
    idx = np.arange(len(d))
    rap = np.empty(n_boot)
    ns, nt = d[DENOM].to_numpy(dtype=float), d[TARGET].to_numpy(dtype=float)
    ls, lc = d["lam"].to_numpy(), d["lam_composto"].to_numpy()
    for i in range(n_boot):
        s = rng.choice(idx, size=len(idx), replace=True)
        rap[i] = D.fit_r(nt[s], lc[s]) / D.fit_r(ns[s], ls[s])

    return {"r_shots": float(r_shots), "r_sot": float(r_sot),
            "rapporto": float(r_sot / r_shots),
            "ic95": (float(np.percentile(rap, 2.5)),
                     float(np.percentile(rap, 97.5))),
            "uguali": bool(np.percentile(rap, 2.5) <= 1.0 <= np.percentile(rap, 97.5)),
            "n": int(len(d))}


def verdetto_gerarchia(conf: pd.DataFrame | None = None,
                       stag: pd.DataFrame | None = None) -> dict:
    """`CRITERIO_GERARCHIA` applicato dal codice, non a occhio."""
    conf = confronto_col_diretto() if conf is None else conf
    stag = per_stagione() if stag is None else stag
    r = conf[conf["variante"] == "gerarchia (composta)"].iloc[0]
    concordi = int(stag["gerarchia_vince"].sum())
    non_perde = bool(r["delta_mae"] >= 0 or abs(r["delta_mae"]) < r["mde"])
    segno = bool(concordi >= 4 or (5 - concordi) >= 4)
    return {
        "criterio": CRITERIO_GERARCHIA,
        "delta_mae": float(r["delta_mae"]),
        "mde": float(r["mde"]),
        "non_perde_oltre_il_mde": non_perde,
        "stagioni_in_cui_vince": concordi,
        "segno_stabile": segno,
        "adotta_la_gerarchia": bool(non_perde and segno and r["delta_mae"] >= 0),
        "ramo": ("gerarchia" if (non_perde and segno and r["delta_mae"] >= 0)
                 else "modello diretto (meno parti)"),
    }
