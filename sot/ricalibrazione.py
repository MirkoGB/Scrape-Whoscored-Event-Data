# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2-bis — la sotto-sicurezza su 1X2: da dove viene, e se si toglie.

R2 ha misurato che il modello e' **sotto-sicuro** sul 1X2 (pendenza 1,223 sulla
classe `1` e 1,324 sulla `2`, cioe' sopra 1.0) e ha lasciato la spiegazione come
domanda aperta n. 1, indicando la **compressione della ridge** della Fase 6A come
ipotesi compatibile ma non misurata. Questo blocco la misura.

**Perche' prima di R3 e non dopo.** Una probabilita' mal calibrata su una partita
sola resta un errore piccolo e locale; R3 la propaga attraverso una simulazione
di stagione, dove gli stessi errori si **sommano** su 38 turni e finiscono nella
distribuzione di scudetto e retrocessione. Se le probabilita' sono
sistematicamente troppo vicine al centro, la classifica simulata e' troppo
compressa e le code — che sono l'unica cosa che R3 pubblica — sono sbagliate nel
verso peggiore. §4 lo misura al livello di aggregazione di R3 invece di
argomentarlo.

**Due domande separate, e tenerle separate e' il contenuto del blocco.**

1. **Da dove viene** (§2). L'ipotesi della ridge dice una cosa precisa e
   falsificabile: il modello comprime il **divario** di forza fra le due squadre,
   quindi allargarlo del reciproco della compressione deve riportare la pendenza
   a 1.0. Si costruisce la de-compressione come parametro `k` e si guarda dove
   cade il `k` che calibra.
2. **Se si toglie** (§3). Una ricalibrazione walk-forward — Platt, temperatura o
   isotonica — corregge il **sintomo** qualunque sia la causa. **Che funzioni non
   e' una conferma dell'ipotesi**, ed e' l'errore di lettura che questo modulo
   esiste per rendere impossibile: le due sezioni rispondono a domande diverse e
   possono benissimo dare esiti opposti.

> **Questo blocco STIMA**, e R2 no. E' la ragione per cui e' un modulo separato e
> non tre funzioni in `sot/esiti.py`, dove un test vieta `minimize`: la
> ricalibrazione ha parametri, e parametri stimati vanno walk-forward. Qui la
> disciplina e' la stessa di sempre (vincolo 1): **il ricalibratore di una
> stagione si addestra sulle stagioni precedenti e su nient'altro.** La 2021-22
> non ha un passato e resta senza ricalibrazione, contata e non riempita.

> **Vincolo 2, e vale in particolare qui.** Se la ricalibrazione migliorasse la
> pendenza peggiorando l'RPS, adottarla sarebbe far tornare un numero. Il criterio
> di adozione e' dichiarato **prima** di guardare i risultati, in
> `CRITERIO_ADOZIONE`, e `verdetto()` lo applica meccanicamente.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import config, esiti as E, perimetro as PM, risultato as R

#: La compressione della ridge misurata dalla Fase 6A: pendenza 0,760 ± 0,018 dei
#: rating sui tassi grezzi. **E' su un altro bersaglio e su un'altra stagione** —
#: i tiri in porta del 2025-26, non i gol delle cinque stagioni — e sta qui come
#: **riferimento dichiarato**, non come misura del modello di R2. L'ipotesi che
#: si prova e' «la compressione ha quest'ordine di grandezza», non «vale 0,760».
PENDENZA_RIDGE_6A = 0.760

#: La de-compressione che l'ipotesi implica: il reciproco della compressione.
K_RIFERIMENTO = 1.0 / PENDENZA_RIDGE_6A

#: La griglia di de-compressione, **dichiarata e non ricavata dai dati**. Contiene
#: 1.0 (il modello pubblicato), il riferimento della 6A, e valori sotto 1 perche'
#: il verso non e' assunto: se il `k` che calibra stesse sotto 1 l'ipotesi sarebbe
#: rovesciata, e una griglia che non lo permette non potrebbe scoprirlo.
K_GRID = (0.70, 0.85, 1.00, 1.15, K_RIFERIMENTO, 1.45, 1.60, 1.80)

#: Minimo di partite passate per stimare il centro del divario in `modo
#: "divario_netto"`. Stessa soglia del walk-forward di E3 e del tasso base di R2:
#: sotto, la riga resta **non trasformata** e si conta, invece di ricevere un
#: centro stimato su quattro partite.
MIN_PASSATO = 30

#: Minimo di partite su cui si accetta di stimare un ricalibratore. Una stagione
#: di partite validabili ne porta circa 320: la soglia sta sotto quella, cosi' che
#: **una** stagione di passato basti, e sopra il punto in cui l'isotonica — che ha
#: piu' gradi di liberta' di tutte — inseguirebbe il rumore.
MIN_TRAINING = 250

#: I tre ricalibratori, **in ordine di semplicita' crescente**: un parametro,
#: sei, e una funzione monotona libera. L'ordine e' il criterio di parita' di
#: `CRITERIO_ADOZIONE` e non un'opinione estetica: piu' parametri stimati su un
#: passato finito, piu' varianza portata dentro la previsione.
METODI = ("temperatura", "platt", "isotonica")

#: Pavimento sulle probabilita' ricalibrate. L'isotonica puo' restituire **zero
#: esatto** su una classe, e uno zero esatto rende la log-loss infinita: e' lo
#: stesso caso di `PAVIMENTO_LAMBDA` in R2 e della frequenza storica grezza di
#: E3, e si tratta allo stesso modo — si smorza, si dichiara, si conta.
PAVIMENTO_P = 1e-4

#: **Il criterio di adozione, scritto prima di guardare i numeri.** Un
#: ricalibratore si adotta solo se soddisfa entrambe le condizioni; a parita', si
#: prende il piu' semplice secondo l'ordine di `METODI`.
CRITERIO_ADOZIONE = (
    "(a) porta |z vs 1.0| sotto 2 su TUTTE E TRE le classi; "
    "(b) non peggiora l'RPS oltre il rumore (differenza appaiata sotto il proprio "
    "MDE); a parita', il piu' semplice secondo l'ordine di METODI"
)


# ---------------------------------------------------------------------------
# §2 — la de-compressione del divario
# ---------------------------------------------------------------------------

def decomprimi(lam_c, lam_t, k: float, centro=0.0):
    """Allarga il **divario** fra i due lambda di un fattore `k`, a livello fermo.

    ```
    d  = log(lam_c) - log(lam_t)          il divario
    d' = centro + k * (d - centro)
    lam_c' = exp((log lam_c + log lam_t + d') / 2)
    lam_t' = exp((log lam_c + log lam_t - d') / 2)
    ```

    **E' la componente della de-compressione che il 1X2 vede**, e non tutta:
    l'esito di una partita dipende da chi e' piu' forte, cioe' dal divario. La
    costruzione conserva `lam_c * lam_t` a ogni cifra — la media geometrica,
    cioe' il livello della partita — e scala il divario esattamente per `k`.
    Entrambe le cose sono verificate da `verifica_decompressione()` e non
    lasciate all'intenzione.

    > **Non e' l'inverso *letterale* della ridge, e la differenza e' misurabile.**
    > La penalita' comprime `attacco` e `difesa` verso zero senza toccare `mu`,
    > quindi comprime lo scarto di **ciascun lato** dalla media, non solo la loro
    > differenza: dentro `log lam_c = mu + att_c + dif_t + gamma` l'ipotesi tocca
    > anche la **somma** dei due lati. Quello e' `modo = "pieno"`, che c'e' e si
    > riporta accanto; questo modo isola il pezzo che muove l'esito, e i due
    > danno la stessa conclusione — il che e' il motivo per cui ci sono entrambi.

    `centro = 0` scala anche il **vantaggio del campo**, che sta dentro il
    divario come termine `gamma` e non e' un effetto di squadra compresso dalla
    ridge. E' il difetto dichiarato del modo semplice, ed e' la ragione per cui
    esiste `centro_passato()`: li' il divario si allarga attorno al vantaggio del
    campo medio invece che attorno allo zero, e il campo resta dov'era.
    """
    lc = np.log(np.asarray(lam_c, dtype=float))
    lt = np.log(np.asarray(lam_t, dtype=float))
    d = lc - lt
    s = lc + lt
    d2 = np.asarray(centro, dtype=float) + k * (d - np.asarray(centro, dtype=float))
    return np.exp((s + d2) / 2.0), np.exp((s - d2) / 2.0)


def dati(d: pd.DataFrame = None) -> pd.DataFrame:
    """Le partite validabili con **i due lambda accanto**, che e' cio' che serve qui.

    R2 lavora sulle probabilita' gia' composte (`esiti.previsioni`); questo blocco
    deve tornare un passo indietro, perche' la de-compressione agisce sul lambda e
    non sulla probabilita'. La riga e' la stessa — stesso perimetro, stesse 1.638 —
    e `probabilita_decompresse(d, 1.0)` deve riprodurre le colonne `modello|p*` di
    R2 a ogni cifra: un test lo pretende.
    """
    if d is not None:
        return d
    p = PM.partite(con_baseline=True)
    return p[p["validabile"]].reset_index(drop=True)


def centro_passato(pv: pd.DataFrame) -> np.ndarray:
    """Il divario medio stimato **sul solo passato**, riga per riga (vincolo 1).

    E' in pratica il vantaggio del campo espresso in log-rapporto di lambda, e
    serve come centro attorno a cui allargare: allargare attorno allo zero
    moltiplicherebbe anche il campo, che non e' un effetto di squadra.

    Il passato e' **tutto** il passato, stagioni precedenti comprese: il vantaggio
    del campo non e' una proprieta' di una stagione, e restringerlo a quella in
    corso darebbe a settembre una stima su tre partite. Sotto `MIN_PASSATO` la
    riga riceve centro `0`, che con `k = 1` la lascia identica: si conta con
    `righe_senza_centro()` invece di riempirla con una stima che non c'e'.
    """
    d = pv.sort_values(["stagione", "matchId"])
    div = np.log(d["lam_casa"].to_numpy(float)) - np.log(d["lam_trasferta"].to_numpy(float))
    cum = np.concatenate([[0.0], np.cumsum(div)])[:-1]
    n = np.arange(len(div))
    with np.errstate(invalid="ignore", divide="ignore"):
        media = np.where(n >= MIN_PASSATO, cum / np.maximum(n, 1), 0.0)
    out = pd.Series(media, index=d.index)
    return out.reindex(pv.index).to_numpy()


def righe_senza_centro(pv: pd.DataFrame) -> int:
    """Quante righe restano senza centro stimabile. Si conta, non si assume."""
    return int(min(MIN_PASSATO, len(pv)))


def centro_livello_passato(pv: pd.DataFrame) -> np.ndarray:
    """La media di `log lam` sul solo passato, riga per riga. Serve a `modo "pieno"`.

    E' il `mu` che la ridge **non** penalizza: allargare attorno a un altro punto
    sposterebbe anche il livello del campionato, che l'ipotesi non tocca.
    """
    d = pv.sort_values(["stagione", "matchId"])
    lg = 0.5 * (np.log(d["lam_casa"].to_numpy(float))
                + np.log(d["lam_trasferta"].to_numpy(float)))
    cum = np.concatenate([[0.0], np.cumsum(lg)])[:-1]
    n = np.arange(len(lg))
    media = np.where(n >= MIN_PASSATO, cum / np.maximum(n, 1), lg)
    return pd.Series(media, index=d.index).reindex(pv.index).to_numpy()


def _lambda_decompressi(pv: pd.DataFrame, k: float, modo: str = "divario"):
    """I due lambda de-compressi, in uno dei tre modi dichiarati.

    - `"divario"`: si allarga il divario attorno a zero. Il livello della partita
      non si muove, il vantaggio del campo si' — e' il difetto dichiarato.
    - `"divario_netto"`: come sopra ma attorno al divario medio del **passato**,
      cioe' al vantaggio del campo, che resta dov'era.
    - `"pieno"`: l'inverso **letterale** della ridge, `log lam' = m + k(log lam - m)`
      con `m` stimato sul solo passato. Allarga anche la somma dei due lati, che
      e' cio' che la penalita' comprime e che il divario da solo non contiene.
    """
    if modo == "pieno":
        m = centro_livello_passato(pv)
        lc = np.log(pv["lam_casa"].to_numpy(float))
        lt = np.log(pv["lam_trasferta"].to_numpy(float))
        return np.exp(m + k * (lc - m)), np.exp(m + k * (lt - m))
    centro = 0.0 if modo == "divario" else centro_passato(pv)
    return decomprimi(pv["lam_casa"].to_numpy(float),
                      pv["lam_trasferta"].to_numpy(float), k, centro)


def probabilita_decompresse(pv: pd.DataFrame, k: float,
                            modo: str = "divario") -> np.ndarray:
    """La matrice `(n, 3)` di probabilita' 1X2 dopo la de-compressione.

    Passa per la **stessa** `risultato.congiunta` di R2, con lo stesso `rho = 0`:
    cambia il lambda e nient'altro, altrimenti si misurerebbe la composizione.
    """
    lc, lt = _lambda_decompressi(pv, k, modo)
    return np.array([R.esiti(R.congiunta(a, b, 0.0)) for a, b in zip(lc, lt)])


def _pendenza(p: np.ndarray, esito: np.ndarray, classe: str) -> tuple[float, float]:
    from .difesa import pendenza_logit

    j = E.CLASSI.index(classe)
    y = (np.asarray(esito) == classe).astype(float)
    return pendenza_logit(y, np.clip(p[:, j], 1e-9, 1 - 1e-9))


def pendenza_marginale_gol(pv: pd.DataFrame, k: float = 1.0,
                           modo: str = "divario") -> dict:
    """La pendenza di calibrazione **sui gol**, non sull'esito. Poisson, Fase 4.

    E' il controllo che decide la sezione, e costa niente perche' il numero
    esiste gia': se il modello comprimesse davvero il divario, i suoi lambda
    sarebbero **troppo vicini fra loro** e questa pendenza starebbe **sopra**
    1.0. E3 l'ha pubblicata a 0,898 ± 0,052, cioe' sotto — e sotto 1.0 significa
    previsioni troppo **estreme**, che e' il verso opposto.

    Qui si ricalcola sulle sole partite del perimetro di R2 (le stesse 1.638),
    cosi' che il confronto con la pendenza 1X2 sia sulle stesse righe e non su
    due campioni che differiscono di due partite.
    """
    from . import validate as V

    lc, lt = _lambda_decompressi(pv, k, modo)
    lam = np.concatenate([lc, lt])
    y = np.concatenate([pv["gol_casa"].to_numpy(float),
                        pv["gol_trasferta"].to_numpy(float)])
    b, se = V.calibration_slope(y, lam)
    return {"k": k, "righe": int(len(y)), "pendenza": float(b),
            "errore standard": float(se),
            "z vs 1.0": float((b - 1.0) / se) if se and se > 0 else np.nan}


def controllo_ipotesi_sui_gol(pv: pd.DataFrame = None) -> pd.DataFrame:
    """L'ipotesi della ridge contro il numero che la misurerebbe direttamente.

    **Con la potenza dichiarata**, che e' cio' che rende leggibile un negativo
    (lezione della 6D). Se i lambda fossero compressi di un fattore `c`, la
    pendenza di calibrazione **sui gol** varrebbe `1/c`: e' la stessa relazione
    che rende la pendenza una diagnostica di compressione. L'ipotesi della 6A
    (`c = 0,760`) prevede quindi una pendenza di 1,316, e la domanda non e' solo
    «e' sopra 1?» ma «quanto e' lontana da 1,316?».

    La riga della compressione minima visibile risponde alla domanda che un
    negativo lascia sempre aperta: **una compressione piccola sarebbe passata
    inosservata?**
    """
    from . import validate as V

    pv = dati(pv)
    lam = np.concatenate([pv["lam_casa"].to_numpy(float),
                          pv["lam_trasferta"].to_numpy(float)])
    y = np.concatenate([pv["gol_casa"].to_numpy(float),
                        pv["gol_trasferta"].to_numpy(float)])
    b, se = V.calibration_slope(y, lam)
    prevista = 1.0 / PENDENZA_RIDGE_6A
    # compressione minima rilevabile a potenza 80%, due code, sulla pendenza
    mde_pend = (stats.norm.isf(0.025) + stats.norm.isf(0.20)) * se
    return pd.DataFrame([
        {"voce": "pendenza sui gol, osservata", "valore": float(b),
         "errore standard": float(se), "z": float((b - 1.0) / se)},
        {"voce": "pendenza che l'ipotesi 6A prevede (1 / 0,760)",
         "valore": float(prevista), "errore standard": np.nan,
         "z": float((b - prevista) / se)},
        {"voce": "compressione minima visibile a potenza 80%",
         "valore": float(1.0 / (1.0 + mde_pend)), "errore standard": np.nan,
         "z": np.nan},
    ])


def griglia_decompressione(pv: pd.DataFrame = None, k_grid=K_GRID,
                           modo: str = "divario") -> pd.DataFrame:
    """Pendenza 1X2, pendenza sui gol e RPS al variare della de-compressione.

    Le tre colonne vanno lette **insieme**: l'ipotesi della ridge non e' «esiste
    un `k` che calibra il 1X2» — quello esiste quasi sempre, perche' allargare le
    probabilita' e' una manopola continua — ma «**lo stesso** `k` che calibra il
    1X2 e' quello che l'ipotesi prevede, e non rompe il resto».
    """
    pv = dati(pv)
    esito = pv["esito"].to_numpy()
    y_over = (pv["gol_totali"] > 2.5).to_numpy()

    righe = []
    for k in k_grid:
        p = probabilita_decompresse(pv, k, modo)
        riga = {"k": float(k)}
        for cl in E.CLASSI:
            b, se = _pendenza(p, esito, cl)
            riga[f"pendenza {cl}"] = b
            riga[f"z {cl}"] = (b - 1.0) / se if se and se > 0 else np.nan
        # La media di `P(X)` accanto alle pendenze: senza, si legge la sezione
        # come se allargare il divario costasse solo un po' di RPS. Costa
        # **pareggi**, ed e' la voce che gia' manca.
        riga["P(X) media"] = float(p[:, 1].mean())
        riga["RPS"] = float(E.rps(p, esito).mean())
        riga["log-loss"] = float(E.logloss(p, esito).mean())
        lc, lt = _lambda_decompressi(pv, k, modo)
        po = np.array([R.over(R.congiunta(a, b_, 0.0), 2.5) for a, b_ in zip(lc, lt)])
        riga["Brier O2.5"] = float(E.brier(po, y_over).mean())
        g = pendenza_marginale_gol(pv, k, modo)
        riga["pendenza gol"] = g["pendenza"]
        riga["z gol"] = g["z vs 1.0"]
        righe.append(riga)
    return pd.DataFrame(righe)


def k_calibrante(pv: pd.DataFrame = None, classe: str = "1",
                 modo: str = "divario", limiti=(0.8, 2.0)) -> dict:
    """Il `k` che porta la pendenza di una classe esattamente a 1.0.

    Si cerca la radice invece di leggere il minimo di una griglia: un `argmin` su
    una griglia dichiarata restituirebbe un punto della griglia e farebbe
    sembrare una coincidenza cio' che e' solo la spaziatura scelta.

    I limiti sono `(0.8, 2.0)` e non un intervallo largo a piacere: sopra 2 le
    probabilita' della classe estrema si avvicinano tanto a 0 e 1 che
    `pendenza_logit` smette di convergere e ritorna `nan` — che e' il suo
    comportamento giusto, ma un `nan` a un estremo impedisce a `brentq` di
    partire. La griglia mostra che le radici cadono ben dentro.
    """
    pv = dati(pv)
    esito = pv["esito"].to_numpy()

    def f(k: float) -> float:
        b, _ = _pendenza(probabilita_decompresse(pv, k, modo), esito, classe)
        return b - 1.0

    a, b_ = limiti
    fa, fb = f(a), f(b_)
    if np.isnan(fa) or np.isnan(fb) or fa * fb > 0:
        return {"classe": classe, "k": np.nan, "estremi": (fa, fb),
                "nota": "nessun cambio di segno dentro i limiti"}
    k = float(optimize.brentq(f, a, b_, xtol=1e-4))
    return {"classe": classe, "k": k, "estremi": (float(fa), float(fb)), "nota": ""}


def deficit_pareggi(pv: pd.DataFrame = None, k: float = 1.0,
                    modo: str = "divario") -> pd.DataFrame:
    """Quanti pareggi il modello dichiara, e quanti ce ne sono. Per stagione.

    E' la voce che la de-compressione peggiora, ed e' anche il ponte con R1: due
    Poisson indipendenti producono **meno pareggi** di quanti se ne osservino, e
    la correzione di Dixon-Coles esiste in letteratura proprio per quello. R1 ha
    misurato che qui `rho = 0` e che lo scostamento presente — meno `0-0` e piu'
    `1-1` — **non ha la forma che un `rho` puo' produrre**. Il deficit resta, e
    non e' una compressione del divario: e' la composizione.

    L'errore standard e' quello binomiale sulla frequenza osservata: serve a dire
    se il deficit e' una differenza o rumore, non a fare un test formale.
    """
    pv = dati(pv)
    p = probabilita_decompresse(pv, k, modo)
    d = pv[["stagione", "esito"]].copy()
    d["pX"] = p[:, 1]

    righe = []
    for st, sub in d.groupby("stagione"):
        oss = float((sub["esito"] == "X").mean())
        att = float(sub["pX"].mean())
        n = len(sub)
        righe.append({"stagione": st, "n": n, "P(X) dichiarata": att,
                      "X osservati": oss, "deficit": oss - att,
                      "se binomiale": float(np.sqrt(oss * (1 - oss) / n)),
                      "pareggi mancanti": (oss - att) * n})
    tot = {"stagione": "**tutte**", "n": len(d),
           "P(X) dichiarata": float(d["pX"].mean()),
           "X osservati": float((d["esito"] == "X").mean())}
    tot["deficit"] = tot["X osservati"] - tot["P(X) dichiarata"]
    tot["se binomiale"] = float(np.sqrt(tot["X osservati"] *
                                        (1 - tot["X osservati"]) / len(d)))
    tot["pareggi mancanti"] = tot["deficit"] * len(d)
    return pd.DataFrame([*righe, tot])


def verifica_decompressione(k: float = 1.4) -> dict:
    """Le due identita' su cui poggia §2. Falsificabili, e non passano da modelli.

    `k = 1` deve essere l'identita'; il divario deve risultare scalato **per
    `k` esatto**; il prodotto `lam_c * lam_t` deve restare invariato. Se una
    delle tre cadesse, «de-compressione» starebbe descrivendo un'altra
    trasformazione e ogni numero della sezione misurerebbe un'altra cosa.
    """
    rng = np.random.default_rng(config.SEED)
    lc = rng.uniform(0.4, 3.2, 500)
    lt = rng.uniform(0.4, 3.2, 500)

    id_c, id_t = decomprimi(lc, lt, 1.0)
    nc, nt = decomprimi(lc, lt, k)
    d0 = np.log(lc) - np.log(lt)
    d1 = np.log(nc) - np.log(nt)
    return {
        "k=1 e' l'identita'": bool(np.allclose(id_c, lc) and np.allclose(id_t, lt)),
        "divario scalato per k": bool(np.allclose(d1, k * d0)),
        "prodotto invariato": bool(np.allclose(nc * nt, lc * lt)),
        "max scarto sul prodotto": float(np.max(np.abs(nc * nt - lc * lt))),
    }


# ---------------------------------------------------------------------------
# §3 — la ricalibrazione, walk-forward
# ---------------------------------------------------------------------------

def _normalizza(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), PAVIMENTO_P, None)
    return p / p.sum(axis=1, keepdims=True)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def applica_temperatura(p: np.ndarray, T: float) -> np.ndarray:
    """`p' ∝ p^(1/T)`. `T < 1` **affila**, `T > 1` appiattisce.

    E' la forma piu' povera possibile di ricalibrazione multiclasse — un
    parametro — e ha una proprieta' che le altre due non hanno: **resta sul
    simplesso per costruzione**, senza rinormalizzazioni che possono rompere
    l'ordine fra le classi. Sulla diagnosi di R2 ("le probabilita' sono troppo
    vicine al centro") e' anche la manopola che corrisponde letteralmente al
    difetto dichiarato.
    """
    return _normalizza(np.power(np.clip(np.asarray(p, float), 1e-12, None), 1.0 / T))


def _fit_temperatura(p: np.ndarray, esito: np.ndarray) -> float:
    """`T` per massima verosimiglianza sul training.

    **Si stima sulla log-loss e si valuta sull'RPS**, ed e' una scelta dichiarata:
    la log-loss e' la verosimiglianza del modello multinomiale, quindi e' cio' che
    una stima di massima verosimiglianza minimizza; l'RPS e' la metrica del
    blocco. Che le due possano non concordare non e' un difetto da nascondere —
    e' la ragione per cui il criterio di adozione guarda l'RPS e non la log-loss.
    """
    def obiettivo(logT: float) -> float:
        return float(E.logloss(applica_temperatura(p, float(np.exp(logT))), esito).mean())

    r = optimize.minimize_scalar(obiettivo, bounds=(np.log(0.2), np.log(5.0)),
                                 method="bounded")
    return float(np.exp(r.x))


def _fit_platt(p: np.ndarray, esito: np.ndarray) -> list[tuple[float, float]]:
    """Platt per classe: `logit(p'_k) = a_k + b_k * logit(p_k)`, poi si rinormalizza.

    Sei parametri. La rinormalizzazione e' il prezzo di trattare tre classi come
    tre problemi binari: le tre mappe non sanno l'una dell'altra e la loro somma
    non fa 1. E' dichiarato, non aggirato — e' anche il motivo per cui la
    temperatura sta prima nell'ordine di semplicita'.
    """
    from sklearn.linear_model import LogisticRegression

    coef = []
    for j, cl in enumerate(E.CLASSI):
        y = (np.asarray(esito) == cl).astype(int)
        x = _logit(p[:, j]).reshape(-1, 1)
        # C grande = penalita' trascurabile: qui la regolarizzazione non c'entra,
        # servono i due coefficienti di massima verosimiglianza.
        m = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000).fit(x, y)
        coef.append((float(m.intercept_[0]), float(m.coef_[0][0])))
    return coef


def applica_platt(p: np.ndarray, coef) -> np.ndarray:
    out = np.empty_like(np.asarray(p, dtype=float))
    for j, (a, b) in enumerate(coef):
        z = a + b * _logit(np.asarray(p)[:, j])
        out[:, j] = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
    return _normalizza(out)


def _fit_isotonica(p: np.ndarray, esito: np.ndarray):
    from sklearn.isotonic import IsotonicRegression

    mods = []
    for j, cl in enumerate(E.CLASSI):
        y = (np.asarray(esito) == cl).astype(float)
        m = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        mods.append(m.fit(p[:, j], y))
    return mods


def applica_isotonica(p: np.ndarray, mods) -> np.ndarray:
    out = np.column_stack([m.predict(np.asarray(p)[:, j])
                           for j, m in enumerate(mods)])
    return _normalizza(out)


_FIT = {"temperatura": _fit_temperatura, "platt": _fit_platt,
        "isotonica": _fit_isotonica}
_APPLICA = {"temperatura": applica_temperatura, "platt": applica_platt,
            "isotonica": applica_isotonica}


def walkforward_ricalibrazione(pv: pd.DataFrame = None, metodo: str = "temperatura"):
    """Ricalibra ogni stagione con un mappatore stimato sulle **stagioni precedenti**.

    **La granularita' e' la stagione**, ed e' una scelta dichiarata: un
    ricalibratore rifittato a ogni giornata userebbe piu' dati ma cambierebbe
    dentro la stagione, e sarebbe un secondo modello che si muove sopra al primo.
    Una stagione e' anche il momento in cui la domanda si pone davvero: all'inizio
    di un campionato si ha tutto il passato e nient'altro.

    La **prima stagione non ha un passato** e resta non ricalibrata. Non si
    riempie con il ricalibratore di un'altra stagione e non si toglie dal
    campione: si marca, e ogni confronto gira sulle righe marcate.

    Ritorna `(P, applicata, parametri)` — la matrice ricalibrata, la maschera
    booleana delle righe su cui il mappatore e' stato davvero applicato, e i
    parametri stimati per stagione.
    """
    pv = dati(pv)
    p0 = probabilita_decompresse(pv, 1.0)
    esito = pv["esito"].to_numpy()

    P = p0.copy()
    applicata = np.zeros(len(pv), dtype=bool)
    parametri = []

    stagioni = sorted(pv["stagione"].unique())
    for st in stagioni:
        m_train = pv["stagione"].to_numpy() < st
        m_test = (pv["stagione"] == st).to_numpy()
        n_train = int(m_train.sum())
        if n_train < MIN_TRAINING:
            parametri.append({"stagione": st, "n_training": n_train,
                              "parametro": "— (senza passato sufficiente)"})
            continue
        mod = _FIT[metodo](p0[m_train], esito[m_train])
        P[m_test] = _APPLICA[metodo](p0[m_test], mod)
        applicata[m_test] = True
        parametri.append({"stagione": st, "n_training": n_train,
                          "parametro": _descrivi(metodo, mod)})
    return P, applicata, pd.DataFrame(parametri)


def _descrivi(metodo: str, mod) -> str:
    if metodo == "temperatura":
        return f"T = {mod:.4f}"
    if metodo == "platt":
        return " · ".join(f"{cl}: a={a:+.3f} b={b:.3f}"
                          for cl, (a, b) in zip(E.CLASSI, mod))
    return "funzione monotona per classe"


def confronto_ricalibrazione(pv: pd.DataFrame = None) -> pd.DataFrame:
    """I tre ricalibratori contro il modello grezzo, sulle **stesse righe**.

    Il confronto gira solo dove il mappatore e' stato davvero applicato: mettere
    dentro la prima stagione, dove i due candidati coincidono per costruzione,
    diluirebbe la differenza verso zero e farebbe sembrare piccolo un effetto solo
    perche' meta' del campione non lo ha ricevuto.
    """
    pv = dati(pv)
    p0 = probabilita_decompresse(pv, 1.0)
    esito = pv["esito"].to_numpy()

    righe = []
    _, app0, _ = walkforward_ricalibrazione(pv, "temperatura")
    base = {"metodo": "modello (R2, non ricalibrato)", "n": int(app0.sum())}
    for cl in E.CLASSI:
        b, se = _pendenza(p0[app0], esito[app0], cl)
        base[f"pendenza {cl}"] = b
        base[f"z {cl}"] = (b - 1.0) / se if se and se > 0 else np.nan
    base["RPS"] = float(E.rps(p0[app0], esito[app0]).mean())
    base["log-loss"] = float(E.logloss(p0[app0], esito[app0]).mean())
    base["delta RPS"] = 0.0
    base["t"] = np.nan
    base["MDE (80%)"] = np.nan
    righe.append(base)

    for metodo in METODI:
        P, app, _ = walkforward_ricalibrazione(pv, metodo)
        riga = {"metodo": metodo, "n": int(app.sum())}
        for cl in E.CLASSI:
            b, se = _pendenza(P[app], esito[app], cl)
            riga[f"pendenza {cl}"] = b
            riga[f"z {cl}"] = (b - 1.0) / se if se and se > 0 else np.nan
        r_dopo = E.rps(P[app], esito[app])
        r_prima = E.rps(p0[app], esito[app])
        diff = r_dopo - r_prima
        se_d = diff.std(ddof=1) / np.sqrt(len(diff))
        riga["RPS"] = float(r_dopo.mean())
        riga["log-loss"] = float(E.logloss(P[app], esito[app]).mean())
        riga["delta RPS"] = float(diff.mean())
        riga["t"] = float(diff.mean() / se_d) if se_d > 0 else np.nan
        riga["MDE (80%)"] = float(
            (stats.norm.isf(0.025) + stats.norm.isf(0.20)) * se_d)
        righe.append(riga)
    return pd.DataFrame(righe)


def verdetto(tab: pd.DataFrame = None) -> dict:
    """Applica `CRITERIO_ADOZIONE` meccanicamente. Nessun giudizio a mano.

    Il criterio e' scritto prima di guardare i numeri, e questa funzione esiste
    perche' un criterio dichiarato che poi viene applicato a occhio non e' un
    criterio dichiarato.
    """
    tab = confronto_ricalibrazione() if tab is None else tab
    # **Accesso per nome di colonna, non per attributo di namedtuple.** Le colonne
    # hanno spazi nel nome (`z 1`, `delta RPS`) e `itertuples` li rinomina in
    # posizionali `_3`, `_7`…: leggerle per attributo darebbe `AttributeError` o,
    # peggio, la colonna sbagliata. Trappola incontrata scrivendo questo modulo.
    esiti_m = []
    for _i, r in tab.iterrows():
        if str(r["metodo"]).startswith("modello"):
            continue
        z = [r[f"z {cl}"] for cl in E.CLASSI]
        z_ok = all((not np.isnan(v)) and abs(v) < 2.0 for v in z)
        rps_ok = bool(r["delta RPS"] <= r["MDE (80%)"])
        esiti_m.append({"metodo": r["metodo"], "pendenza ok": bool(z_ok),
                        "RPS non peggiorato": rps_ok,
                        "adottabile": bool(z_ok and rps_ok)})
    e = pd.DataFrame(esiti_m)
    amm = [m for m in METODI if bool(e.set_index("metodo").loc[m, "adottabile"])]
    return {"criterio": CRITERIO_ADOZIONE, "tabella": e,
            "adottabili": amm, "scelto": amm[0] if amm else None}


# ---------------------------------------------------------------------------
# §4 — che cosa succede quando si aggrega a stagione (il motivo di R3)
# ---------------------------------------------------------------------------

def _punti_attesi(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Punti attesi e loro varianza per riga, per il lato di casa e di trasferta."""
    p1, px, p2 = p[:, 0], p[:, 1], p[:, 2]
    e_casa = 3 * p1 + 1 * px
    e_tras = 3 * p2 + 1 * px
    v_casa = 9 * p1 + 1 * px - e_casa ** 2
    v_tras = 9 * p2 + 1 * px - e_tras ** 2
    return np.column_stack([e_casa, e_tras]), np.column_stack([v_casa, v_tras])


def identita_punti(pv: pd.DataFrame = None, P: np.ndarray = None) -> pd.DataFrame:
    """La verifica al livello di aggregazione di R3: **la classifica si disperde
    quanto il modello dice?**

    Una probabilita' sotto-sicura non fa danno visibile su una partita; su una
    stagione intera si somma, e la classifica simulata esce **troppo corta**. La
    forma falsificabile e' un'identita' di varianza:

        var(punti osservati fra le squadre) = var(punti ATTESI) + media(varianza
                                              di campionamento)

    Il primo termine e' quanto il modello crede che le squadre differiscano, il
    secondo e' quanta fortuna il modello stesso ammette. Se la somma sta sotto
    l'osservato, il modello **sotto-dichiara la separazione**, ed e' esattamente
    cio' che una probabilita' troppo vicina al centro produce.

    **Non e' un test con una potenza**: le realizzazioni sono cinque stagioni
    (R0), e questa e' una descrizione al livello giusto, non una validazione. Il
    suo uso e' il **confronto fra varianti**, che gira sulle stesse righe.
    """
    pv = dati(pv)
    if P is None:
        P = probabilita_decompresse(pv, 1.0)
    ep, vp = _punti_attesi(P)

    d = pv[["stagione", "casa", "trasferta", "esito"]].copy()
    d["ep_casa"], d["ep_tras"] = ep[:, 0], ep[:, 1]
    d["vp_casa"], d["vp_tras"] = vp[:, 0], vp[:, 1]
    d["oss_casa"] = np.select([d["esito"] == "1", d["esito"] == "X"], [3, 1], 0)
    d["oss_tras"] = np.select([d["esito"] == "2", d["esito"] == "X"], [3, 1], 0)

    lungo = pd.concat([
        d.rename(columns={"casa": "team", "ep_casa": "ep", "vp_casa": "vp",
                          "oss_casa": "oss"})[["stagione", "team", "ep", "vp", "oss"]],
        d.rename(columns={"trasferta": "team", "ep_tras": "ep", "vp_tras": "vp",
                          "oss_tras": "oss"})[["stagione", "team", "ep", "vp", "oss"]],
    ])

    righe = []
    for st, sub in lungo.groupby("stagione"):
        g = sub.groupby("team").agg(ep=("ep", "mean"), vp=("vp", "mean"),
                                    oss=("oss", "mean"), n=("oss", "size"))
        # varianza di campionamento della MEDIA per partita di ogni squadra
        camp = float((g["vp"] / g["n"]).mean())
        righe.append({
            "stagione": st, "squadre": len(g),
            "var osservata": float(g["oss"].var(ddof=1)),
            "var attesa": float(g["ep"].var(ddof=1)),
            "var campionamento": camp,
            "attesa + campionamento": float(g["ep"].var(ddof=1)) + camp,
        })
    out = pd.DataFrame(righe)
    out["rapporto"] = out["var osservata"] / out["attesa + campionamento"]
    return out


def identita_punti_per_meta(pv: pd.DataFrame = None) -> pd.DataFrame:
    """L'identita' di §4 separata fra prima e seconda meta' di stagione.

    **E' il controllo che impedisce di attribuire alla calibrazione cio' che e'
    solo il burn-in.** I lambda sono walk-forward: alla settima giornata il
    modello sa poco, e una previsione onestamente incerta abbassa la dispersione
    dei punti attesi senza che nulla sia mal calibrato. Se il rapporto scendesse
    verso 1 nella seconda meta', la sotto-dispersione sarebbe soprattutto
    apprendimento mancante e R3 — che simula **il resto** di una stagione da una
    giornata avanzata — ne subirebbe molto meno.

    Se invece resta, e' una proprieta' del modello e R3 la eredita per intero.
    """
    pv = dati(pv)
    P = probabilita_decompresse(pv, 1.0)
    righe = []
    for nome, m in (("1a meta' (giornata <= 19)", pv["giornata"] <= 19),
                    ("2a meta' (giornata > 19)", pv["giornata"] > 19)):
        m = m.to_numpy()
        t = identita_punti(pv[m].reset_index(drop=True), P[m])
        righe.append({"perimetro": nome, "partite": int(m.sum()),
                      **_riassunto_identita(t)})
    return pd.DataFrame(righe)


def identita_punti_confronto(pv: pd.DataFrame = None) -> pd.DataFrame:
    """L'identita' di §4 prima e dopo ogni ricalibrazione, sulle stesse righe.

    E' il numero che risponde alla domanda per cui il blocco esiste: la
    sotto-sicurezza, propagata a stagione, quanto costa — e la ricalibrazione la
    ripaga?
    """
    pv = dati(pv)
    p0 = probabilita_decompresse(pv, 1.0)
    _, app, _ = walkforward_ricalibrazione(pv, "temperatura")
    sub = pv[app].copy()

    righe = []
    base = identita_punti(sub, p0[app])
    righe.append({"variante": "modello (R2)",
                  **_riassunto_identita(base)})
    for metodo in METODI:
        P, _a, _p = walkforward_ricalibrazione(pv, metodo)
        t = identita_punti(sub, P[app])
        righe.append({"variante": metodo, **_riassunto_identita(t)})
    return pd.DataFrame(righe)


def _riassunto_identita(t: pd.DataFrame) -> dict:
    return {"stagioni": len(t),
            "var osservata": float(t["var osservata"].mean()),
            "var attesa + camp.": float(t["attesa + campionamento"].mean()),
            "rapporto medio": float(t["rapporto"].mean()),
            "stagioni con rapporto > 1": int((t["rapporto"] > 1).sum())}
