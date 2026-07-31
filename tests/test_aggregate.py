"""Riconciliazione giocatori -> squadra.

Il vincolo richiesto e' esatto, non approssimato: per ogni singola partita la
somma dei tiri in porta dei giocatori deve coincidere con il totale di
squadra. Tolleranza zero.
"""

import numpy as np
import pandas as pd


def _reconcile(player_match, team_match, col):
    per_team = (player_match.groupby(["matchId", "teamId"])[col].sum()
                .rename("from_players"))
    totals = team_match.set_index(["matchId", "teamId"])[col].rename("from_team")
    return pd.concat([per_team, totals], axis=1).fillna(0)


def test_sot_giocatori_uguale_totale_squadra(player_match, team_match):
    j = _reconcile(player_match, team_match, "sot")
    bad = j[j["from_players"] != j["from_team"]]
    assert bad.empty, bad.head(20).to_dict()


def test_tiri_giocatori_uguale_totale_squadra(player_match, team_match):
    j = _reconcile(player_match, team_match, "shots")
    bad = j[j["from_players"] != j["from_team"]]
    assert bad.empty, bad.head(20).to_dict()


def test_gol_giocatori_uguale_totale_squadra(player_match, team_match):
    j = _reconcile(player_match, team_match, "goals")
    bad = j[j["from_players"] != j["from_team"]]
    assert bad.empty, bad.head(20).to_dict()


def test_xg_giocatori_uguale_totale_squadra(player_match, team_match):
    j = _reconcile(player_match, team_match, "xg")
    assert np.allclose(j["from_players"], j["from_team"], atol=1e-9)


def test_tutte_le_squadre_partita_presenti(player_match, team_match):
    """Anche chi non ha tirato deve comparire, con 0, non sparire."""
    a = set(map(tuple, team_match[["matchId", "teamId"]].to_numpy()))
    b = set(map(tuple, player_match[["matchId", "teamId"]].drop_duplicates().to_numpy()))
    assert a == b


def test_sot_mai_maggiore_dei_tiri(team_match, player_match):
    assert (team_match["sot"] <= team_match["shots"]).all()
    assert (player_match["sot"] <= player_match["shots"]).all()


def test_gol_mai_maggiori_dei_sot(team_match):
    """Ogni gol regolare e' un tiro in porta, quindi gol <= SoT."""
    assert (team_match["goals"] <= team_match["sot"]).all()


def test_possesso_e_field_tilt_sommano_a_uno(team_match):
    for col in ("possession", "field_tilt"):
        s = team_match.groupby("matchId")[col].sum()
        assert np.allclose(s.dropna(), 1.0, atol=1e-9), col


def test_avversario_coerente(team_match):
    """L'avversario di A in una partita deve avere A come avversario."""
    m = team_match.set_index(["matchId", "teamId"])["opponentId"]
    for (mid, tid), opp in m.items():
        assert m[(mid, opp)] == tid


def test_xg_concesso_e_il_xg_dell_avversario(team_match):
    idx = team_match.set_index(["matchId", "teamId"])
    for row in team_match.itertuples(index=False):
        assert abs(idx.loc[(row.matchId, row.opponentId), "xg"] - row.xg_conceded) < 1e-9
