"""Costruzione delle due tabelle di lavoro della Fase 1.

`team_match`   760 righe (380 partite x 2 squadre)
`player_match` una riga per giocatore convocato per partita

Da qui in poi si lavora sui Parquet: gli eventi grezzi non vengono piu' letti.

Nota sulle squadre-partita a zero tiri: la tabella parte dall'elenco completo
delle 760 coppie (matchId, teamId) presenti negli eventi, non dal groupby dei
tiri. Altrimenti una squadra che non ha tirato sparirebbe dal campione invece
di comparire con 0, e la media di campionato risulterebbe gonfiata.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, features, io_events, minutes as mins_mod, shots as shots_mod, xg as xg_mod


def _base_team_match(events: pd.DataFrame) -> pd.DataFrame:
    """Scheletro: tutte le 760 coppie squadra-partita, con data e avversario."""
    base = (events.groupby(["matchId", "teamId"])
            .agg(h_a=("h_a", "first"), date=("startDate", "first"))
            .reset_index())

    opp = base[["matchId", "teamId"]].rename(columns={"teamId": "opponentId"})
    base = base.merge(opp, on="matchId")
    base = base[base["teamId"] != base["opponentId"]].reset_index(drop=True)

    base["is_home"] = (base["h_a"] == "h").astype(int)

    names = io_events.team_id_map(events)
    base["team"] = base["teamId"].map(names)
    base["opponent"] = base["opponentId"].map(names)

    # Indice cronologico della partita per ciascuna squadra (1..38).
    # NON e' la giornata ufficiale: i recuperi la disallineano. La validazione
    # walk-forward usa comunque la data, non questo indice.
    base = base.sort_values(["teamId", "date"]).reset_index(drop=True)
    base["team_match_idx"] = base.groupby("teamId").cumcount() + 1

    return base


def build_shots(events: pd.DataFrame) -> pd.DataFrame:
    """Tabella dei tiri con xG cross-fitted."""
    sh = shots_mod.shot_frame(events)
    sh = sh.join(xg_mod.fit_predict_xg(sh))
    return sh


def build_team_match(events: pd.DataFrame, shots: pd.DataFrame) -> pd.DataFrame:
    base = _base_team_match(events)

    parts = [
        features.shot_context(shots),
        features.team_context(events),
        features.ppda(events),
    ]
    out = base
    for p in parts:
        out = out.merge(p, on=["matchId", "teamId"], how="left")

    count_cols = ["shots", "sot", "goals", "big_chances", "box_touches"]
    out[count_cols] = out[count_cols].fillna(0).astype(int)
    out["xg"] = out["xg"].fillna(0.0)

    # xG e distanza concessi: gli stessi valori, visti dall'avversario.
    conceded = out[["matchId", "teamId", "xg", "shots", "sot", "xg_per_shot"]].rename(
        columns={"teamId": "opponentId", "xg": "xg_conceded",
                 "shots": "shots_conceded", "sot": "sot_conceded",
                 "xg_per_shot": "xg_per_shot_conceded"})
    out = out.merge(conceded, on=["matchId", "opponentId"], how="left")

    cols = ["matchId", "date", "team", "teamId", "opponent", "opponentId",
            "is_home", "team_match_idx",
            "shots", "sot", "goals", "xg", "xg_per_shot", "big_chances",
            "mean_shot_distance", "possession", "field_tilt", "box_touches",
            "ppda", "def_actions",
            "shots_conceded", "sot_conceded", "xg_conceded", "xg_per_shot_conceded"]
    return out[cols].sort_values(["date", "matchId", "is_home"]).reset_index(drop=True)


def build_player_match(events: pd.DataFrame, shots: pd.DataFrame,
                       lineup: pd.DataFrame) -> pd.DataFrame:
    mins = mins_mod.minutes_played(lineup, events)
    roles = mins_mod.season_roles(mins, events)

    sh = shots.dropna(subset=["playerId"]).copy()
    sh["playerId"] = sh["playerId"].astype("int64")
    per_player = sh.groupby(["matchId", "teamId", "playerId"]).agg(
        shots=("is_sot", "size"),
        sot=("is_sot", "sum"),
        goals=("is_goal", "sum"),
        xg=("xg", "sum"),
    ).reset_index()
    per_player["playerId"] = per_player["playerId"].astype("Int64")

    out = mins.merge(per_player, on=["matchId", "teamId", "playerId"], how="left")
    for c in ["shots", "sot", "goals"]:
        out[c] = out[c].fillna(0).astype(int)
    out["xg"] = out["xg"].fillna(0.0)

    # Ruolo di stagione (quello per-partita e' assente per i panchinari).
    out = out.drop(columns=["role", "role_code"]).merge(roles, on="playerId", how="left")

    names = (events.dropna(subset=["playerId"])
             .assign(playerId=lambda d: d["playerId"].astype("int64"))
             .groupby("playerId")["playerName"].first())
    out["playerName"] = out["playerId"].map(names)

    meta = _base_team_match(events)[["matchId", "teamId", "team", "opponent",
                                     "is_home", "date", "team_match_idx"]]
    out = out.merge(meta, on=["matchId", "teamId"], how="left")

    cols = ["matchId", "date", "team", "teamId", "opponent", "is_home",
            "team_match_idx", "playerId", "playerName", "role", "role_inferred",
            "is_starter", "minutes", "shots", "sot", "goals", "xg"]
    return out[cols].sort_values(["date", "matchId", "teamId", "minutes"],
                                 ascending=[True, True, True, False]).reset_index(drop=True)


def run(force: bool = False) -> dict[str, pd.DataFrame]:
    """Costruisce e salva le tabelle di Fase 1."""
    events = io_events.load_events(force=force)
    lineup = io_events.load_lineup_events()

    shots = build_shots(events)
    team = build_team_match(events, shots)
    player = build_player_match(events, shots, lineup)

    shots.to_parquet(config.SHOTS_PARQUET, index=False)
    team.to_parquet(config.TEAM_MATCH, index=False)
    player.to_parquet(config.PLAYER_MATCH, index=False)

    return {"shots": shots, "team_match": team, "player_match": player}


def load_team_match() -> pd.DataFrame:
    return pd.read_parquet(config.TEAM_MATCH)


def load_player_match() -> pd.DataFrame:
    return pd.read_parquet(config.PLAYER_MATCH)
