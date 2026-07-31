# -*- coding: utf-8 -*-
"""Modello per giocatore, rosa 2026-27 e ricomposizione."""

import numpy as np
import pandas as pd
import pytest

from sot import config, model_player as MP, project_2627 as P, squad_2627 as SQ


@pytest.fixture(scope="module")
def player_ctx(player_match, team_match):
    d = MP.with_context(player_match, team_match)
    du = d[MP.usable(d)].reset_index(drop=True)
    return du, MP.PlayerModel(tau=3.0).fit(du)


# ------------------------------------------------------------ modello giocatore
def test_portieri_esclusi_senza_perdere_tiri(player_match, team_match):
    """I portieri non tirano mai: escluderli non deve perdere nemmeno un SoT."""
    d = MP.with_context(player_match, team_match)
    assert d.loc[~MP.usable(d), "sot"].sum() == 0


def test_ricomposizione_riproduce_i_totali(player_ctx):
    """La somma dei lambda dei giocatori deve dare il totale di campionato."""
    du, m = player_ctx
    assert abs(m.predict(du).sum() - du["sot"].sum()) < 1.0


def test_ricomposizione_per_squadra_accurata(player_ctx, team_match):
    du, m = player_ctx
    du = du.assign(lam=m.predict(du))
    per_team = du.groupby("team")["lam"].sum() / 38
    obs = team_match.groupby("team")["sot"].mean()
    assert np.corrcoef(per_team, obs[per_team.index])[0, 1] > 0.95


def test_shrinkage_piu_forte_con_pochi_minuti(player_ctx):
    """Chi ha giocato poco deve finire piu' vicino alla media del suo ruolo."""
    du, m = player_ctx
    tot = du.groupby(["playerId", "role"], as_index=False).agg(minutes=("minutes", "sum"))
    v = m.player_effects().set_index("playerId")["v"]
    tot["absv"] = tot["playerId"].map(v).abs()
    low = tot[tot["minutes"] < 300]["absv"].mean()
    high = tot[tot["minutes"] > 2000]["absv"].mean()
    assert low < high


def test_tassi_estremi_vengono_compressi(player_ctx):
    """Nessun tasso di modello puo' avvicinarsi ai 6.9 SoT/90 grezzi su 26 minuti."""
    du, m = player_ctx
    tot = du.groupby(["playerId", "role"], as_index=False).agg(minutes=("minutes", "sum"))
    assert m.rate_per90(tot).max() < 2.5


def test_correzione_di_contesto_ha_il_segno_giusto(player_ctx, team_match):
    """In una squadra forte il tasso di modello deve stare sotto il grezzo."""
    du, m = player_ctx
    como = du[du["team"] == "Como"].groupby(
        ["playerId", "role"], as_index=False).agg(minutes=("minutes", "sum"),
                                                  sot=("sot", "sum"))
    como = como[como["minutes"] > 900]
    grezzo = como["sot"] / como["minutes"] * 90
    modello = m.rate_per90(como)
    assert (modello < grezzo).mean() > 0.7


# --------------------------------------------------------------------- rosa
def test_rosa_completa_e_senza_duplicati():
    sq = SQ.squad()
    assert len(sq) == 26
    assert not sq["name"].duplicated().any()
    ids = sq["playerId"].dropna()
    assert not ids.duplicated().any()
    assert sq["role"].isin(["GK", "DEF", "MID", "FWD"]).all()


def test_id_della_rosa_esistono_nei_dati(player_match):
    sq = SQ.squad()
    known = set(player_match["playerId"].dropna().astype(int))
    for pid in sq["playerId"].dropna().astype(int):
        assert pid in known, pid


def test_i_confermati_giocavano_nel_como(player_match):
    sq = SQ.squad()
    como = set(player_match.loc[player_match["team"] == "Como", "playerId"]
               .dropna().astype(int))
    for pid in sq.loc[~sq["is_new"], "playerId"].dropna().astype(int):
        assert pid in como, pid


def test_minuti_proiettati_rispettano_il_budget():
    proj = SQ.project_minutes()
    assert abs(proj["minutes_proj"].sum() - SQ.OUTFIELD_MINUTES_BUDGET) < 1.0
    assert (proj["minutes_proj"] > 0).all()
    assert "GK" not in set(proj["role"])


def test_rotazione_comprime_i_titolari():
    """Piu' rotazione = meno minuti ai titolarissimi, piu' alla rosa."""
    a = SQ.project_minutes(rotation=0.0).set_index("name")["minutes_proj"]
    b = SQ.project_minutes(rotation=0.30).set_index("name")["minutes_proj"]
    top = a.idxmax()
    assert b[top] < a[top]
    assert b.std() < a.std()


# -------------------------------------------------------------- proiezione
def test_proiezione_in_un_intervallo_plausibile(player_match, team_match):
    _, s, _, _ = P.build_projection(player_match, team_match)
    assert 3.5 < s["lambda_bottomup_2627"] < 6.5
    assert 0.8 < s["ratio"] < 1.25


def test_monte_carlo_riproducibile(player_match, team_match):
    proj, s, model, _ = P.build_projection(player_match, team_match)
    a = P.monte_carlo(proj, s, model, r=26.0, n_sim=2000)
    b = P.monte_carlo(proj, s, model, r=26.0, n_sim=2000)
    assert np.array_equal(a, b)


def test_ogni_fonte_contribuisce_varianza_positiva(player_match, team_match):
    proj, s, model, _ = P.build_projection(player_match, team_match)
    for src in P.SOURCES:
        v = P.monte_carlo(proj, s, model, r=26.0, n_sim=4000, sources=(src,)).var()
        assert v > 0, src


def test_lo_shock_di_squadra_e_quello_ereditato(player_match, team_match):
    """Il Monte Carlo non deve ridurre lo shock di squadra di nascosto.

    La sua varianza deve restare quella implicata dal riferimento dall'alto
    (65% della varianza totale di 186 con IC80% [152, 222]).
    """
    proj, s, model, _ = P.build_projection(player_match, team_match)
    v = P.monte_carlo(proj, s, model, r=26.0, n_sim=20000,
                      sources=("team_shock",)).var()
    expected = P.TEAM_SHOCK_SHARE * P.TOPDOWN_SEASON_SD ** 2
    assert abs(v / expected - 1.0) < 0.20, (v, expected)


def test_test_mezza_stagione_usa_solo_il_primo_tempo(player_match, team_match):
    ht = P.first_half_test(player_match, team_match, split=19)
    assert len(ht) == 20
    assert ht[["topdown", "livello_dai_giocatori", "compositivo",
               "actual_h2"]].notna().all().all()
