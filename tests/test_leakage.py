"""Nessuna stima puo' vedere dati che seguono il target.

Questo e' il vincolo che, se violato, produce i risultati "troppo belli". I
test qui sotto lo verificano meccanicamente invece di affidarsi alla lettura
del codice.
"""

import numpy as np
import pandas as pd
import pytest

from sot import aggregate, config, walkforward as wf


@pytest.fixture(scope="module")
def preds(team_match):
    return wf.build_predictors(team_match)


def test_train_sempre_antecedente_al_test(preds):
    """Per ogni split, la data massima del train precede quella del test."""
    n = 0
    for as_of, train, test in wf.date_splits(preds):
        assert train["date"].max() < test["date"].min()
        assert (test["date"] == as_of).all()
        n += 1
    assert n > 50, f"solo {n} split: il protocollo non sta girando"


def test_split_non_condividono_partite(preds):
    for _, train, test in wf.date_splits(preds):
        assert not (set(train["matchId"]) & set(test["matchId"]))


def test_predittori_escludono_la_partita_corrente(team_match):
    """La media mobile non deve contenere il valore della partita stessa.

    Controprova diretta: se la si ricalcola dopo aver alterato il valore di una
    partita, il predittore di quella stessa partita non deve cambiare.
    """
    df = wf.build_predictors(team_match)
    tampered = team_match.copy()
    row = tampered.index[400]
    tampered.loc[row, "possession"] = 0.99
    df2 = wf.build_predictors(tampered)

    key = ["matchId", "team"]
    a = df.set_index(key)["poss_att"]
    b = df2.set_index(key)["poss_att"]
    k = tuple(team_match.loc[row, key])
    assert a[k] == b[k] or (np.isnan(a[k]) and np.isnan(b[k]))


def test_prima_partita_senza_storia(preds):
    """La prima partita di ogni squadra non puo' avere una media del passato."""
    first = preds[preds["team_match_idx"] == 1]
    assert first[list(wf.CANDIDATES)].isna().all().all()


def test_predittore_usa_solo_partite_precedenti(team_match):
    """Ricostruzione manuale della media mobile per una riga a campione."""
    df = wf.build_predictors(team_match)
    row = df[(df["team"] == "Como") & (df["team_match_idx"] == 12)].iloc[0]
    past = team_match[(team_match["team"] == "Como")
                      & (team_match["date"] < row["date"])]
    assert len(past) == 11

    age = (row["date"] - past["date"]).dt.days.to_numpy()
    w = 0.5 ** (age / config.HALF_LIFE_DAYS)
    expected = np.sum(w * past["possession"].to_numpy()) / w.sum()
    assert abs(expected - row["poss_att"]) < 1e-9


def test_burn_in_esclude_le_prime_giornate(preds):
    el = wf.eligible(preds)
    assert preds.loc[el, "team_match_idx"].min() >= config.BURN_IN_ROUND
    assert not el[preds["team_match_idx"] < config.BURN_IN_ROUND].any()
