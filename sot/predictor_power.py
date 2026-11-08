# -*- coding: utf-8 -*-
"""Fase 6D — i predittori dove l'effetto attacco e' debolmente identificato.

Gli otto candidati di `walkforward.CANDIDATES` sono stati scartati in Fase 2
misurandone il valore **incrementale** contro un effetto attacco con trenta e
piu' giornate di storia alle spalle. Sono medie mobili della squadra stessa:
in quel regime sono collineari con l'effetto attacco, e la conclusione "non
aggiungono informazione, la ripetono" vale **li'**. L'ipotesi mai testata e'
che paghino dove quell'effetto e' ancora acerbo.

Qui cambia **soltanto l'insieme di valutazione**. Le previsioni walk-forward
sono le stesse — stesso split per data, stessa griglia di alpha scelta sul solo
passato, stesse medie mobili — e nessun parametro viene ristimato sul regime:
restringere la valutazione dopo aver ristimato qualcosa sul sottoinsieme
sarebbe un altro esperimento, non lo stesso in un regime diverso.

Il modulo aggiunge quello che in Fase 2 mancava: la **potenza**. Su cento righe
un `t` sotto soglia non dice "il predittore non serve", dice "questo test non
l'avrebbe visto"; le due frasi si distinguono solo calcolando contro quale
effetto il test avrebbe avuto una probabilita' decente di rifiutare. Ogni `t`
qui dentro esce accompagnato dall'effetto minimo rilevabile e dalla potenza
contro due alternative **dichiarate in anticipo**:

* l'effetto per riga che lo stesso predittore mostra nel regime maturo — cioe'
  "se qui valesse quanto vale li', lo vedremmo?";
* il suo guadagno in campione **stimato sulle sole righe del regime**, corretto
  per il sovradattamento: e' il tetto, perche' nessuno stimatore fuori campione
  puo' rendere, su quelle righe, piu' di un coefficiente scelto guardandole
  tutte.

Attenzione al secondo, che e' facile leggere male. Aggiungere un parametro
libero a un modello annidato **alza sempre** la verosimiglianza in campione:
il guadagno grezzo non e' un tetto, e' un tetto piu' rumore. Sotto l'ipotesi
nulla il doppio di quel guadagno e' un chi-quadro con un grado di liberta',
quindi in media vale 0.5 per parametro. Da qui le due letture riportate: il
**p del rapporto di verosimiglianza** (in campione, non predittivo) e il tetto
al netto dei 0.5 punti di sovradattamento, che e' la correzione dell'AIC.

Una nota sulla soglia. `T_KEEP = 2.0` e' dichiarata in Fase 2 e non si tocca:
cambiarla adesso, dopo aver visto i `t`, e' esattamente la cosa che la
dichiarazione anticipata serve a impedire. La correzione per la molteplicita'
resta quella di Fase 2 — il massimo di otto statistiche indipendenti sotto
l'ipotesi nulla vale in media 1.42, quindi un massimo di quell'ordine non e'
una scoperta — qui resa esatta da `p_del_massimo`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import integrate, stats

from . import (baselines as bl, config, dispersion, model_team as MT,
               validate as V, walkforward as wf)

# --------------------------------------------------------------------------
# Costanti dichiarate in anticipo. Sono le stesse della Fase 2: se un giorno
# divergessero, i due test non sarebbero piu' confrontabili e il confronto
# "accanto, non al posto" perderebbe senso. `tests/test_predictor_power.py`
# verifica che `run_phase2.py` usi questa e non una copia.
# --------------------------------------------------------------------------
T_KEEP = 2.0                    # soglia sul t appaiato per tenere un predittore
ALPHA_INS = 12.0                # alpha del confronto in campione (Fase 2)
POTENZA_OBIETTIVO = 0.80        # potenza a cui si riporta l'effetto minimo
FAMIGLIA = len(wf.CANDIDATES)   # otto candidati testati insieme
BASE = "base"

# Regimi come intervalli di `team_match_idx`, estremi inclusi.
#
# Attenzione a leggere i nomi per quello che sono: "acerbo" e' *le prime otto
# partite di ciascuna squadra*, ma le prime tre non hanno previsione — a quelle
# date il campionato non ha ancora le 30 partite che `date_splits` pretende
# prima di stimare qualsiasi cosa. L'insieme valutabile parte quindi dalla
# quarta partita, e va detto: e' un troncamento del regime, non una scelta.
#
# "acerbo" e "maturo" **si sovrappongono** sulle partite 6-8. Il regime
# disgiunto, che contiene solo righe mai valutate prima, e' il terzo.
REGIMI: dict[str, tuple[int, int]] = {
    "acerbo": (1, 8),
    "maturo": (config.BURN_IN_ROUND, 38),
    "acerbo disgiunto": (1, config.BURN_IN_ROUND - 1),
}

_KEY = ["matchId", "team"]


# --------------------------------------------------------------- walk-forward
def previsioni(df: pd.DataFrame, candidati: tuple[str, ...] | None = None,
               verbose: bool = True, target: str = bl.TARGET) -> pd.DataFrame:
    """Un walk-forward per il modello base e uno per ciascun candidato.

    Ritorna una tabella larga con una colonna `lam_<nome>` per modello, su
    **tutte** le righe che hanno una previsione, non solo su quelle del
    burn-in: quali righe valutare e' una decisione successiva, e tenerla
    separata dal calcolo e' l'unico modo di applicare piu' regimi alle stesse
    identiche previsioni.

    `target` esiste dalla Fase 12 / V3 e **il default non va cambiato qui**:
    tutto cio' che la Fase 6D ha pubblicato lo assume, e un test verifica che
    con il default i numeri di `reports/phase6_predittori.csv` si riproducano a
    1e-12. La colonna del bersaglio esce **col proprio nome**, mai rinominata in
    `sot` — e' la stessa garanzia di `walkforward_predict`.
    """
    candidati = tuple(wf.CANDIDATES) if candidati is None else tuple(candidati)

    if verbose:
        print(f"  walk-forward: base + {len(candidati)} candidati")
    base = (V.walkforward_predict(df, extra=(), target=target)
            .sort_values(_KEY).reset_index(drop=True))

    out = base[["matchId", "date", "team", "opponent", "is_home",
                "team_match_idx", target, "alpha"]].copy()
    out[f"lam_{BASE}"] = base["lam"].to_numpy()

    for name in candidati:
        p = (V.walkforward_predict(df, extra=(name,), target=target)
             .sort_values(_KEY).reset_index(drop=True))
        if not p[_KEY].equals(base[_KEY]):
            raise ValueError(f"{name}: righe disallineate rispetto al modello base")
        out[f"lam_{name}"] = p["lam"].to_numpy()
        if verbose:
            print(f"    {name} fatto")

    return out


def maschera(prev: pd.DataFrame, regime: str) -> np.ndarray:
    """Righe del regime, come maschera booleana su `prev`."""
    lo, hi = REGIMI[regime]
    return prev["team_match_idx"].between(lo, hi).to_numpy()


# -------------------------------------------------------------------- potenza
def potenza(delta: float, se: float, t_crit: float = T_KEEP) -> float:
    """Probabilita' di superare la soglia se l'effetto vero per riga e' `delta`.

    Test a una coda: il predittore si tiene solo se **migliora**. Con delta = 0
    questa funzione restituisce la dimensione del test, non zero — che e' il
    modo giusto di leggere una potenza bassa: il 2.3% e' il pavimento, e una
    potenza del 7% significa che il test e' appena sopra il caso.
    """
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    return float(stats.norm.sf(t_crit - delta / se))


def effetto_minimo(se: float, t_crit: float = T_KEEP,
                   obiettivo: float = POTENZA_OBIETTIVO) -> float:
    """Effetto per riga rilevabile con probabilita' `obiettivo` (il MDE).

    E' il numero che rende leggibile un non-rifiuto: se il MDE e' piu' grande
    di qualunque effetto plausibile, il test non poteva concludere niente e
    dirlo "non significativo" e' fuorviante.
    """
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    return float((t_crit + stats.norm.ppf(obiettivo)) * se)


def soglia_sidak(k: int = FAMIGLIA, alpha: float = 0.05) -> float:
    """Soglia sul `t` che tiene al `alpha` **di famiglia** su k test a una coda."""
    return float(stats.norm.isf(1.0 - (1.0 - alpha) ** (1.0 / k)))


def p_del_massimo(t_max: float, k: int = FAMIGLIA) -> float:
    """P(massimo di k normali standard > t_max): la correzione, resa esatta.

    E' la versione calcolata dell'argomento gia' usato in Fase 2 ("su otto
    candidati un massimo di 1.42 e' quanto ci si aspetta"). Assume indipendenza
    fra i candidati: qui non la si ha — sono medie mobili correlate fra loro —
    e la correlazione rende il test **meno** severo del dovuto, quindi il p
    riportato e' conservativo nella direzione sbagliata per chi volesse
    dichiarare una scoperta.
    """
    return float(1.0 - stats.norm.cdf(t_max) ** k)


GDL_EXTRA = 1   # un predittore = un parametro libero in piu'


def p_rapporto_verosimiglianza(d_ins: float, gdl: int = GDL_EXTRA) -> float:
    """p del test del rapporto di verosimiglianza **in campione**.

    Sotto l'ipotesi nulla che il coefficiente sia zero, `2 * d_ins` e' un
    chi-quadro con `gdl` gradi di liberta'. E' il test piu' potente che queste
    righe permettano — usa i loro stessi valori per stimare il coefficiente —
    e proprio per questo **non e' una prova di valore predittivo**: qui serve
    solo come limite superiore. Se non rifiuta nemmeno lui, non c'e' un test
    piu' sensibile da provare dentro questa specificazione.
    """
    return float(stats.chi2.sf(2.0 * max(d_ins, 0.0), gdl))


def tetto_corretto(d_ins: float, gdl: int = GDL_EXTRA) -> float:
    """Guadagno in campione al netto del sovradattamento atteso (0.5 per gdl).

    E' la correzione dell'AIC, e serve a non usare come alternativa nel calcolo
    della potenza un effetto che sotto l'ipotesi nulla si otterrebbe comunque.
    Troncato a zero: un tetto negativo non e' un'alternativa sensata per un
    test a una coda.
    """
    return float(max(d_ins - 0.5 * gdl, 0.0))


def t_atteso_massimo(k: int = FAMIGLIA) -> float:
    """Valore atteso del massimo di k normali standard indipendenti.

    Per k = 8 vale 1.4236: e' il termine di paragone con cui in Fase 2 si e'
    letto il t = 1.42 del possesso.
    """
    hi = integrate.quad(lambda x: 1.0 - stats.norm.cdf(x) ** k, 0.0, 40.0)[0]
    lo = integrate.quad(lambda x: stats.norm.cdf(x) ** k, -40.0, 0.0)[0]
    return float(hi - lo)


# ------------------------------------------------------------------ confronto
def _ll(y: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """Log-verosimiglianza per riga, Poisson (r = R_MAX), come in Fase 2."""
    return dispersion.nb2_loglik(np.asarray(y, dtype=float),
                                 np.asarray(lam, dtype=float), dispersion.R_MAX)


def confronto(prev: pd.DataFrame, regime: str,
              df: pd.DataFrame | None = None,
              riferimento: pd.DataFrame | None = None,
              candidati: tuple[str, ...] | None = None,
              target: str = bl.TARGET) -> pd.DataFrame:
    """Guadagno fuori campione di ciascun candidato sulle righe del regime.

    `df` (la tabella con i predittori) serve ai due confronti **in campione**;
    senza, quelle colonne restano assenti. `riferimento` e' la tabella di un
    altro regime — in pratica sempre quella del maturo — da cui si prende
    l'effetto per riga contro cui calcolare la potenza.

    I due numeri in campione non sono la stessa cosa e vanno letti diversi:

    * `d_ins` stima su **tutte** le 760 righe con `as_of` a fine stagione,
      esattamente come la Fase 2, e valuta sulle righe del regime. Serve alla
      continuita' col report precedente, ma non e' un tetto: il decadimento a
      150 giorni pesa le prime giornate per circa un terzo, quindi quei
      coefficienti non sono scelti per il regime acerbo.
    * `d_ins_regime` stima sulle **sole righe del regime**, che e' il tetto
      vero: un coefficiente scelto guardando proprio quelle righe. Se resta
      negativo, il predittore non ha niente da dare li' dentro, e la potenza
      non c'entra piu'.
    """
    if candidati is None:
        candidati = tuple(c for c in wf.CANDIDATES if f"lam_{c}" in prev.columns)

    m = maschera(prev, regime)
    sub = prev[m]
    y = sub[target].to_numpy(dtype=float)
    ll0 = _ll(y, sub[f"lam_{BASE}"].to_numpy())

    ins0 = ins0_reg = None
    if df is not None:
        d_in = _righe_in_campione(df, sub)
        y_in = d_in[target].to_numpy(dtype=float)
        teams = sorted(set(df["team"]) | set(df["opponent"]))
        as_of = d_in["date"].max()

        def _fit(extra, solo_regime):
            # `target=target` NON e' decorativo: senza, il parametro sembrerebbe
            # funzionare — `y_in` e' gia' del bersaglio giusto — e il modello
            # verrebbe stimato su `sot` mentre lo si valuta su un altro
            # bersaglio. Un test lo blocca pretendendo che la verosimiglianza
            # in campione CAMBI al cambiare del target.
            mod = MT.TeamModel(alpha=ALPHA_INS, extra=extra, target=target)
            return (mod.fit(d_in, as_of=as_of, teams=teams) if solo_regime
                    else mod.fit(df, teams=teams))

        ins0 = float(np.sum(_ll(y_in, _fit((), False).predict(d_in))))
        ins0_reg = float(np.sum(_ll(y_in, _fit((), True).predict(d_in))))

    rif = None if riferimento is None else riferimento.set_index("predittore")["d_riga"]

    rows = []
    for name in candidati:
        d = _ll(y, sub[f"lam_{name}"].to_numpy()) - ll0
        n = len(d)
        se = float(d.std(ddof=1) / np.sqrt(n))
        media = float(d.mean())
        t = media / se if se > 0 else float("nan")

        row = {"predittore": name, "n": n, "d_oos": float(d.sum()),
               "d_riga": media, "se_riga": se, "t": t,
               "mde_riga": effetto_minimo(se), "mde_oos": effetto_minimo(se) * n,
               "tenuto": bool(t > T_KEEP)}

        if ins0 is not None:
            row["d_ins"] = float(np.sum(_ll(y_in, _fit((name,), False)
                                            .predict(d_in)))) - ins0
            row["d_ins_regime"] = float(np.sum(_ll(y_in, _fit((name,), True)
                                                   .predict(d_in)))) - ins0_reg
            row["p_lr"] = p_rapporto_verosimiglianza(row["d_ins_regime"])
            row["tetto"] = tetto_corretto(row["d_ins_regime"])
            row["potenza_vs_tetto"] = potenza(row["tetto"] / n, se)

        if rif is not None:
            row["d_riga_maturo"] = float(rif.get(name, np.nan))
            row["potenza_vs_maturo"] = potenza(row["d_riga_maturo"], se)

        rows.append(row)

    return pd.DataFrame(rows).sort_values("t", ascending=False).reset_index(drop=True)


def righe_del_regime(df: pd.DataFrame, prev: pd.DataFrame,
                     regime: str) -> pd.DataFrame:
    """Le righe della tabella dei predittori valutate in un regime."""
    return _righe_in_campione(df, prev[maschera(prev, regime)])


def penalita(df_fit: pd.DataFrame, extra: tuple[str, ...] = (),
             alpha: float = ALPHA_INS, teams: list | None = None,
             target: str = bl.TARGET) -> dict:
    """Verosimiglianza grezza, penalita' ridge e coefficiente, dallo stesso fit.

    Serve a spiegare un fatto che altrimenti sembra un errore: nel regime
    maturo aggiungere un predittore fa **scendere** la verosimiglianza grezza
    in campione. Non e' un bug dell'ottimizzatore. L'obiettivo minimizzato non
    e' la verosimiglianza, e' verosimiglianza pesata **piu' la penalita' ridge**
    su attacco e difesa; un predittore collineare con l'effetto attacco compra
    una riduzione della penalita' e paga in adattamento. E' la stessa
    sostituzione che la Fase 2 aveva dedotto dal risultato fuori campione, qui
    visibile direttamente nei due termini dell'obiettivo.
    """
    teams = teams if teams is not None else sorted(
        set(df_fit["team"]) | set(df_fit["opponent"]))
    as_of = df_fit["date"].max()
    m = MT.TeamModel(alpha=alpha, extra=extra, target=target).fit(
        df_fit, as_of=as_of, teams=teams)
    y = df_fit[target].to_numpy(dtype=float)
    lam = m.predict(df_fit)
    w = 0.5 ** (np.clip((as_of - df_fit["date"]).dt.total_seconds().to_numpy()
                        / 86400.0, 0.0, None) / m.half_life)
    pen = float(alpha * np.sum(m._penalty_mask() * m.beta_ ** 2))
    return {"loglik": float(np.sum(_ll(y, lam))), "penalita": pen,
            "obiettivo": float(np.sum(w * (lam - y * np.log(lam))) + pen),
            "coef": dict(m.extra_coefs)}


def _righe_in_campione(df: pd.DataFrame, sub: pd.DataFrame) -> pd.DataFrame:
    """Le stesse righe del regime, prese dalla tabella dei predittori."""
    key = pd.MultiIndex.from_frame(sub[_KEY])
    sel = pd.MultiIndex.from_frame(df[_KEY]).isin(key)
    out = df[sel]
    if len(out) != len(sub):
        raise ValueError(f"righe in campione {len(out)} contro {len(sub)} valutate")
    return out


# ------------------------------------------------- il contesto: baseline stupidi
def contesto(prev: pd.DataFrame, df: pd.DataFrame, regime: str,
             target: str = bl.TARGET) -> pd.DataFrame:
    """Modello base e baseline sulle stesse righe del regime.

    Non e' un ornamento: la premessa del blocco e' che nel regime acerbo
    l'effetto attacco sia **debolmente identificato**, e quella premessa si
    verifica solo guardando quanto il modello batte "media squadra + campo"
    li' dentro rispetto a quanto lo batte a stagione matura. Se nel regime
    acerbo il modello non staccasse i baseline, il vantaggio incrementale di un
    predittore avrebbe piu' spazio per esistere — ed e' proprio l'ipotesi da
    testare.
    """
    blw = (V.walkforward_baselines(df, target=target)
           .sort_values(_KEY).reset_index(drop=True))
    m = maschera(prev, regime)
    sub = prev[m]
    key = pd.MultiIndex.from_frame(sub[_KEY])
    be = blw.set_index(pd.MultiIndex.from_frame(blw[_KEY])).loc[key]

    y = sub[target].to_numpy(dtype=float)
    preds = {V.MODEL_NAME: sub[f"lam_{BASE}"].to_numpy(dtype=float)}
    for name in bl.BASELINES:
        preds[name] = be[name].to_numpy(dtype=float)

    rows = []
    ref_ll = _ll(y, preds[V.MODEL_NAME])
    for name, lam in preds.items():
        ll = _ll(y, lam)
        d = ref_ll - ll
        se = d.std(ddof=1) / np.sqrt(len(d)) if name != V.MODEL_NAME else 0.0
        rows.append({
            "modello": name, "n": len(y),
            "mae": float(np.mean(np.abs(y - lam))),
            "loglik": float(np.sum(ll)),
            "d_loglik_vs_modello": float(d.sum()),
            "t_vs_modello": float(d.mean() / se) if se > 0 else float("nan"),
        })
    return pd.DataFrame(rows).set_index("modello")
