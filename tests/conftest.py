"""Fixture condivise: le tabelle di Fase 1, costruite una volta per sessione."""

import pytest

from sot import aggregate, config, io_events, minutes as minutes_mod


@pytest.fixture(scope="session")
def tables():
    if not (config.TEAM_MATCH.exists() and config.PLAYER_MATCH.exists()
            and config.SHOTS_PARQUET.exists()):
        return aggregate.run()
    import pandas as pd
    return {
        "team_match": pd.read_parquet(config.TEAM_MATCH),
        "player_match": pd.read_parquet(config.PLAYER_MATCH),
        "shots": pd.read_parquet(config.SHOTS_PARQUET),
    }


@pytest.fixture(scope="session")
def team_match(tables):
    return tables["team_match"]


@pytest.fixture(scope="session")
def player_match(tables):
    return tables["player_match"]


@pytest.fixture(scope="session")
def shots(tables):
    return tables["shots"]


@pytest.fixture(scope="session")
def events():
    return io_events.load_events()


@pytest.fixture(scope="session")
def lineup():
    return io_events.load_lineup_events()


@pytest.fixture(scope="session")
def mins(lineup, events):
    return minutes_mod.minutes_played(lineup, events)
