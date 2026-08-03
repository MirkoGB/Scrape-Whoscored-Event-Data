# -*- coding: utf-8 -*-
"""Il modificatore di difesa: simulato per giornata, mai applicato alle medie.

`docs/regole_fantacalcio.md` §2.2 e' esplicito su due punti che decidono la
forma di questo modulo, e nessuno dei due e' negoziabile:

1. **la media di stagione e' sbagliata.** Le fasce sono una funzione a scalini
   della media difensiva, quindi applicarle alla media stagionale non da' lo
   stesso risultato che mediare i bonus ottenuti giornata per giornata. E' lo
   stesso fenomeno di convessita' gia' misurato in Fase 6A, dove il Monte Carlo
   alzava il centro dell'1,55%; **qui il segno puo' andare in entrambe le
   direzioni e va misurato**, ed e' quello che `costo_della_media` fa;
2. **il modificatore non e' una proprieta' del giocatore.** Dipende dalla media
   della linea schierata, quindi lo stesso difensore vale molto se completa una
   linea che senza di lui starebbe appena sotto una soglia, e quasi nulla se la
   linea e' gia' ben dentro una fascia o e' irrecuperabile. Un numero
   "contributo al modificatore" calcolato in isolamento non significa niente.

Ne segue che ogni numero prodotto qui porta con se' **due etichette**: la linea
di riferimento e il modulo. Un contributo marginale senza entrambe e' incompleto,
e le funzioni restituiscono sempre le due colonne.

## `escludi`, e cosa comporta

`[DECISO 0.3 — 2026-08-03]` un difensore senza voto **esce dalla media** e la
linea si accorcia. Non e' una scelta neutra: la media su meno elementi e' piu'
variabile, e con fasce a scalini piu' variabile non vuol dire ne' meglio ne'
peggio a priori — dipende da dove la linea sta rispetto alle soglie. E' un altro
motivo per simulare invece di ragionare a media.

**Il caso limite dichiarato**: se nessuno della linea prende voto, non c'e'
nessuna media da calcolare e il modificatore vale **0**, non il malus. Non e'
"media sotto 6,00": e' assenza di media. Con portiere piu' tre-cinque difensori
la probabilita' e' minuscola, ma il caso esiste e va deciso invece di scoprirlo
come `nan`.

## Cosa questo modulo NON sa

**Non sa chi giochera'.** Simula la linea che gli si dichiara, non la formazione
vera. Per l'asta e' il taglio giusto — si compra una rosa, non una formazione —
ma significa che il contributo marginale e' *condizionato allo schieramento*, e
un difensore che non gioca non prende modificatore ne' contributo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sot import config, lega as L

# Il voto della fonte sta su una griglia di mezzi punti. Simulare su un continuo
# darebbe medie leggermente diverse **proprio vicino alle soglie**, che e' dove
# le fasce decidono: la griglia si rispetta.
PASSO_VOTO = 0.5
VOTO_MIN, VOTO_MAX = 1.0, 10.0

REPLICHE = 2000
GIORNATE = 38


def _arrotonda(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x / PASSO_VOTO) * PASSO_VOTO, VOTO_MIN, VOTO_MAX)


def simula_linea(mu: np.ndarray, sd: np.ndarray, p_voto: np.ndarray,
                 giornate: int = GIORNATE, repliche: int = REPLICHE,
                 seed: int = None) -> np.ndarray:
    """Bonus di modificatore per ogni replica di stagione.

    `mu`, `sd`, `p_voto` sono vettori lunghi quanto la linea: il primo elemento
    e' il portiere, gli altri i difensori. Restituisce un vettore di lunghezza
    `repliche` con il **bonus medio per giornata** di ogni stagione simulata.

    Le tre grandezze sono indipendenti fra i membri della linea, ed e' una
    semplificazione dichiarata: in realta' una difesa che prende tre gol prende
    voti bassi *insieme*, quindi la correlazione vera e' positiva e questa
    simulazione **sottostima la variabilita' della media di linea**. Con fasce a
    scalini la sottostima non ha segno ovvio sul bonus atteso — dipende da dove
    cade la linea — e va detta invece di essere corretta a occhio.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    n = len(mu)
    forma = (repliche, giornate, n)
    prende = rng.random(forma) < p_voto[None, None, :]
    voti = _arrotonda(rng.normal(mu[None, None, :], sd[None, None, :], forma))

    if L.gestione_sv() != "escludi":                      # pragma: no cover
        raise NotImplementedError(
            f"gestione_sv={L.gestione_sv()!r}: implementata solo 'escludi', "
            "che e' la decisione 0.3. Le altre due letture cambiano la media e "
            "vanno scritte, non approssimate")

    quanti = prende.sum(axis=2)
    somma = np.where(prende, voti, 0.0).sum(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        media = np.where(quanti > 0, somma / np.maximum(quanti, 1), np.nan)

    soglie = np.array([f.minimo if f.minimo is not None else -np.inf for f in L.FASCE])
    valori = np.array([f.bonus for f in L.FASCE])
    indice = np.searchsorted(soglie[1:], media, side="right")
    bonus = valori[indice]
    # Nessuno a voto: non c'e' media, quindi non c'e' fascia. Zero, non malus.
    bonus = np.where(np.isnan(media), 0.0, bonus)
    return bonus.mean(axis=1)


def profilo(giocatori: pd.DataFrame, ruolo: str) -> pd.DataFrame:
    """Estrae `mu`, `sd`, `p_voto` per i giocatori di un ruolo.

    `mu` e' il voto base atteso e `p_voto` la probabilita' di prendere voto in
    una giornata, cioe' `presenze_attese / 38`: sono gli **stessi due fattori**
    che il modello per l'asta stima, non una seconda stima parallela. Se
    divergessero, il contributo al modificatore e i punti direbbero cose
    incoerenti sullo stesso giocatore.
    """
    d = giocatori[giocatori["ruolo"] == ruolo].copy()
    d["p_voto"] = np.clip(d["presenze_attese"] / GIORNATE, 0.0, 1.0)
    d["mu"] = d["voto_atteso"]
    d["sd"] = d["sd_voto"]
    return d


UNIVERSI = ("schierabili", "tutti i quotati")


def _mediano(d: pd.DataFrame, quanti: int | None) -> tuple[float, float, float]:
    if quanti is not None and len(d) > quanti:
        d = d.nlargest(quanti, "punti_previsti")
    return float(d["mu"].median()), float(d["sd"].median()), float(d["p_voto"].median())


def linea_riferimento(giocatori: pd.DataFrame, n_difensori: int,
                      universo: str = "schierabili") -> dict:
    """La linea dichiarata rispetto a cui ogni contributo e' marginale.

    **Va dichiarata, non scelta implicitamente** (§2.2): lo stesso giocatore ha
    contributi diversi rispetto a linee diverse, e un numero senza la sua linea
    e' incompleto. Per questo l'universo e' un parametro con due valori, e
    entrambi finiscono nel report.

    | universo | chi entra nel mediano | cosa descrive |
    | --- | --- | --- |
    | `schierabili` (default) | i migliori `n_squadre x n_difensori` per punti attesi | la linea che una lega di 8 squadre schiera davvero |
    | `tutti i quotati` | tutti i difensori del listone | il mediano del listone |

    **Il default non e' `tutti i quotati`, ed e' una correzione a una prima
    versione che lo era.** Il mediano di tutti i quotati e' un panchinaro: meta'
    del listone gioca pochissimo, quindi quella linea ha una media difensiva
    attesa di 5,93 — cioe' sotto la soglia minima — e ogni contributo marginale
    misurato contro di lei risultava gonfiato. Una linea di riferimento deve
    essere una linea che qualcuno schiera.
    """
    if universo not in UNIVERSI:
        raise ValueError(f"universo {universo!r} fuori da {UNIVERSI}")
    quanti_d = (L.LEGA.n_squadre * n_difensori if universo == "schierabili" else None)
    quanti_p = L.LEGA.n_squadre if universo == "schierabili" else None
    mu_p, sd_p, pv_p = _mediano(profilo(giocatori, "p"), quanti_p)
    mu_d, sd_d, pv_d = _mediano(profilo(giocatori, "d"), quanti_d)
    return {
        "n_difensori": n_difensori,
        "universo": universo,
        "mu": np.array([mu_p] + [mu_d] * n_difensori),
        "sd": np.array([sd_p] + [sd_d] * n_difensori),
        "p_voto": np.array([pv_p] + [pv_d] * n_difensori),
    }


def contributo_marginale(giocatori: pd.DataFrame, moduli=None,
                         repliche: int = REPLICHE,
                         universo: str = "schierabili") -> pd.DataFrame:
    """Quanto vale ogni portiere e ogni difensore, **per modulo**.

    Il contributo e' `E[bonus con lui al posto di un riferimento]` meno
    `E[bonus della linea di riferimento pura]`, moltiplicato per le 38 giornate
    per esprimerlo in punti di stagione — che e' la scala su cui si compra.

    Restituisce una riga per giocatore **e per modulo**, mai una sola: con
    `n_difensori` che dipende dal modulo (decisione 0.2) lo stesso difensore ha
    tre contributi diversi, e schiacciarli in una media nasconderebbe proprio
    l'effetto che la decisione ha introdotto.
    """
    moduli = moduli or L.LEGA.moduli
    fuori = []
    for n_dif in sorted({m.n_difensori_modificatore for m in moduli}):
        rif = linea_riferimento(giocatori, n_dif, universo)
        base = simula_linea(rif["mu"], rif["sd"], rif["p_voto"],
                            repliche=repliche).mean()

        for ruolo, posizione in (("p", 0), ("d", 1)):
            d = profilo(giocatori, ruolo)
            for _, g in d.iterrows():
                mu = rif["mu"].copy(); sd = rif["sd"].copy(); pv = rif["p_voto"].copy()
                mu[posizione] = g["mu"]; sd[posizione] = g["sd"]; pv[posizione] = g["p_voto"]
                atteso = simula_linea(mu, sd, pv, repliche=repliche).mean()
                fuori.append({
                    "giocatore_id": g["giocatore_id"], "giocatore": g["giocatore"],
                    "ruolo": ruolo, "n_difensori": n_dif, "universo": universo,
                    "bonus_riferimento_per_giornata": round(float(base), 4),
                    "bonus_con_lui_per_giornata": round(float(atteso), 4),
                    "contributo_stagione": round(float(atteso - base) * GIORNATE, 2),
                })
    return pd.DataFrame(fuori)


def costo_della_media(giocatori: pd.DataFrame, n_difensori: int = 4,
                      repliche: int = REPLICHE,
                      universo: str = "schierabili") -> pd.DataFrame:
    """Quanto sbaglia chi applica le fasce alla media di stagione.

    E' la misura che §2.2 chiede esplicitamente — "il segno puo' andare in
    entrambe le direzioni e va misurato" — e non un controllo di stile: se i due
    coincidessero, tutta la simulazione sarebbe lavoro sprecato.
    """
    rif = linea_riferimento(giocatori, n_difensori, universo)
    simulato = simula_linea(rif["mu"], rif["sd"], rif["p_voto"],
                            repliche=repliche).mean()
    # La scorciatoia: una sola media, quella attesa, e una sola fascia.
    media_attesa = float(np.average(rif["mu"], weights=rif["p_voto"]))
    scorciatoia = L.modificatore(media_attesa)
    return pd.DataFrame([{
        "universo": universo, "n_difensori": n_difensori,
        "media_difensiva_attesa": round(media_attesa, 4),
        "bonus_da_media_di_stagione": scorciatoia,
        "bonus_simulato_per_giornata": round(float(simulato), 4),
        "scarto_per_giornata": round(float(simulato) - scorciatoia, 4),
        "scarto_di_stagione": round((float(simulato) - scorciatoia) * GIORNATE, 2),
    }])
