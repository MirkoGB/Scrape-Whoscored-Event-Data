# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2 — 1X2 e over/under, valutati.

R1 ha consegnato la congiunta e `rho = 0`. Questo blocco la legge come
**previsione** e la misura: RPS, log-loss, Brier per soglia, calibrazione, contro
baseline che non sono di cortesia.

**La metrica principale e' l'RPS e non la log-loss**, ed e' una scelta con un
motivo: l'esito 1X2 e' **ordinale**. Fra `1` e `2` c'e' `X`, e una previsione che
sbaglia dando probabilita' al pareggio sbaglia meno di una che la da' alla
vittoria opposta. La log-loss non lo sa — tratta le tre classi come etichette
scambiabili — e infatti si riporta accanto, non al posto.

**Il confronto e' a composizione fissata** (vincolo 6). Ogni baseline e' una
coppia di lambda, e viene composta **con la stessa** `risultato.congiunta` del
modello: se il modello passasse per la congiunta e i baseline per una regola
diversa, il confronto misurerebbe la composizione invece del lambda, che e'
l'errore che renderebbe il blocco privo di significato.

> **Vincolo 3, e non e' aggirabile.** Qui non si valuta nessuna scommessa. Non
> esistono quote di mercato nel repository, e le uniche disponibili sarebbero
> quelle generate da questo stesso modello: confrontarcisi e' circolare, ed e' il
> codice che sta in `legacy/`. Si misura **quanto la previsione e' buona**, non
> quanto varrebbe puntarci. Un test vieta che in questo modulo compaia una quota.

**Il pavimento sui lambda dei baseline e' dichiarato** (`PAVIMENTO_LAMBDA`): un
lambda esattamente zero e' un estimatore **degenere**, e su una riga del campione
`media squadra` lo produce mentre la squadra segna davvero. Senza pavimento la
log-loss di quel baseline e' infinita — che non e' un risultato ma un artefatto.
E' lo stesso caso della frequenza storica grezza di E3, trattato allo stesso
modo: si smorza, si dichiara, e si dice quante righe tocca.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config, perimetro as PM, risultato as R

#: Le tre classi, **in ordine**. L'ordine e' la ragione per cui l'RPS esiste: e'
#: cio' che rende `X` intermedio fra `1` e `2`. Non riordinare.
CLASSI = ("1", "X", "2")

#: Le linee di gol totali. **Dichiarate, non scelte guardando i dati**: la 2.5 e'
#: la linea di mercato standard, la 1.5 e la 3.5 la circondano. `difesa.LINEA_GOL`
#: vale 1.5 ma e' sui gol di UNA squadra: sono grandezze diverse e non si eredita.
LINEE = (1.5, 2.5, 3.5)

#: Pavimento sui lambda dei baseline. Un baseline che predice esattamente zero
#: non e' un avversario serio, e' un estimatore degenere: vedi la docstring.
PAVIMENTO_LAMBDA = 0.05


def _p_esiti(lam_c, lam_t, rho: float = 0.0) -> np.ndarray:
    """Matrice `(n, 3)` di probabilita' 1X2, nell'ordine di `CLASSI`."""
    return np.array([R.esiti(R.congiunta(a, b, rho))
                     for a, b in zip(np.asarray(lam_c), np.asarray(lam_t))])


def _p_over(lam_c, lam_t, linea: float, rho: float = 0.0) -> np.ndarray:
    return np.array([R.over(R.congiunta(a, b, rho), linea)
                     for a, b in zip(np.asarray(lam_c), np.asarray(lam_t))])


def previsioni(d: pd.DataFrame = None, rho: float = 0.0) -> pd.DataFrame:
    """Le previsioni del modello e dei quattro baseline, sulle stesse partite.

    Ogni candidato esce come tre colonne `p1/pX/p2` piu' una `over_<linea>` per
    ciascuna linea, tutte composte con la **stessa** procedura.
    """
    if d is None:
        p = PM.partite(con_baseline=True)
        d = p[p["validabile"]].copy()

    out = d[["stagione", "matchId", "giornata", "casa", "trasferta",
             "gol_casa", "gol_trasferta", "esito", "gol_totali"]].copy()

    candidati = {"modello": ("lam_casa", "lam_trasferta")}
    for b in PM.BASELINE:
        candidati[b] = (f"{b}_casa", f"{b}_trasferta")

    for nome, (cc, ct) in candidati.items():
        lc = np.maximum(d[cc].to_numpy(float), PAVIMENTO_LAMBDA)
        lt = np.maximum(d[ct].to_numpy(float), PAVIMENTO_LAMBDA)
        pe = _p_esiti(lc, lt, rho if nome == "modello" else 0.0)
        for j, cl in enumerate(CLASSI):
            out[f"{nome}|p{cl}"] = pe[:, j]
        for ln in LINEE:
            out[f"{nome}|over{ln}"] = _p_over(lc, lt, ln)
    return out


def righe_pavimentate(d: pd.DataFrame = None) -> pd.DataFrame:
    """Quante righe il pavimento tocca, per candidato. Si conta, non si assume."""
    if d is None:
        p = PM.partite(con_baseline=True)
        d = p[p["validabile"]]
    righe = []
    for b in PM.BASELINE:
        n = int(((d[f"{b}_casa"] < PAVIMENTO_LAMBDA)
                 | (d[f"{b}_trasferta"] < PAVIMENTO_LAMBDA)).sum())
        righe.append({"candidato": b, "righe_pavimentate": n})
    righe.append({"candidato": "modello",
                  "righe_pavimentate": int(((d["lam_casa"] < PAVIMENTO_LAMBDA)
                                            | (d["lam_trasferta"] < PAVIMENTO_LAMBDA)).sum())})
    return pd.DataFrame(righe)


# ---------------------------------------------------------------------------
# Le metriche
# ---------------------------------------------------------------------------

def rps(p: np.ndarray, esito: np.ndarray) -> np.ndarray:
    """Ranked Probability Score, per riga. **Piu' basso e' meglio.**

    `RPS = somma_k (F_k - O_k)^2 / (K - 1)` sulle cumulate. E' la metrica giusta
    per un esito ordinale: sbagliare dando probabilita' al pareggio costa meno
    che darla alla vittoria opposta, e la log-loss non lo sa.
    """
    p = np.asarray(p, dtype=float)
    o = np.zeros_like(p)
    for j, cl in enumerate(CLASSI):
        o[:, j] = (np.asarray(esito) == cl).astype(float)
    return np.square(np.cumsum(p, axis=1) - np.cumsum(o, axis=1))[:, :-1].sum(axis=1) / (len(CLASSI) - 1)


def logloss(p: np.ndarray, esito: np.ndarray, eps: float = 1e-15) -> np.ndarray:
    """Log-loss multiclasse, per riga. Non sa che le classi sono ordinate."""
    p = np.clip(np.asarray(p, dtype=float), eps, 1.0)
    idx = np.array([CLASSI.index(e) for e in esito])
    return -np.log(p[np.arange(len(idx)), idx])


def brier(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.square(np.asarray(p, dtype=float) - np.asarray(y, dtype=float))


def valutazione(pv: pd.DataFrame = None) -> pd.DataFrame:
    """Il modello contro i quattro baseline, sulle stesse righe, su ogni metrica.

    Si aggiunge un quinto avversario che non e' un modello di squadra: il **tasso
    base 1X2**, cioe' le frequenze storiche delle tre classi. E' il piu' stupido
    possibile, e il vincolo 6 chiede che ci sia.
    """
    pv = previsioni() if pv is None else pv
    esito = pv["esito"].to_numpy()

    righe = []
    for nome in ["modello", *PM.BASELINE, "tasso base 1X2"]:
        if nome == "tasso base 1X2":
            p = _tasso_base(pv)
            # Anche l'over va stimato sul SOLO PASSATO. La media dell'intero
            # campione darebbe a ogni partita la conoscenza di quanti gol si
            # sono segnati nel resto della stagione — vincolo 1, ed e' un errore
            # che questo blocco ha commesso e corretto prima di pubblicare.
            ov = {ln: _tasso_base_over(pv, ln) for ln in LINEE}
        else:
            p = pv[[f"{nome}|p{c}" for c in CLASSI]].to_numpy()
            ov = {ln: pv[f"{nome}|over{ln}"].to_numpy() for ln in LINEE}
        riga = {"candidato": nome,
                "RPS": float(rps(p, esito).mean()),
                "log-loss": float(logloss(p, esito).mean())}
        for ln in LINEE:
            riga[f"Brier O{ln}"] = float(
                brier(ov[ln], (pv["gol_totali"] > ln).to_numpy()).mean())
        righe.append(riga)
    return pd.DataFrame(righe)


def _tasso_base(pv: pd.DataFrame) -> np.ndarray:
    """Le frequenze 1X2 stimate **sul solo passato**, riga per riga.

    Vincolo 1: usare le frequenze dell'intero campione darebbe a ogni partita la
    conoscenza di come e' finito il campionato. E' la stessa correzione che la
    Fase 4 ha applicato a `r` e al tasso base del Brier con `walkforward_base_rate`.
    """
    pv = pv.sort_values(["stagione", "matchId"]).reset_index(drop=True)
    out = np.empty((len(pv), 3))
    for st, sub in pv.groupby("stagione"):
        idx = sub.index.to_numpy()
        e = sub["esito"].to_numpy()
        for i, pos in enumerate(idx):
            passato = e[:i]
            if len(passato) < 30:          # stessa soglia del walk-forward di E3
                out[pos] = np.array([1 / 3, 1 / 3, 1 / 3])
            else:
                out[pos] = [(passato == c).mean() for c in CLASSI]
    # rinormalizza: le frequenze empiriche sommano a 1 per costruzione, ma il
    # ramo uniforme e gli arrotondamenti no.
    return out / out.sum(axis=1, keepdims=True)


def _tasso_base_over(pv: pd.DataFrame, linea: float) -> np.ndarray:
    """La frequenza storica di over, stimata sul solo passato. Vincolo 1."""
    pv = pv.sort_values(["stagione", "matchId"]).reset_index(drop=True)
    out = np.empty(len(pv))
    for st, sub in pv.groupby("stagione"):
        idx = sub.index.to_numpy()
        y = (sub["gol_totali"].to_numpy() > linea).astype(float)
        for i, pos in enumerate(idx):
            out[pos] = 0.5 if i < 30 else y[:i].mean()
    return out


def confronto_appaiato(pv: pd.DataFrame = None,
                       metrica: str = "RPS") -> pd.DataFrame:
    """Differenza appaiata modello - baseline, con `t`. Convenzione del progetto.

    Il segno e' scelto perche' **piu' basso e' meglio** su tutte queste metriche:
    una differenza negativa significa che il modello vince.
    """
    pv = previsioni() if pv is None else pv

    def valori(nome: str) -> np.ndarray:
        """Il vettore per riga della metrica richiesta, per un candidato."""
        if metrica.startswith("Brier O"):
            ln = float(metrica.removeprefix("Brier O"))
            y = (pv["gol_totali"] > ln).to_numpy()
            p = (_tasso_base_over(pv, ln) if nome == "tasso base 1X2"
                 else pv[f"{nome}|over{ln}"].to_numpy())
            return brier(p, y)
        f = {"RPS": rps, "log-loss": logloss}[metrica]
        p = (_tasso_base(pv) if nome == "tasso base 1X2"
             else pv[[f"{nome}|p{c}" for c in CLASSI]].to_numpy())
        return f(p, pv["esito"].to_numpy())

    vm = valori("modello")
    righe = []
    for nome in [*PM.BASELINE, "tasso base 1X2"]:
        diff = vm - valori(nome)
        se = diff.std(ddof=1) / np.sqrt(len(diff))
        # MDE a potenza 80%, due code: (z_0.975 + z_0.80) * SE. E' la lezione
        # della 6D — un `t` piccolo non dice che l'effetto sia zero finche' non
        # si sa quanto grande dovesse essere per essere visto.
        mde = float((stats.norm.isf(0.025) + stats.norm.isf(0.20)) * se)
        righe.append({"baseline": nome, "differenza": float(diff.mean()),
                      "errore standard": float(se),
                      "t": float(diff.mean() / se) if se > 0 else np.nan,
                      "MDE (80%)": mde,
                      "modello vince": bool(diff.mean() < 0),
                      "oltre il rumore": bool(abs(diff.mean()) > mde)})
    return pd.DataFrame(righe)


def dispersione_somma(d: pd.DataFrame = None) -> pd.DataFrame:
    """Quanto ogni candidato fa variare la SOMMA dei due lambda, e a che pro.

    E' la misura che spiega il rovesciamento dell'ordine su over/under, ed e'
    stata fatta perche' la spiegazione scritta prima — «le medie di squadra
    sommate disperdono troppo» — era un'affermazione e non un numero. Il numero
    la corregge: il fatto centrale non e' la dispersione di un candidato, e' che
    **il totale di gol di una partita e' quasi imprevedibile per tutti**. Con una
    correlazione dell'ordine di 0,1, ogni dispersione in piu' e' quasi tutta
    varianza pagata a vuoto, e vince chi ne mette meno.
    """
    if d is None:
        p = PM.partite(con_baseline=True)
        d = p[p["validabile"]]
    tot = d["gol_totali"].to_numpy(float)

    righe = [{"candidato": "**osservato**", "media": float(tot.mean()),
              "sd": float(tot.std(ddof=1)), "corr con il totale vero": np.nan}]
    coppie = [("modello", "lam_casa", "lam_trasferta")]
    coppie += [(b, f"{b}_casa", f"{b}_trasferta") for b in PM.BASELINE]
    for nome, cc, ct in coppie:
        s = (d[cc] + d[ct]).to_numpy(float)
        righe.append({"candidato": nome, "media": float(s.mean()),
                      "sd": float(s.std(ddof=1)),
                      "corr con il totale vero": float(np.corrcoef(s, tot)[0, 1])})
    return pd.DataFrame(righe)


def calibrazione(pv: pd.DataFrame = None, candidato: str = "modello",
                 classe: str = "1", bins: int = 10) -> pd.DataFrame:
    """Affidabilita': la probabilita' dichiarata contro la frequenza osservata."""
    pv = previsioni() if pv is None else pv
    p = pv[f"{candidato}|p{classe}"].to_numpy()
    y = (pv["esito"] == classe).to_numpy().astype(float)
    bordi = np.linspace(0, 1, bins + 1)
    k = np.clip(np.digitize(p, bordi) - 1, 0, bins - 1)
    righe = []
    for b in range(bins):
        m = k == b
        if not m.any():
            continue
        righe.append({"fascia": f"{bordi[b]:.1f}-{bordi[b+1]:.1f}",
                      "n": int(m.sum()), "dichiarata": float(p[m].mean()),
                      "osservata": float(y[m].mean())})
    return pd.DataFrame(righe)


def pendenza_calibrazione(pv: pd.DataFrame = None, candidato: str = "modello",
                          classe: str = "1") -> dict:
    """Pendenza logistica della classe contro il proprio logit. 1.0 = calibrato.

    E' la stessa diagnostica della Fase 4, dove aveva separato il modello dai
    baseline meglio dell'accuratezza. Qui si applica a un esito categoriale una
    classe per volta, che e' il modo in cui resta interpretabile.
    """
    from .difesa import pendenza_logit

    pv = previsioni() if pv is None else pv
    p = np.clip(pv[f"{candidato}|p{classe}"].to_numpy(), 1e-9, 1 - 1e-9)
    y = (pv["esito"] == classe).to_numpy().astype(float)
    b, se = pendenza_logit(y, p)
    return {"candidato": candidato, "classe": classe, "pendenza": float(b),
            "errore standard": float(se),
            "z vs 1.0": float((b - 1.0) / se) if se and se > 0 else np.nan}


def per_segmento(pv: pd.DataFrame = None) -> pd.DataFrame:
    """RPS del modello e del baseline migliore, per meta' di stagione e squilibrio.

    La Fase 4 aveva trovato che il modello perde nel terzile alto di lambda; qui
    si guarda l'analogo, cioe' le partite squilibrate, dove `rho` costante e' anche
    l'assunzione piu' fragile (domanda aperta 3 di R1).
    """
    pv = previsioni() if pv is None else pv
    esito = pv["esito"].to_numpy()
    pm = pv[[f"modello|p{c}" for c in CLASSI]].to_numpy()
    pb = pv[[f"media squadra + campo|p{c}" for c in CLASSI]].to_numpy()
    d = pv.copy()
    d["rps_modello"] = rps(pm, esito)
    d["rps_baseline"] = rps(pb, esito)
    sq = np.abs(np.log(pv["modello|p1"] / pv["modello|p2"]))
    d["segmento"] = pd.qcut(sq, 3, labels=["equilibrate", "medie", "squilibrate"])

    righe = []
    for nome, sub in d.groupby("segmento", observed=True):
        righe.append({"segmento": str(nome), "n": len(sub),
                      "RPS modello": float(sub["rps_modello"].mean()),
                      "RPS baseline": float(sub["rps_baseline"].mean()),
                      "differenza": float((sub["rps_modello"] - sub["rps_baseline"]).mean())})
    for meta, sub in d.groupby(d["giornata"] > 19, observed=True):
        righe.append({"segmento": "2a meta'" if meta else "1a meta'", "n": len(sub),
                      "RPS modello": float(sub["rps_modello"].mean()),
                      "RPS baseline": float(sub["rps_baseline"].mean()),
                      "differenza": float((sub["rps_modello"] - sub["rps_baseline"]).mean())})
    return pd.DataFrame(righe)
