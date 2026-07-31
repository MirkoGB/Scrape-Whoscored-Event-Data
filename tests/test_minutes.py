"""Ricostruzione dei minuti.

I minuti non esistono nei dati e vanno derivati da formazioni, sostituzioni ed
espulsioni. Il controllo e' esatto: la somma dei minuti di una squadra in una
partita deve valere `11 * durata - minuti persi per inferiorita' numerica`.
"""

import numpy as np

from sot import minutes as minutes_mod


def test_riconciliazione_esatta(mins, lineup, events):
    dur = minutes_mod.match_duration(events)
    chk = minutes_mod.check_minutes(mins, lineup, dur)
    bad = chk[chk["diff"].abs() > 1e-9]
    assert bad.empty, bad[["matchId", "teamId", "tot_minutes",
                           "expected", "diff"]].head(20).to_dict("records")


def test_undici_titolari_per_squadra_partita(mins):
    starters = mins[mins["is_starter"]].groupby(["matchId", "teamId"]).size()
    assert (starters == 11).all(), starters[starters != 11].to_dict()


def test_un_portiere_titolare_per_squadra_partita(mins):
    gk = mins[(mins["is_starter"]) & (mins["role_code"] == 1)]
    counts = gk.groupby(["matchId", "teamId"]).size()
    assert len(counts) == 760
    assert (counts == 1).all()


def test_minuti_non_negativi_e_plausibili(mins, events):
    dur = minutes_mod.match_duration(events)
    assert (mins["minutes"] >= 0).all()
    cap = mins["matchId"].map(dur).astype(float)
    assert (mins["minutes"] <= cap + 1e-9).all()


def test_titolari_non_sostituiti_giocano_tutta_la_partita(mins, events):
    dur = minutes_mod.match_duration(events)
    full = mins[mins["is_starter"] & (mins["start_min"] == 0)]
    played_all = full[full["end_min"] == full["matchId"].map(dur).astype(float)]
    assert len(played_all) > 0
    assert np.allclose(played_all["minutes"],
                       played_all["matchId"].map(dur).astype(float))


def test_massimo_cinque_subentrati_per_squadra_partita(mins):
    """Regolamento: cinque sostituzioni. Un sesto ingresso segnala un errore."""
    subs = mins[(~mins["is_starter"]) & (mins["minutes"] > 0)]
    counts = subs.groupby(["matchId", "teamId"]).size()
    assert counts.max() <= 5, counts[counts > 5].to_dict()


def test_ogni_giocatore_con_tiri_ha_minuti(player_match):
    """Non si puo' tirare senza essere in campo."""
    bad = player_match[(player_match["shots"] > 0) & (player_match["minutes"] <= 0)]
    assert bad.empty, bad[["matchId", "playerName", "shots", "minutes"]].head(10).to_dict("records")
