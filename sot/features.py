"""Predittori di contesto calcolati dagli eventi, per squadra-partita.

Tutte le coordinate sono Opta 0-100 e ogni squadra attacca verso x = 100 nel
proprio sistema di riferimento. Una posizione x per la squadra A corrisponde
quindi a 100 - x per la squadra B: e' il motivo per cui le soglie di PPDA
sembrano asimmetriche.

Geometria derivata dalle dimensioni regolamentari (105 x 68 m):
  area di rigore   x >= 84.29,  20.35 <= y <= 79.65   (16.5 m x 40.32 m)
  ultimo terzo     x >= 66.67
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BOX_X = 100.0 - 16.5 / 105.0 * 100.0          # 84.29
BOX_Y_LO = 50.0 - (40.32 / 68.0 * 100.0) / 2  # 20.35
BOX_Y_HI = 50.0 + (40.32 / 68.0 * 100.0) / 2  # 79.65
FINAL_THIRD_X = 200.0 / 3.0                   # 66.67

# Azioni difensive che entrano nel denominatore del PPDA.
DEF_ACTION_TYPES = ("Tackle", "Interception", "Challenge")


def _in_box(df: pd.DataFrame) -> np.ndarray:
    return ((df["x"] >= BOX_X) & df["y"].between(BOX_Y_LO, BOX_Y_HI)).to_numpy()


def team_context(events: pd.DataFrame) -> pd.DataFrame:
    """Una riga per (matchId, teamId) con i predittori di contesto."""
    ev = events
    key = ["matchId", "teamId"]

    touches = ev[ev["isTouch"]]
    tot_touch = touches.groupby(key).size().rename("touches")

    # --- possesso: quota di tocchi sul totale della partita ---
    match_touch = touches.groupby("matchId").size().rename("match_touches")

    # --- tocchi in area ---
    box = touches[_in_box(touches)].groupby(key).size().rename("box_touches")

    # --- field tilt: quota di tocchi nell'ultimo terzo sul totale dei due ---
    ft = touches[touches["x"] >= FINAL_THIRD_X]
    ft_team = ft.groupby(key).size().rename("ft_touches")
    ft_match = ft.groupby("matchId").size().rename("ft_match")

    out = (pd.concat([tot_touch, box, ft_team], axis=1)
           .reset_index()
           .fillna({"box_touches": 0, "ft_touches": 0}))
    out = out.merge(match_touch.reset_index(), on="matchId")
    out = out.merge(ft_match.reset_index(), on="matchId")

    out["possession"] = out["touches"] / out["match_touches"]
    out["field_tilt"] = out["ft_touches"] / out["ft_match"].replace(0, np.nan)

    return out.drop(columns=["match_touches", "ft_match", "ft_touches"])


def ppda(events: pd.DataFrame) -> pd.DataFrame:
    """PPDA: passaggi avversari concessi per azione difensiva.

    Definizione standard: passaggi tentati dall'avversario nei propri 60% di
    campo, divisi per le azioni difensive della squadra che pressa nella stessa
    zona. Valori **bassi** indicano pressing intenso.

    Nel sistema Opta di ogni squadra, "i propri 60%" dell'avversario sono
    x <= 60 nel frame dell'avversario, che corrisponde a x >= 40 nel frame di
    chi pressa.
    """
    ev = events
    passes = ev[(ev["type"] == "Pass") & (ev["x"] <= 60.0)]
    opp_passes = passes.groupby(["matchId", "teamId"]).size().rename("passes_own_60")

    is_def = ev["type"].isin(DEF_ACTION_TYPES) | ev["foulCommitted"]
    actions = ev[is_def & (ev["x"] >= 40.0)]
    def_actions = actions.groupby(["matchId", "teamId"]).size().rename("def_actions")

    df = (pd.concat([opp_passes, def_actions], axis=1)
          .fillna(0).reset_index())

    # Per ogni squadra servono i passaggi dell'AVVERSARIO: si ribalta sul match.
    tot_passes = df.groupby("matchId")["passes_own_60"].transform("sum")
    df["opp_passes_own_60"] = tot_passes - df["passes_own_60"]

    df["ppda"] = df["opp_passes_own_60"] / df["def_actions"].replace(0, np.nan)
    return df[["matchId", "teamId", "ppda", "def_actions", "opp_passes_own_60"]]


def shot_context(shots: pd.DataFrame) -> pd.DataFrame:
    """Aggregati sui tiri: volume, qualita', distanza."""
    sh = shots.copy()
    sh["big_chance"] = sh["bigChanceMissed"] | sh["bigChanceScored"]

    out = sh.groupby(["matchId", "teamId"]).agg(
        shots=("is_sot", "size"),
        sot=("is_sot", "sum"),
        goals=("is_goal", "sum"),
        xg=("xg", "sum"),
        mean_shot_distance=("shot_distance_m", "mean"),
        big_chances=("big_chance", "sum"),
    ).reset_index()

    out["xg_per_shot"] = out["xg"] / out["shots"].replace(0, np.nan)
    return out
