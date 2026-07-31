"""Controllo di sanita' della definizione di tiro in porta.

Questi test NON esistono per far quadrare i numeri con i riferimenti: se un
giorno divergessero, la risposta e' indagare la causa, non ritoccare la
definizione. La soglia e' quella dichiarata nella specifica (5%); i valori
attuali stanno entro lo 0.2%.
"""

import pytest

from sot import config, shots as shots_mod


def _rel(a, b):
    return abs(a - b) / b


def test_numero_partite(team_match):
    assert team_match["matchId"].nunique() == config.REF_N_MATCHES
    assert len(team_match) == 2 * config.REF_N_MATCHES


def test_media_campionato(team_match):
    got = team_match["sot"].mean()
    assert _rel(got, config.REF_LEAGUE_MEAN) < config.SANITY_TOLERANCE, got


def test_media_casa_trasferta(team_match):
    home = team_match.loc[team_match["is_home"] == 1, "sot"].mean()
    away = team_match.loc[team_match["is_home"] == 0, "sot"].mean()
    assert _rel(home, config.REF_HOME_MEAN) < config.SANITY_TOLERANCE, home
    assert _rel(away, config.REF_AWAY_MEAN) < config.SANITY_TOLERANCE, away


def test_media_como(team_match):
    got = team_match.loc[team_match["team"] == "Como", "sot"].mean()
    assert _rel(got, config.REF_COMO_MEAN) < config.SANITY_TOLERANCE, got


def test_ogni_squadra_gioca_38_partite(team_match):
    counts = team_match.groupby("team").size()
    assert len(counts) == 20
    assert (counts == 38).all(), counts[counts != 38].to_dict()


def test_definizione_coincide_con_flag_opta(events):
    """La regola adottata deve coincidere evento per evento con `shotOnTarget`.

    Se questo test fallisce, la nostra definizione si e' scostata dalla
    convenzione Opta: va segnalato, non aggiustato.
    """
    ours = shots_mod.shots_on_target_mask(events)
    opta = events["shotOnTarget"].astype(bool)
    assert int(ours.sum()) == int(opta.sum())
    assert (ours == opta).all(), int((ours != opta).sum())


def test_pali_esclusi(events):
    """I pali non sono tiri in porta: includerli porterebbe la media a 4.27."""
    mask = shots_mod.shots_on_target_mask(events)
    assert not mask[events["type"] == "ShotOnPost"].any()


def test_tiri_respinti_esclusi(events):
    """`SavedShot` con `shotBlocked` e' una respinta di un difensore."""
    mask = shots_mod.shots_on_target_mask(events)
    assert not mask[events["shotBlocked"].astype(bool)].any()


def test_autogol_esclusi(events):
    mask = shots_mod.shots_on_target_mask(events)
    assert not mask[events["isOwnGoal"].astype(bool)].any()


def test_nessun_duplicato_squadra_partita(team_match):
    assert not team_match.duplicated(subset=["matchId", "teamId"]).any()
