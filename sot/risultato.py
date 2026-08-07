# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R1 — dalla coppia di lambda alla distribuzione del risultato.

E3.1 consegna due **marginali**: il lambda dei gol di ciascuna squadra nella
partita. Un esito 1X2 non e' una marginale — e' una funzione della **congiunta**,
e la congiunta non e' determinata dalle marginali. Serve un'ipotesi sulla
dipendenza, e questo modulo la rende un **parametro misurabile** invece di una
scelta implicita.

**I lambda di E3.1 NON vengono ristimati.** Entrano come dati. E' una scelta e
non una comodita': E3.1 e' gia' validato per conto suo (t = 5,52 contro il
baseline migliore, PIT p = 0,773) e rifittarlo dentro un modello di congiunta
cambierebbe quella validazione senza rifarla. Qui si stima **un parametro solo**,
`rho`, a marginali fissate.

**La forma della dipendenza e' quella di Dixon-Coles**, e la ragione per cui si
tocca solo l'angolo dei punteggi bassi e' che li' sta il fenomeno noto: due
squadre sullo 0-0 all'80' non giocano come sullo 0-0 al 10'. La correzione

    P(x, y) = tau(x, y) * Poisson(x; lam_c) * Poisson(y; lam_t)

vale 1 ovunque tranne nelle quattro celle `(0,0) (0,1) (1,0) (1,1)`:

    tau(0,0) = 1 - lam_c * lam_t * rho
    tau(0,1) = 1 + lam_c * rho
    tau(1,0) = 1 + lam_t * rho
    tau(1,1) = 1 - rho

`rho = 0` **e' l'indipendenza**, ed e' il nullo di ogni test qui dentro. Non e'
il valore di comodo: e' cio' che si assume senza accorgersene quando si
moltiplicano due Poisson, e questo modulo esiste per non assumerlo.

> **Il conto NON e' fatto sulla `rho` della Fase 6C.** Quella e' lo shrinkage fra
> stagioni del livello di squadra, e non c'entra niente con questa. Nomi uguali,
> grandezze diverse: qui si chiama `rho_dc` ovunque il contesto non sia ovvio.

**La verifica falsificabile del blocco** e' `verifica_marginali()`: sommando la
congiunta per righe e per colonne devono tornare le due Poisson di partenza, e a
`rho != 0` devono tornare **lo stesso** — perche' la correzione di Dixon-Coles
sposta massa **dentro** l'angolo, non fuori. Se le marginali si muovessero, la
congiunta non sarebbe una congiunta di quei lambda e ogni numero di R2 sarebbe
costruito su un modello diverso da quello che E3 ha validato.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import config

#: Troncamento della congiunta. Serie A: il massimo osservato in cinque stagioni
#: e' 7 gol per squadra. Si va a 12 e si **misura** la massa buttata via
#: (`massa_troncata`) invece di dichiararla trascurabile.
MAX_GOL = 12

#: Il perimetro entro cui `rho` produce ancora probabilita' non negative dipende
#: dai lambda; questo e' solo il rettangolo di ricerca dell'ottimizzatore.
RHO_LIMITI = (-0.5, 0.5)

#: Le quattro celle che Dixon-Coles corregge. Stanno qui e non nel corpo perche'
#: **quali** celle si toccano e' l'ipotesi, non un dettaglio di implementazione.
CELLE_CORRETTE = ((0, 0), (0, 1), (1, 0), (1, 1))


def tau(x, y, lam_c, lam_t, rho: float):
    """Il fattore di correzione. Vale 1 fuori dalle quattro celle."""
    x = np.asarray(x)
    y = np.asarray(y)
    out = np.ones(np.broadcast(x, y, lam_c, lam_t).shape, dtype=float)
    out = np.where((x == 0) & (y == 0), 1.0 - lam_c * lam_t * rho, out)
    out = np.where((x == 0) & (y == 1), 1.0 + lam_c * rho, out)
    out = np.where((x == 1) & (y == 0), 1.0 + lam_t * rho, out)
    out = np.where((x == 1) & (y == 1), 1.0 - rho, out)
    return out


def congiunta(lam_c: float, lam_t: float, rho: float = 0.0,
              max_gol: int = MAX_GOL) -> np.ndarray:
    """La matrice `P(gol_casa = x, gol_trasferta = y)`, `(max_gol+1)` quadrata.

    **Non rinormalizza.** La massa persa dal troncamento resta persa e si legge
    con `massa_troncata()`: rinormalizzare la nasconderebbe dentro le celle
    basse, che sono proprio quelle su cui si misura `rho`.
    """
    g = np.arange(max_gol + 1)
    px = stats.poisson.pmf(g, lam_c)
    py = stats.poisson.pmf(g, lam_t)
    p = np.outer(px, py)
    x, y = np.meshgrid(g, g, indexing="ij")
    return p * tau(x, y, lam_c, lam_t, rho)


def massa_troncata(lam_c: float, lam_t: float, max_gol: int = MAX_GOL) -> float:
    """Quanta probabilita' il troncamento butta via. Si misura, non si assume."""
    return float(1.0 - congiunta(lam_c, lam_t, 0.0, max_gol).sum())


def massa_troncata_dati(d: pd.DataFrame) -> dict:
    """La massa persa dal troncamento **sui lambda veri**, non su una coppia comoda.

    Serve perche' `massa_troncata(1.6, 1.2)` sta sotto la precisione di stampa e
    farebbe sembrare il troncamento esatto: cresce ripidamente con il lambda, e i
    lambda del campione arrivano a 3,2. Il massimo e' il numero da dichiarare.
    """
    v = np.array([massa_troncata(a, b) for a, b in
                  zip(d["lam_casa"], d["lam_trasferta"])])
    return {"max": float(v.max()), "media": float(v.mean()),
            "lam_max": float(max(d["lam_casa"].max(), d["lam_trasferta"].max()))}


def verifica_marginali(lam_c: float = 1.6, lam_t: float = 1.2,
                       rho: float = 0.1) -> dict:
    """Le marginali della congiunta sono le due Poisson di partenza?

    E' la verifica falsificabile del blocco. La correzione di Dixon-Coles sposta
    massa **dentro** l'angolo dei punteggi bassi, quindi le marginali non devono
    muoversi — a `rho` qualsiasi.

    **Le marginali si conservano ESATTAMENTE, e non e' un caso numerico: e'
    algebra.** Sulla riga `x = 0` le due celle toccate sono `(0,0)` e `(0,1)`, e
    la loro variazione e'

        P(0;c)P(0;t) * (-c*t*rho)  +  P(0;c)P(1;t) * (c*rho)

    con `P(1;t) = t * P(0;t)`, cioe' `P(0;c)P(0;t)*c*rho*(-t + t) = 0`. Lo stesso
    sulle colonne. **La forma di Dixon-Coles e' costruita per questo**: sposta
    massa dentro l'angolo senza toccare i totali di riga e di colonna.

    > Questa docstring diceva il contrario — che il residuo fosse dell'ordine di
    > `rho*lam` — finche' la funzione non l'ha misurato e non ha restituito zero
    > a ogni cifra. **E' la verifica che ha corretto la prosa**, ed e' il motivo
    > per cui e' scritta come misura e non come commento.
    """
    p0 = congiunta(lam_c, lam_t, 0.0)
    p1 = congiunta(lam_c, lam_t, rho)
    return {
        "somma_rho0": float(p0.sum()),
        "somma_rho": float(p1.sum()),
        "scarto_somma": float(abs(p1.sum() - p0.sum())),
        "scarto_marg_casa": float(np.abs(p1.sum(axis=1) - p0.sum(axis=1)).max()),
        "scarto_marg_trasf": float(np.abs(p1.sum(axis=0) - p0.sum(axis=0)).max()),
        "massa_troncata": massa_troncata(lam_c, lam_t),
    }


def esiti(p: np.ndarray) -> tuple[float, float, float]:
    """Da una congiunta a `(P(1), P(X), P(2))`, rinormalizzate sulla massa viva."""
    n = p.shape[0]
    x, y = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = p.sum()
    return (float(p[x > y].sum() / tot),
            float(p[x == y].sum() / tot),
            float(p[x < y].sum() / tot))


def over(p: np.ndarray, linea: float) -> float:
    """`P(gol totali > linea)`. La linea e' mezza, quindi non c'e' il pari."""
    n = p.shape[0]
    x, y = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    return float(p[(x + y) > linea].sum() / p.sum())


# ---------------------------------------------------------------------------
# La stima di rho, a marginali FISSATE
# ---------------------------------------------------------------------------

def _loglik(rho: float, lam_c, lam_t, gc, gt) -> float:
    """Log-verosimiglianza delle sole celle corrette, a lambda fissi.

    Fuori dalle quattro celle `tau` vale 1 e il termine non dipende da `rho`:
    includerlo sommerebbe una costante identica sotto nullo e alternativa. Si
    tiene comunque tutta la verosimiglianza per leggibilita' del numero, ma la
    **differenza** fra due `rho` viene solo dall'angolo.
    """
    t = tau(gc, gt, lam_c, lam_t, rho)
    if np.any(t <= 0):
        return -np.inf
    base = (stats.poisson.logpmf(gc, lam_c) + stats.poisson.logpmf(gt, lam_t))
    return float(np.sum(base + np.log(t)))


def stima_rho(d: pd.DataFrame) -> dict:
    """MLE di `rho` sulle partite date, con i lambda di E3.1 come dati.

    Ritorna anche il test del rapporto di verosimiglianza contro `rho = 0`, che
    e' il nullo dell'indipendenza. **In campione**: e' un limite superiore di
    quanto la dipendenza possa valere, ed e' la direzione in cui va usato — un
    rifiuto qui non dimostra valore predittivo, esattamente come in 6D.
    """
    lam_c = d["lam_casa"].to_numpy()
    lam_t = d["lam_trasferta"].to_numpy()
    gc = d["gol_casa"].to_numpy()
    gt = d["gol_trasferta"].to_numpy()

    f = lambda r: -_loglik(r, lam_c, lam_t, gc, gt)  # noqa: E731
    res = optimize.minimize_scalar(f, bounds=RHO_LIMITI, method="bounded")
    rho = float(res.x)

    ll0 = _loglik(0.0, lam_c, lam_t, gc, gt)
    ll1 = _loglik(rho, lam_c, lam_t, gc, gt)
    lr = 2.0 * (ll1 - ll0)
    return {
        "n": int(len(d)),
        "rho": rho,
        "loglik_0": ll0,
        "loglik_rho": ll1,
        "lr": float(lr),
        "p_lr": float(stats.chi2.sf(lr, 1)) if lr > 0 else 1.0,
        "sul_bordo": bool(abs(rho - RHO_LIMITI[0]) < 1e-6
                          or abs(rho - RHO_LIMITI[1]) < 1e-6),
    }


def mde_rho(d: pd.DataFrame, potenza: float = 0.80, alpha: float = 0.05,
            griglia=None, repliche: int = 400, seed: int = None) -> pd.DataFrame:
    """Quale `rho` vero questo campione vedrebbe, con potenza dichiarata.

    E' la lezione della Fase 6D applicata qui: un `rho` non distinguibile da zero
    non dice che la dipendenza sia zero finche' non si sa quanto grande dovrebbe
    essere per essere vista. Si simulano risultati **dalla congiunta con `rho`
    vero** e si conta quante volte il test lo rifiuta.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    griglia = np.array([0.02, 0.05, 0.08, 0.12, 0.20]) if griglia is None else np.asarray(griglia)
    soglia = stats.chi2.isf(alpha, 1)

    lam_c = d["lam_casa"].to_numpy()
    lam_t = d["lam_trasferta"].to_numpy()
    n = len(d)
    lato = MAX_GOL + 1

    righe = []
    for rv in griglia:
        # Le `n` distribuzioni si costruiscono UNA volta per `rho`, non una per
        # replica: erano 3,9 milioni di chiamate e sono 1.638.
        P = np.empty((n, lato * lato))
        for i in range(n):
            q = np.clip(congiunta(lam_c[i], lam_t[i], rv), 0, None).ravel()
            P[i] = q / q.sum()
        cum = np.cumsum(P, axis=1)

        rifiuti = 0
        for _ in range(repliche):
            u = rng.random((n, 1))
            k = (cum < u).sum(axis=1)          # inversa della cdf, vettorizzata
            sim = pd.DataFrame({"lam_casa": lam_c, "lam_trasferta": lam_t,
                                "gol_casa": k // lato, "gol_trasferta": k % lato})
            if stima_rho(sim)["lr"] > soglia:
                rifiuti += 1
        righe.append({"rho_vero": float(rv), "potenza": rifiuti / repliche,
                      "repliche": repliche})
    return pd.DataFrame(righe)


def celle_osservate(d: pd.DataFrame) -> pd.DataFrame:
    """Frequenza osservata contro attesa nelle quattro celle, senza modelli.

    **E' la derivazione indipendente** della stessa cosa che `stima_rho` misura
    con la verosimiglianza. Se le due non concordassero, il numero da credere
    sarebbe questo: non passa da nessuna ottimizzazione.
    """
    lam_c = d["lam_casa"].to_numpy()
    lam_t = d["lam_trasferta"].to_numpy()
    gc = d["gol_casa"].to_numpy()
    gt = d["gol_trasferta"].to_numpy()

    righe = []
    for (x, y) in CELLE_CORRETTE:
        att = float(np.sum(stats.poisson.pmf(x, lam_c) * stats.poisson.pmf(y, lam_t)))
        oss = int(np.sum((gc == x) & (gt == y)))
        righe.append({"cella": f"{x}-{y}", "osservate": oss,
                      "attese_indip": att, "rapporto": oss / att if att else np.nan})
    tot_o = sum(r["osservate"] for r in righe)
    tot_a = sum(r["attese_indip"] for r in righe)
    righe.append({"cella": "**angolo**", "osservate": tot_o,
                  "attese_indip": tot_a, "rapporto": tot_o / tot_a})
    return pd.DataFrame(righe)


def correlazione_residui(d: pd.DataFrame) -> dict:
    """La correlazione fra gli scarti dai due lambda. Terza derivazione.

    Non usa Dixon-Coles e non usa la verosimiglianza: e' `corr(gc - lam_c,
    gt - lam_t)`. Sotto indipendenza condizionata ai lambda vale zero, e il segno
    e' leggibile senza sapere niente di `tau`.
    """
    rc = d["gol_casa"].to_numpy() - d["lam_casa"].to_numpy()
    rt = d["gol_trasferta"].to_numpy() - d["lam_trasferta"].to_numpy()
    r, p = stats.pearsonr(rc, rt)
    return {"n": int(len(d)), "corr": float(r), "p": float(p)}
