"""Definizione unica di "tiro in porta" per tutto il repo.

REGOLA ADOTTATA
---------------
    isShot AND ( (type == 'SavedShot' AND NOT shotBlocked)
                 OR (type == 'Goal'  AND NOT isOwnGoal) )

Cosa include: le conclusioni parate dal portiere e i gol.

Cosa esclude, e perche':

* `MissedShots` — fuori bersaglio, per definizione.
* `ShotOnPost` (pali) — WhoScored li tiene in un tipo evento a se'. Non sono
  conteggiati come tiri in porta dalla convenzione Opta standard, che e' quella
  dei valori di riferimento. Includerli porterebbe la media di campionato da
  4.03 a 4.27.
* `SavedShot` con `shotBlocked == True` — respinte di un difensore. WhoScored
  usa lo stesso tipo evento `SavedShot` sia per le parate del portiere sia per
  i blocchi di un giocatore di movimento: `shotBlocked` e' l'unico
  discriminante. Non sono tiri in porta.
* autogol (`isOwnGoal`) — non sono un tiro in porta della squadra che segna,
  e non vanno attribuiti a chi li subisce.

VERIFICA: questa regola coincide esattamente, evento per evento, con il flag
Opta nativo `shotOnTarget` presente nei dati (3066 = 3066 sulla stagione). Le
due definizioni sono state calcolate in parallelo, non per tentativi
successivi. I gol regolari portano gia' `shotOnTarget = True`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def shots_on_target_mask(events: pd.DataFrame) -> pd.Series:
    """Maschera booleana dei tiri in porta. Vedi la docstring del modulo."""
    is_shot = events["isShot"].astype("boolean").fillna(False)
    blocked = events["shotBlocked"].astype("boolean").fillna(False)
    own = events["isOwnGoal"].astype("boolean").fillna(False)

    saved = (events["type"] == "SavedShot") & ~blocked
    goal = (events["type"] == "Goal") & ~own
    return (is_shot & (saved | goal)).astype(bool)


def shots_mask(events: pd.DataFrame) -> pd.Series:
    """Maschera dei tiri totali: tutti i tentativi, autogol esclusi.

    Comprende quindi `MissedShots`, `SavedShot` (parati e respinti),
    `ShotOnPost` e i gol regolari.
    """
    is_shot = events["isShot"].astype("boolean").fillna(False)
    own = events["isOwnGoal"].astype("boolean").fillna(False)
    return (is_shot & ~own).astype(bool)


def shot_frame(events: pd.DataFrame) -> pd.DataFrame:
    """Sotto-tabella dei soli tiri, con geometria e flag pronti per l'xG."""
    sh = events.loc[shots_mask(events)].copy()
    sh["is_sot"] = shots_on_target_mask(sh).to_numpy()
    sh["is_goal"] = sh["isGoal"].astype("boolean").fillna(False).to_numpy()
    sh = sh.join(shot_geometry(sh))
    return sh


def shot_geometry(shots: pd.DataFrame) -> pd.DataFrame:
    """Distanza e angolo di tiro in metri / radianti.

    Le coordinate Opta sono 0-100 su entrambi gli assi e le squadre attaccano
    sempre verso x = 100 (verificato: x medio dei tiri 85.2, solo 39 tiri su
    9381 con x < 50). Nessun ribaltamento necessario.
    """
    from .config import GOAL_X, GOAL_Y, PITCH_LENGTH_M, PITCH_WIDTH_M, GOAL_WIDTH_M

    dx = (GOAL_X - shots["x"].to_numpy()) * PITCH_LENGTH_M / 100.0
    dy = (shots["y"].to_numpy() - GOAL_Y) * PITCH_WIDTH_M / 100.0

    dist = np.sqrt(dx ** 2 + dy ** 2)

    # Angolo sotteso dalla porta, formula standard.
    half = GOAL_WIDTH_M / 2.0
    a = np.sqrt((dy - half) ** 2 + dx ** 2)
    b = np.sqrt((dy + half) ** 2 + dx ** 2)
    cos = np.clip((a ** 2 + b ** 2 - GOAL_WIDTH_M ** 2) / (2 * a * b), -1.0, 1.0)
    angle = np.arccos(cos)

    return pd.DataFrame(
        {"shot_distance_m": dist, "shot_angle_rad": angle},
        index=shots.index,
    )
