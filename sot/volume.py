# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V1 — lo strato del volume: i tentativi per squadra-partita.

    shots_ij ~ NB2(lambda_ij, r)
    log(lambda_ij) = mu + attacco_i + difesa_j + gamma * casa

**La specificazione e' quella della Fase 2 e cambia solo il bersaglio**, ed e'
voluto: se la specificazione cambiasse insieme al bersaglio non si saprebbe a
quale delle due cose attribuire la differenza. E' la stessa disciplina con cui
E3 ha portato `TeamModel` sui gol.

**LA VALIDAZIONE NON SI EREDITA.** Che il modello sia calibrato sui tiri in
porta non dice niente sui tentativi: media tre volte piu' alta, dispersione
diversa, e un bersaglio che dipende dall'avversario in modo diverso. Tutto qui
dentro e' rifatto da capo — `r`, il tasso base, la pendenza, il PIT — con `r` e
tasso base ricostruiti **sul solo passato**, perche' entrano nel Brier e un
Brier con parametri stimati sull'intero campione non e' fuori campione.

IL WALK-FORWARD E' DENTRO LA STAGIONE
-------------------------------------
Ogni stagione ha il proprio walk-forward e le previsioni si impilano dopo. Non
e' una comodita': le squadre cambiano fra stagioni e un decadimento di 150
giorni attraverso l'estate darebbe alla prima giornata di settembre un training
fatto quasi solo di maggio. E' la scelta di E3, per la stessa ragione, e V0 le
ha aggiunto un argomento: **il livello dei tentativi si muove del 5,5% fra le
cinque stagioni**, e stimando dentro stagione `mu` lo assorbe per costruzione —
senza bisogno di un effetto di stagione ne' della standardizzazione di E1, che
governa il confronto fra unita' grezze di stagioni diverse e qui non serve
perche' quel confronto non avviene mai.

IL CLUSTER DI PARTITA, E PERCHE' VA NEL VERSO BUONO
---------------------------------------------------
La riga e' la squadra-partita, ma l'unita' indipendente e' la **partita**: le
due squadre condividono ritmo, punteggio e arbitro. V0 ha misurato la
correlazione fra i due lati e vale **-0,349** — negativa, non positiva, perche'
il possesso e' a somma costante e chi domina tira molto lasciando tirare poco.

Ne segue che raggruppare per partita **riduce** l'errore standard invece di
gonfiarlo (fattore 0,807). Un fattore favorevole non dichiarato resta pero' un
numero sbagliato, quindi ogni confronto appaiato di questo modulo riporta
**entrambi** i `t`, per riga e per cluster: cosi' si vede quanto valeva
l'assunzione invece di doverla assumere. E' la stessa forma con cui
`walkforward_r` ha reso visibile la scorciatoia della Fase 2.

QUATTRO LIMITI, IN TABELLA E NON IN FONDO (vincolo 5)
-----------------------------------------------------
1. **Il fattore di cluster**, sopra.
2. **Cinque cold start invece di uno.** Le prime tre giornate di ogni stagione
   non hanno previsione (`date_splits` pretende 30 partite di training) e il
   burn-in ne toglie altre due. `copertura()` li conta invece di lasciarli
   impliciti.
3. **Il MAE pooled non e' confrontabile fra stagioni**, perche' il livello si
   muove del 5,5%. `per_stagione()` riporta anche il MAE **relativo**.
4. **La 2021-22 e' la prima stagione di ritorno del pubblico**, quindi il suo
   `gamma` non e' confrontabile con gli altri quattro. Dentro stagione non fa
   danno alla stima; una media dei cinque `gamma` sarebbe una media di due
   regimi, e va etichettata.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config, tentativi as T

#: Il bersaglio. E' `team_match.shots`, cioe' i tentativi totali.
TARGET = T.TARGET

#: La soglia Over principale per le metriche binarie, **dichiarata in V0** e non
#: scelta qui guardando i dati: 12.5 e' la linea di mercato piu' vicina alla
#: media di tentativi per squadra-partita (12,58). La 4.5 della Fase 2 sarebbe
#: assurda su questo bersaglio, ed e' un altro modo di dire che le due
#: validazioni non si ereditano.
LINEA = T.LINEA_PRINCIPALE

#: I quattro baseline stupidi (vincolo 6), nell'ordine in cui si leggono.
BASELINE = ("media squadra + campo", "media squadra", "media casa/trasferta",
            "media campionato")

def cache(league: str | None = None, target: str = TARGET) -> Path:
    """Dove sta il walk-forward, per campionato e per bersaglio.

    **Il nome del file non cambia per il caso gia' pubblicato: cambia la
    cartella**, perche' `processed_league_dir` gia' separa i campionati. Cosi' la
    cache della Serie A sui tentativi resta esattamente dove era —
    `data/processed/ITA-serie-a/fase12_walkforward_tiri.parquet` — e i numeri di
    V1 non si ricalcolano per il solo fatto che questa funzione esiste.

    Il bersaglio entra nel nome solo quando **non** e' quello di V1: la Fase 14
    ha bisogno del walk-forward sui **tiri in porta** per stimarne la propria
    `r`, che e' un'altra grandezza (26,0 contro 20,0) e non si eredita.
    """
    nome = ("fase12_walkforward_tiri.parquet" if target == TARGET
            else f"fase14_walkforward_{target}.parquet")
    return config.processed_league_dir(league) / nome


#: Il percorso della Serie A, cioe' `cache()`. Resta una costante perche' e' cio'
#: che la guardia del vincolo 9 enumera, e perche' V2 e i test la leggono.
CACHE = cache()


def walkforward_tiri(stagioni=None, force: bool = False,
                     league: str | None = None,
                     target: str = TARGET) -> pd.DataFrame:
    """Walk-forward dei tentativi, una stagione per volta, poi impilate.

    Aggiunge `lam_subiti`: il lambda dell'**avversario** nella stessa partita.
    E' la stessa stima letta dall'altro lato, e serve a due cose che V1 non fa
    ma prepara — il totale di partita e la difesa come grandezza a se'.

    **La cache vale solo per l'insieme dichiarato di stagioni**, ed e' una
    correzione della Fase 14 e non un dettaglio: prima la cache si leggeva
    *qualunque* cosa fosse passata in `stagioni`, quindi chiedere una stagione
    sola restituiva in silenzio il walk-forward di tutte e cinque. Con una
    stagione in corso quel difetto diventerebbe visibile nel modo peggiore — la
    previsione userebbe un `r` che non ha niente a che vedere con le stagioni
    chieste — quindi si scrive e si legge la cache **solo** per il default.
    """
    default = list(config.SEASONS_STORICHE)
    stagioni = default if stagioni is None else list(stagioni)
    cacheabile = stagioni == default

    percorso = cache(league, target)
    if cacheabile and percorso.is_file() and not force:
        return pd.read_parquet(percorso)

    from . import validate as V

    u = T.universo(stagioni, league=league)

    pezzi = []
    for st in stagioni:
        d = u[u["stagione"] == st].copy()
        p = V.walkforward_predict(d, target=target)
        b = V.walkforward_baselines(d, target=target)
        # La chiave e' `(matchId, team)`: su `matchId` da solo accoppierebbe fra
        # loro le due squadre della stessa partita, che e' il modo piu'
        # silenzioso di scambiare attacco e difesa. Si dichiara e si verifica.
        m = p.merge(b.drop(columns=["date", "team_match_idx", target, "eligible"]),
                    on=["matchId", "team"], how="inner")
        assert len(m) == len(p), "il join dei baseline ha cambiato le righe"
        m["stagione"] = st

        k = m.set_index(["matchId", "team"])["lam"]
        m["lam_subiti"] = [k.get((mi, o), np.nan) for mi, o
                           in zip(m["matchId"], m["opponent"])]
        pezzi.append(m)

    out = pd.concat(pezzi, ignore_index=True)

    # I tiri in porta osservati viaggiano accanto: sono il bersaglio di V2, e
    # riportarli qui evita che V2 debba rifare il join con l'universo.
    g = u.set_index(["stagione", "matchId", "team"])
    extra = [c for c in (TARGET, T.TARGET_PRECISIONE, "sot_conceded",
                         "shots_conceded") if c not in out.columns]
    for c in extra:
        out[c] = [g[c].get((s, mi, t), np.nan) for s, mi, t
                  in zip(out["stagione"], out["matchId"], out["team"])]

    if cacheabile:
        percorso.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(percorso, index=False)
    return out


def _valutabili(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    wf = walkforward_tiri() if wf is None else wf
    return wf[wf["eligible"]].copy()


def copertura(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Quante righe si perdono, dove, e per quale dei due motivi.

    **I cold start sono cinque, non uno**, ed e' il limite che il perimetro
    multi-stagione introduce e che nessuno vedrebbe da un totale. Le due cause
    non vanno sommate: `senza_previsione` sono le righe che `date_splits` non
    produce affatto, `perse_burnin` quelle che una previsione ce l'hanno ma non
    sono valutabili.
    """
    wf = walkforward_tiri() if wf is None else wf
    u = T.universo()
    righe = []
    for st, d in u.groupby("stagione"):
        w = wf[wf["stagione"] == st]
        righe.append({
            "stagione": st,
            "righe_universo": len(d),
            "con_previsione": len(w),
            "senza_previsione": len(d) - len(w),
            "valutabili": int(w["eligible"].sum()),
            "perse_burnin": int((~w["eligible"]).sum()),
            "quota_valutabile": float(w["eligible"].sum() / len(d)),
        })
    tot = pd.DataFrame(righe)
    tot.loc[len(tot)] = {
        "stagione": "TOTALE",
        **{c: tot[c].sum() for c in tot.columns if c not in ("stagione", "quota_valutabile")},
        "quota_valutabile": float(tot["valutabili"].sum() / tot["righe_universo"].sum()),
    }
    return tot


def valutazione(wf: pd.DataFrame | None = None, linea: float = LINEA) -> pd.DataFrame:
    """Il modello contro i quattro baseline, sulle stesse identiche righe.

    **Non eredita niente dalle Fasi 2 e 4.** `r` e il tasso base sono
    ricostruiti sul solo passato con la procedura di Fase 4.
    """
    from . import validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    r = V.walkforward_r(y, d["lam"].to_numpy(), d["date"])
    base = V.walkforward_base_rate(y, d["date"], line=linea)

    righe = [{"modello": V.MODEL_NAME,
              **V.metrics(y, d["lam"].to_numpy(), r=r, line=linea, base_rate=base)}]
    for nome in BASELINE:
        righe.append({"modello": nome,
                      **V.metrics(y, d[nome].to_numpy(), r=r, line=linea,
                                  base_rate=base)})
    return pd.DataFrame(righe)


def confronto_appaiato(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il margine sul baseline con il suo `t`, **per riga e per cluster**.

    Senza il `t`, "il modello vince" e' una differenza di terza cifra letta come
    un risultato: la Fase 2 lo ha insegnato sui tiri in porta, dove il margine
    sul baseline migliore valeva t = 1,86, cioe' dentro il rumore.

    I due `t` si riportano **sempre in coppia**. Quello per riga tratta 3.778
    squadre-partita come indipendenti e non lo sono; quello per cluster
    raggruppa per `matchId` ed e' l'unita' onesta.
    """
    from . import validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    e_mod = np.abs(y - d["lam"].to_numpy())

    righe = []
    for nome in BASELINE:
        e_b = np.abs(y - d[nome].to_numpy())
        # `paired_t` ritorna (somma, t), NON (t, p): scambiarli e' silenzioso.
        _s, t_riga = V.paired_t(e_b, e_mod)
        _s, t_clu = V.paired_t(e_b, e_mod, cluster=d["matchId"].to_numpy())
        delta = float((e_b - e_mod).mean())
        righe.append({"baseline": nome,
                      "mae_baseline": float(e_b.mean()),
                      "mae_modello": float(e_mod.mean()),
                      "delta_mae": delta,
                      "t_per_riga": t_riga,
                      "t_per_cluster": t_clu,
                      "rapporto": t_clu / t_riga if t_riga else float("nan")})
    return pd.DataFrame(righe)


def per_stagione(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Cinque quasi-repliche invece di un numero solo.

    **Il MAE pooled non e' confrontabile fra stagioni**: il livello si muove del
    5,5%, e un MAE assoluto piu' basso puo' voler dire soltanto che quella
    stagione si tirava di meno. Il MAE **relativo** e' la colonna da leggere per
    il confronto orizzontale.

    E il segno del margine per stagione dice una cosa che il `t` pooled non
    contiene: cinque segni concordi sono un'evidenza diversa da un `t` pooled
    dello stesso valore.
    """
    from . import validate as V

    d = _valutabili(wf)
    righe = []
    for st, g in d.groupby("stagione"):
        y = g[TARGET].to_numpy(dtype=float)
        lam = g["lam"].to_numpy()
        e_mod = np.abs(y - lam)
        e_b = np.abs(y - g[V.BEST_BASELINE].to_numpy())
        _s, t = V.paired_t(e_b, e_mod, cluster=g["matchId"].to_numpy())
        righe.append({
            "stagione": st, "n": len(g),
            "media_osservata": float(y.mean()),
            "mae": float(e_mod.mean()),
            "mae_relativo": float(e_mod.mean() / y.mean()),
            "bias": float((lam - y).mean()),
            "corr": float(np.corrcoef(y, lam)[0, 1]),
            "delta_su_baseline": float((e_b - e_mod).mean()),
            "t_per_cluster": t,
            "vince": bool(e_mod.mean() < e_b.mean()),
        })
    return pd.DataFrame(righe)


def dispersione_tiri(wf: pd.DataFrame | None = None) -> dict:
    """`r` della NB2 sui tentativi, condizionata a lambda.

    Sui tiri in porta vale 26,0. Sui tentativi non e' noto e **non si eredita**:
    un `r` sotto `dispersion.R_SUSPICIOUS` non e' un risultato ma il sintomo di
    un errore di specificazione, ed e' cosi' che va letto se compare.
    """
    from . import dispersion as D

    d = _valutabili(wf)
    return D.conditional_dispersion(d[TARGET].to_numpy(dtype=float),
                                    d["lam"].to_numpy())


def forma_predittiva(wf: pd.DataFrame | None = None) -> dict:
    """PIT randomizzato e copertura: la forma, non solo la media.

    E' il controllo che la pendenza di calibrazione **non** fa. Su un conteggio
    a media 12,6 la coda conta piu' che sui gol, ed e' li' che vivono le linee
    16.5 e 8.5.
    """
    from . import validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    lam = d["lam"].to_numpy()
    r = V.walkforward_r(y, lam, d["date"])
    return {"pit": V.pit_uniformity(V.pit(y, lam, r=r)),
            "copertura": V.interval_coverage(y, lam, r=r),
            "r_mediana": float(np.median(r))}


def brier_per_linea(wf: pd.DataFrame | None = None,
                    linee=T.LINEE_TIRI) -> pd.DataFrame:
    """Brier del modello e del baseline migliore su tutte le linee dichiarate.

    Una linea sola sarebbe un risultato scelto: la Fase 4 lo ha gia' stabilito
    misurando su quattro soglie invece che su una.
    """
    from . import dispersion as D, validate as V

    d = _valutabili(wf)
    y = d[TARGET].to_numpy(dtype=float)
    lam = d["lam"].to_numpy()
    lam_b = d[V.BEST_BASELINE].to_numpy()
    r = V.walkforward_r(y, lam, d["date"])

    righe = []
    for ln in linee:
        yb = (y > ln).astype(float)
        base = V.walkforward_base_rate(y, d["date"], line=ln)
        righe.append({
            "linea": ln,
            "tasso_base": float(yb.mean()),
            "brier_modello": V.brier(yb, D.p_over(lam, ln, r)),
            "brier_baseline": V.brier(yb, D.p_over(lam_b, ln, r)),
            "brier_tasso_base": V.brier(yb, base),
        })
    out = pd.DataFrame(righe)
    out["vince_su_baseline"] = out["brier_modello"] < out["brier_baseline"]
    out["vince_su_tasso_base"] = out["brier_modello"] < out["brier_tasso_base"]
    return out


def segmenti(wf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il modello per campo, terzile di lambda e meta' di stagione.

    La Fase 4 ha trovato che sui tiri in porta il modello perde nel **terzile
    alto**, ed e' lo shrinkage della ridge: le squadre che tirano molto sono
    quelle che il ritorno alla media penalizza. Se il segno si ripete qui, e'
    la quarta misura dello stesso effetto e **non va corretta**.
    """
    from . import validate as V

    d = _valutabili(wf)
    d["_terzile"] = pd.qcut(d["lam"], 3, labels=["basso", "medio", "alto"])
    d["_meta"] = np.where(d["team_match_idx"] <= 19, "1a meta'", "2a meta'")
    d["_campo"] = np.where(d["is_home"].astype(bool), "casa", "trasferta")

    righe = []
    for nome, col in (("campo", "_campo"), ("terzile lambda", "_terzile"),
                      ("meta' stagione", "_meta")):
        for val, g in d.groupby(col, observed=True):
            y = g[TARGET].to_numpy(dtype=float)
            e_mod = np.abs(y - g["lam"].to_numpy())
            e_b = np.abs(y - g[V.BEST_BASELINE].to_numpy())
            righe.append({
                "segmento": nome, "valore": str(val), "n": len(g),
                "mae_modello": float(e_mod.mean()),
                "mae_baseline": float(e_b.mean()),
                "delta": float((e_b - e_mod).mean()),
                "bias": float((g["lam"].to_numpy() - y).mean()),
                "vince": bool(e_mod.mean() < e_b.mean()),
            })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# V3 — i predittori da dati evento, ritestati sul nuovo bersaglio
# --------------------------------------------------------------------------
#: La cache dei nove walk-forward (base + otto candidati) per cinque stagioni.
#: Costa ~3 minuti a `--force`, pochi secondi da qui.
CACHE_PRED = config.processed_league_dir() / "fase12_v3_predittori.parquet"


def predittori_per_stagione(stagioni=None) -> pd.DataFrame:
    """La tabella dei predittori, costruita **una stagione per volta**.

    **Non si costruisce sul concatenato**, ed e' il difetto che V0 ha
    anticipato: `pre_match_ewm` raggruppa per `team`, che e' un nome e si ripete
    fra stagioni, quindi la prima giornata di settembre 2023 riceverebbe una
    media a decadimento dominata da maggio 2023 (peso 0,57 a 110 giorni), cioe'
    da una rosa che non esiste piu'. Sarebbe l'argomento di E3 sul walk-forward,
    applicato un livello piu' in basso.

    Un test lo blocca pretendendo che la **prima partita di ogni stagione** abbia
    predittori nulli: sul concatenato non lo sarebbero.
    """
    from . import walkforward as wf

    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    u = T.universo(stagioni)
    pezzi = []
    for st in stagioni:
        d = wf.build_predictors(u[u["stagione"] == st].copy())
        d["stagione"] = st
        pezzi.append(d)
    return pd.concat(pezzi, ignore_index=True)


def previsioni_predittori(stagioni=None, force: bool = False,
                          verbose: bool = True) -> pd.DataFrame:
    """I nove walk-forward (base + otto candidati) sul bersaglio `shots`.

    Come in 6D, le previsioni si calcolano **una volta sola** su tutte le righe
    che ne hanno una, e i regimi si applicano dopo: ricalcolarle per regime
    renderebbe i tre esiti non confrontabili.
    """
    if CACHE_PRED.is_file() and not force:
        return pd.read_parquet(CACHE_PRED)

    from . import predictor_power as PP

    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    dfp = predittori_per_stagione(stagioni)
    pezzi = []
    for st in stagioni:
        if verbose:
            print(f"  {st}...")
        p = PP.previsioni(dfp[dfp["stagione"] == st].copy(), verbose=False,
                          target=TARGET)
        p["stagione"] = st
        pezzi.append(p)
    out = pd.concat(pezzi, ignore_index=True)
    CACHE_PRED.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE_PRED, index=False)
    return out


def confronto_predittori(prev: pd.DataFrame | None = None,
                         regimi=None) -> pd.DataFrame:
    """Il guadagno fuori campione di ciascun candidato, per regime.

    **`df=None` di proposito**, quindi senza i due numeri in campione della 6D.
    Non e' una dimenticanza: `d_ins` li' stimava su tutte le righe di **una**
    stagione, e la versione multi-stagione richiederebbe un fit poolato che
    attraversa l'estate — cioe' esattamente cio' che V1 ha deciso di non fare.
    Il tetto in campione resta quello della 6D, su un bersaglio diverso, e non
    si eredita: e' dichiarato fra le domande aperte invece di essere fabbricato.
    """
    from . import predictor_power as PP

    prev = previsioni_predittori() if prev is None else prev
    regimi = tuple(PP.REGIMI) if regimi is None else tuple(regimi)
    pezzi = []
    for r in regimi:
        c = PP.confronto(prev, r, target=TARGET)
        c["regime"] = r
        c["n_righe"] = int(PP.maschera(prev, r).sum())
        pezzi.append(c)
    return pd.concat(pezzi, ignore_index=True)


def segno_per_stagione(prev: pd.DataFrame | None = None,
                       regime: str = "maturo") -> pd.DataFrame:
    """Il `t` di ciascun candidato, stagione per stagione.

    Cinque `t` con lo stesso segno sono un'evidenza diversa da un `t` pooled
    dello stesso valore, e la seconda non si legge dalla prima. E' la stessa
    lettura che V1 applica al margine sul baseline.
    """
    from . import predictor_power as PP

    prev = previsioni_predittori() if prev is None else prev
    righe = []
    for st, g in prev.groupby("stagione"):
        c = PP.confronto(g, regime, target=TARGET)
        for _, r in c.iterrows():
            righe.append({"stagione": st, "predittore": r["predittore"],
                          "t": r["t"], "d_riga": r["d_riga"], "n": r["n"]})
    out = pd.DataFrame(righe)
    pivot = out.pivot(index="predittore", columns="stagione", values="t")
    pivot["positivi"] = (pivot > 0).sum(axis=1)
    pivot["max_assoluto"] = pivot.drop(columns=["positivi"]).abs().max(axis=1)
    return pivot.reset_index()


def contesto_regimi(prev: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il modello base contro i baseline stupidi, dentro ciascun regime.

    E' la premessa del blocco, **verificata invece che assunta**: se nel regime
    acerbo il modello non staccasse i baseline, un predittore incrementale
    avrebbe piu' spazio per esistere. I baseline vengono dal walk-forward di V1,
    gia' calcolati per stagione, invece di essere ricalcolati poolando.
    """
    from . import predictor_power as PP, validate as V

    prev = previsioni_predittori() if prev is None else prev
    wf1 = walkforward_tiri().set_index(["matchId", "team"])

    righe = []
    for r in PP.REGIMI:
        sub = prev[PP.maschera(prev, r)]
        idx = list(zip(sub["matchId"], sub["team"]))
        y = sub[TARGET].to_numpy(dtype=float)
        preds = {V.MODEL_NAME: sub[f"lam_{PP.BASE}"].to_numpy(dtype=float)}
        for nome in BASELINE:
            preds[nome] = np.array([wf1[nome].get(k, np.nan) for k in idx])

        ok = ~np.isnan(np.vstack(list(preds.values()))).any(axis=0)
        for nome, lam in preds.items():
            e = np.abs(y[ok] - lam[ok])
            # La log-verosimiglianza per riga e' l'unita' in cui `mde_riga` e'
            # espresso: senza, il MDE non si puo' rapportare a niente e i MDE di
            # due bersagli diversi sembrano confrontabili quando non lo sono.
            ll = PP._ll(y[ok], lam[ok])
            righe.append({"regime": r, "modello": nome, "n": int(ok.sum()),
                          "mae": float(e.mean()),
                          "ll_per_riga": float(ll.mean())})
    out = pd.DataFrame(righe)
    base = out[out["modello"] == V.MODEL_NAME].set_index("regime")
    out["delta_vs_modello"] = out["mae"] - out["regime"].map(base["mae"])
    out["delta_ll_vs_modello"] = (out["regime"].map(base["ll_per_riga"])
                                  - out["ll_per_riga"])
    return out


def mde_relativo(prev: pd.DataFrame | None = None) -> pd.DataFrame:
    """Il MDE **in rapporto al guadagno del modello sul baseline migliore**.

    **I MDE di due bersagli diversi NON sono confrontabili in unita' assolute**,
    ed e' un errore che questo blocco ha commesso e corretto: sui tentativi la
    log-verosimiglianza Poisson ha una varianza per riga molto maggiore che sui
    tiri in porta (media 12,6 contro 4,0), quindi cinque volte le righe non
    bastano a compensare e il MDE assoluto **peggiora** invece di migliorare.

    L'unita' confrontabile e' adimensionale: quanto vale il MDE rispetto a cio'
    che il modello guadagna sul baseline migliore, **nella stessa unita'** di
    log-verosimiglianza per riga. Un MDE pari al 10% di quel guadagno significa
    che il test vede un predittore che valga un decimo del modello intero.
    """
    from . import predictor_power as PP, validate as V

    prev = previsioni_predittori() if prev is None else prev
    ctx = contesto_regimi(prev)
    conf = confronto_predittori(prev)

    righe = []
    for r in PP.REGIMI:
        g = ctx[ctx["regime"] == r].set_index("modello")
        guadagno = float(g.loc[V.BEST_BASELINE, "delta_ll_vs_modello"])
        mde = float(conf[conf["regime"] == r]["mde_riga"].min())
        righe.append({
            "regime": r,
            "n": int(conf[conf["regime"] == r]["n"].iloc[0]),
            "mde_riga": mde,
            "guadagno_modello_su_baseline": guadagno,
            "mde_in_quota_del_guadagno": mde / guadagno if guadagno else float("nan"),
        })
    return pd.DataFrame(righe)


def ratings(wf: pd.DataFrame | None = None, stagione: str | None = None,
            alpha: float | None = None) -> pd.DataFrame:
    """Forza offensiva e difensiva sui tentativi, a fine stagione.

    **E' una descrizione, non una previsione**: il fit usa tutta la stagione, e
    serve a leggere il modello, non a validarlo. La scala e' quella di
    `level_chain.ratings_per_campo` — cioe' l'**avversario medio in trasferta**,
    come `fig5` — e non e' il campo neutro: la Fase 6A ha dovuto documentarlo
    dopo averlo scoperto, e qui si dichiara subito.
    """
    from . import model_team as MT, validate as V

    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    u = T.universo([stagione])
    d = _valutabili(wf)
    a = (float(d.loc[d["stagione"] == stagione, "alpha"].median())
         if alpha is None and "alpha" in d.columns else alpha)
    m = MT.TeamModel(alpha=a or V.ALPHA_GRID[2], target=TARGET).fit(u)
    r = m.ratings()
    r["tentativi_attesi_trasferta"] = np.exp(m.mu_ + r["attack"]
                                             + r["defence"].mean())
    r["stagione"] = stagione
    r["vantaggio_campo"] = float(np.exp(m.home_advantage))
    return r
