"""Assenza di leakage nell'xG interno.

L'xG viene poi usato come predittore di un modello stimato sulla stessa
stagione. Il vincolo e' che l'xG di un tiro non possa dipendere dall'esito di
quel tiro ne' da quello degli altri tiri della stessa partita.
"""

import numpy as np
from sklearn.model_selection import GroupKFold

from sot import xg as xg_mod


def test_i_fold_non_condividono_partite(shots):
    """Ogni fold di test deve avere partite disgiunte dal proprio train."""
    pen = xg_mod.is_penalty(shots)
    groups = shots["matchId"].to_numpy()[~pen]
    X = np.zeros((len(groups), 1))
    y = shots["is_goal"].astype(int).to_numpy()[~pen]

    gkf = GroupKFold(n_splits=xg_mod.N_FOLDS)
    for tr, te in gkf.split(X, y, groups):
        assert not (set(groups[tr]) & set(groups[te]))


def test_feature_non_contengono_esito(shots):
    """Nessuna feature deve essere una funzione dell'esito del tiro.

    In particolare `big_chance` e' l'unione di segnata e fallita, quindi non
    separa i gol dai non-gol; le due colonne prese singolarmente lo farebbero.
    """
    f = xg_mod.build_features(shots)
    y = shots["is_goal"].astype(int).to_numpy()
    for col in f.columns:
        v = f[col].to_numpy()
        if len(np.unique(v)) <= 1:
            continue
        # Una feature che identifica l'esito avrebbe correlazione |r| ~ 1.
        r = np.corrcoef(v, y)[0, 1]
        assert abs(r) < 0.9, (col, r)

    assert "bigChanceScored" not in f.columns
    assert "bigChanceMissed" not in f.columns


def test_xg_calibrato_in_aggregato(shots):
    """La somma degli xG deve avvicinarsi al numero di gol."""
    tot_xg = shots["xg"].sum()
    goals = shots["is_goal"].sum()
    assert abs(tot_xg - goals) / goals < 0.05, (tot_xg, goals)


def test_xg_batte_il_tasso_base(shots):
    m = xg_mod.evaluate(shots, shots["xg"])
    assert m["logloss_model"] < m["logloss_base"]


def test_xg_nel_dominio(shots):
    assert shots["xg"].between(0.0, 1.0).all()
    assert shots["xg"].notna().all()


def test_rigori_trattati_a_parte(shots):
    pen = xg_mod.is_penalty(shots)
    assert pen.sum() == 106
    assert (shots.loc[pen, "xg_source"] == "penalty_rate").all()
    assert (shots.loc[~pen, "xg_source"] == "model").all()
    # Il dischetto: controprova geometrica dell'identificazione.
    assert abs(shots.loc[pen, "x"].mean() - 88.5) < 0.5
    assert abs(shots.loc[pen, "y"].mean() - 50.0) < 0.5
