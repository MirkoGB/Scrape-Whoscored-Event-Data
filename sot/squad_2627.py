# -*- coding: utf-8 -*-
"""Rosa Como 2026-27 e proiezione dei minuti.

FONTE E LIMITI
--------------
Ricostruita il 30 luglio 2026 da Wikipedia italiana (rosa aggiornata al
1 luglio 2026) e inglese (6 aprile 2026). **Il mercato chiude il 1 settembre
2026**: questa rosa cambiera'. E' la fonte di incertezza piu' grande della
proiezione e non e' quantificabile dai dati — va dichiarata, non nascosta.

RUOLI
-----
I ruoli usati sono quelli **dei nostri dati** (posizione in formazione
WhoScored), non quelli di Wikipedia. Diao, Addai, Kuhn e Jesus Rodriguez sono
attaccanti per Wikipedia ma esterni offensivi schierati a centrocampo nel
2025-26: l'effetto `v` di ciascuno e' stimato rispetto alla media del proprio
ruolo, quindi cambiare etichetta qui e non nel modello introdurrebbe un errore
di scala. La coerenza interna conta piu' della nomenclatura.

I PORTIERI contribuiscono esattamente zero tiri in porta (0 su 72.176 minuti
in tutta la Serie A 2025-26) e sono esclusi dal calcolo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# (nome, playerId 2025-26 o None, ruolo nei nostri dati, minuti 25-26, SoT 25-26)
CONFIRMED = [
    ("Jean Butez",            256536, "GK",  3722,  0),
    ("Marc-Oliver Kempf",     116465, "DEF", 2548,  6),
    ("Alex Valle",            454341, "DEF", 2209,  2),
    ("Edoardo Goldaniga",     118148, "DEF",   18,  0),
    ("Jacobo Ramon",          516374, "DEF", 2977,  9),
    ("Ivan Smolcic",          531127, "DEF", 1814,  4),
    ("Ignace Van der Brempt", 402849, "DEF", 1019,  0),
    ("Maxence Caqueret",      368272, "MID", 1596,  4),
    ("Nico Paz",              448659, "MID", 3101, 48),
    ("Martin Baturina",       407944, "MID", 1719,  9),
    ("Maximo Perrone",        433972, "MID", 2959,  9),
    ("Lucas da Cunha",        379615, "MID", 2940, 16),
    ("Jesus Rodriguez",       539559, "MID", 1874, 12),
    ("Nicolas Kuhn",          420245, "MID",  757,  3),
    ("Assane Diao",           502427, "MID", 1143, 10),
    ("Jayden Addai",          510581, "MID",  741,  6),
    ("Alvaro Morata",          91213, "FWD", 1043,  8),
    ("Tasos Douvikas",        422873, "FWD", 2457, 30),
]

# Nuovi arrivi senza dati Serie A 2025-26. Ruolo da Wikipedia.
# Non avendo dati del loro campionato di provenienza (abbiamo solo Serie A),
# partono dalla media del ruolo con varianza fortemente gonfiata.
NEW_SIGNINGS = [
    ("Noel Tornqvist",  None, "GK"),
    ("Mauro Vigorito",  None, "GK"),
    ("Kaiki Bruno",     None, "DEF"),
    ("Andres Cuenca",   None, "DEF"),
    ("Adrian Lahdo",    None, "MID"),
    ("Luis Milla",      None, "MID"),
    ("Mattia Liberali", None, "MID"),
    ("Fabio Rispoli",   None, "MID"),
]

# Usciti dal Como 2025-26, con i minuti che liberano.
DEPARTED = [
    ("Diego Carlos",     2126,  2),
    ("Mergim Vojvoda",   1712,  7),
    ("Alberto Moreno",   1331,  4),
    ("Sergi Roberto",     636,  2),
    ("Stefan Posch",      465,  3),
    ("Andrea Le Borgne",    4,  0),
]

# Budget di minuti di movimento del Como 2025-26 (38 partite).
OUTFIELD_MINUTES_BUDGET = 37189.0
N_MATCHES = 38

# Compressione dei minuti dei titolarissimi verso la rosa allargata, per la
# rotazione dovuta alla Champions League. E' un'ASSUNZIONE: non e' stimabile
# dai dati 2025-26, in cui il Como non giocava le coppe europee. Viene fatta
# variare nel Monte Carlo.
ROTATION_DEFAULT = 0.15
ROTATION_RANGE = (0.05, 0.25)


def squad() -> pd.DataFrame:
    """Rosa 2026-27 con lo stato di ciascun giocatore."""
    rows = [{"name": n, "playerId": pid, "role": r,
             "minutes_2526": m, "sot_2526": s, "is_new": False}
            for n, pid, r, m, s in CONFIRMED]
    rows += [{"name": n, "playerId": pid, "role": r,
              "minutes_2526": 0.0, "sot_2526": 0, "is_new": True}
             for n, pid, r in NEW_SIGNINGS]
    return pd.DataFrame(rows)


def quote_minuti(base: np.ndarray, is_new: np.ndarray, freed: float,
                 rotation: float = 0.0) -> np.ndarray:
    """Quote di minuti di una rosa, dalla rosa e dai minuti del periodo passato.

    E' la procedura di `project_minutes` isolata dal caso Como 2026-27, perche'
    serve anche al test di mezza stagione (`project_2627.first_half_test`), che
    deve proiettare i minuti del secondo tempo di stagione **con la stessa
    regola** con cui la proiezione vera proietta il 2026-27. Se le due
    procedure divergessero, il test non testerebbe l'estimatore in uso.

    1. chi c'era gia' parte dai propri minuti del periodo passato;
    2. chi arriva si spartisce in parti uguali i minuti lasciati liberi da chi
       e' uscito;
    3. `rotation` comprime linearmente verso la quota uniforme.
    """
    base = np.asarray(base, dtype=float).copy()
    is_new = np.asarray(is_new, dtype=bool)
    n_new = int(is_new.sum())
    if n_new:
        base[is_new] = freed / n_new

    share = base / base.sum()
    uniform = np.full(len(share), 1.0 / len(share))
    share = (1.0 - rotation) * share + rotation * uniform
    return share / share.sum()


def project_minutes(sq: pd.DataFrame | None = None,
                    rotation: float = ROTATION_DEFAULT,
                    budget: float = OUTFIELD_MINUTES_BUDGET) -> pd.DataFrame:
    """Minuti di Serie A proiettati sul 2026-27, per i soli giocatori di movimento.

    Procedura:

    1. I confermati partono dai propri minuti 2025-26.
    2. I nuovi arrivi si spartiscono in parti uguali i minuti lasciati liberi
       dai partenti (6.274 su 6 giocatori di movimento, circa 1.046 a testa:
       un profilo da rotazione, non da titolare).
    3. Le quote si normalizzano al budget di minuti di movimento.
    4. `rotation` comprime linearmente le quote verso quella uniforme, per la
       rotazione dovuta alla Champions.

    I passi 1, 2 e 4 stanno in `quote_minuti`, che e' l'unica definizione della
    procedura: la usa anche il test di mezza stagione.
    """
    if sq is None:
        sq = squad()
    out = sq[sq["role"] != "GK"].copy()

    freed = sum(m for _, m, _ in DEPARTED)
    out["share"] = quote_minuti(out["minutes_2526"].to_numpy(dtype=float),
                                out["is_new"].to_numpy(), freed, rotation)
    out["minutes_proj"] = out["share"] * budget
    out["minutes_per_match"] = out["minutes_proj"] / N_MATCHES
    return out.sort_values("minutes_proj", ascending=False).reset_index(drop=True)
