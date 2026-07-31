"""xG interno, stimato dai dati evento. NON e' l'xG di un fornitore.

I CSV WhoScored non contengono xG: `matchCentreData` non lo espone e nessuna
delle 259 colonne lo contiene. Va quindi stimato, e va detto chiaramente in
ogni output che si tratta di un xG interno, con una scala che non coincide
necessariamente con quella di Opta o StatsBomb.

LEAKAGE
-------
L'xG serve poi come predittore nel modello dei tiri in porta, stimato sulla
stessa stagione. Se ogni tiro ricevesse un xG da un modello addestrato anche
su quel tiro, l'informazione sull'esito rientrerebbe di soppiatto.

Si usa quindi **cross-fitting a 5 fold raggruppati per `matchId`**: l'xG di un
tiro proviene sempre da un modello che non ha visto ne' quel tiro ne' alcun
altro tiro della stessa partita. Raggruppare per partita, e non per singolo
tiro, e' essenziale: i tiri di una stessa partita condividono contesto, e
separarli lascerebbe passare informazione.

I rigori sono modellati a parte (tasso di conversione empirico): la loro
geometria e' degenere e li renderebbe punti di leva nel modello principale.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config

N_FOLDS = 5

# Feature numeriche e binarie usate dal modello.
NUM_FEATURES = ["shot_distance_m", "shot_angle_rad", "log_distance", "inv_distance"]
BIN_FEATURES = [
    "is_header", "is_weak_foot_unknown",
    "is_open_play", "is_counter", "is_set_piece", "is_corner",
    "in_six_yard", "in_box", "outside_box",
    "big_chance",
]


def build_features(shots: pd.DataFrame) -> pd.DataFrame:
    """Matrice di feature per l'xG, dai soli campi noti prima dell'esito."""
    f = pd.DataFrame(index=shots.index)

    dist = shots["shot_distance_m"].to_numpy()
    f["shot_distance_m"] = dist
    f["shot_angle_rad"] = shots["shot_angle_rad"].to_numpy()
    f["log_distance"] = np.log1p(dist)
    f["inv_distance"] = 1.0 / np.clip(dist, 1.0, None)

    body = shots["shotBodyType"].astype("string").fillna("")
    f["is_header"] = (body == "Head").to_numpy()
    f["is_weak_foot_unknown"] = (~body.isin(["Head", "LeftFoot", "RightFoot"])).to_numpy()

    f["is_open_play"] = shots["shotOpenPlay"].to_numpy()
    f["is_counter"] = shots["shotCounter"].to_numpy()
    f["is_set_piece"] = shots["shotSetPiece"].to_numpy()
    f["is_corner"] = shots["shotDirectCorner"].to_numpy()

    f["in_six_yard"] = shots["shotSixYardBox"].to_numpy()
    f["in_box"] = shots["shotPenaltyArea"].to_numpy()
    f["outside_box"] = shots["shotOboxTotal"].to_numpy()

    # "Grande occasione" come unione di segnata e fallita: l'unione non rivela
    # l'esito, mentre le due colonne separate lo rivelerebbero.
    f["big_chance"] = (shots["bigChanceMissed"] | shots["bigChanceScored"]).to_numpy()

    return f.astype(float)


def is_penalty(shots: pd.DataFrame) -> np.ndarray:
    """Rigori.

    Attenzione: la colonna `situation` **non** li marca — resta nulla su tutti
    e 106. L'unico segnale e' il qualifier `Penalty`, che equivale
    esattamente all'unione di `penaltyScored` e `penaltyMissed` (81 + 25 = 106,
    stessa cardinalita' del qualifier, zero eccezioni). Essendo l'unione di
    segnati e sbagliati, non rivela l'esito.

    Controprova geometrica: questi tiri hanno x medio 88.5 e y medio 50.0,
    cioe' il dischetto.
    """
    return (shots["penaltyScored"] | shots["penaltyMissed"]).to_numpy()


def _make_model() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(C=1.0, max_iter=2000,
                                   random_state=config.SEED)),
    ])


def fit_predict_xg(shots: pd.DataFrame) -> pd.DataFrame:
    """xG cross-fitted per ogni tiro.

    Ritorna un DataFrame con `xg` e `xg_source` ("model" o "penalty_rate").
    """
    shots = shots.copy()
    pen = is_penalty(shots)
    y = shots["is_goal"].astype(int).to_numpy()

    xg = np.full(len(shots), np.nan)

    # --- rigori: tasso empirico, anch'esso fuori campione per partita ---
    if pen.any():
        groups_p = shots.loc[pen, "matchId"].to_numpy()
        y_p = y[pen]
        idx_p = np.flatnonzero(pen)
        n_splits = min(N_FOLDS, len(np.unique(groups_p)))
        if n_splits >= 2:
            gkf = GroupKFold(n_splits=n_splits)
            for tr, te in gkf.split(idx_p, y_p, groups_p):
                xg[idx_p[te]] = y_p[tr].mean()
        else:
            xg[idx_p] = y_p.mean()

    # --- tiri su azione: logistica cross-fitted ---
    open_idx = np.flatnonzero(~pen)
    X = build_features(shots).to_numpy()[open_idx]
    y_o = y[open_idx]
    groups = shots["matchId"].to_numpy()[open_idx]

    gkf = GroupKFold(n_splits=N_FOLDS)
    for tr, te in gkf.split(X, y_o, groups):
        model = _make_model()
        model.fit(X[tr], y_o[tr])
        xg[open_idx[te]] = model.predict_proba(X[te])[:, 1]

    out = pd.DataFrame(
        {"xg": xg, "xg_source": np.where(pen, "penalty_rate", "model")},
        index=shots.index,
    )
    return out


def fit_full(shots: pd.DataFrame) -> Pipeline:
    """Modello xG stimato su tutti i tiri su azione.

    Serve solo per ispezionare i coefficienti nei report. **Non** va usato per
    assegnare xG ai tiri della stagione: per quello esiste `fit_predict_xg`.
    """
    pen = is_penalty(shots)
    X = build_features(shots).to_numpy()[~pen]
    y = shots["is_goal"].astype(int).to_numpy()[~pen]
    model = _make_model()
    model.fit(X, y)
    return model


def evaluate(shots: pd.DataFrame, xg: pd.Series) -> dict:
    """Log-loss e calibrazione dell'xG, sempre contro il tasso base."""
    from sklearn.metrics import log_loss, roc_auc_score

    y = shots["is_goal"].astype(int).to_numpy()
    p = np.clip(xg.to_numpy(), 1e-6, 1 - 1e-6)
    base = np.full_like(p, y.mean())

    return {
        "n_shots": int(len(y)),
        "n_goals": int(y.sum()),
        "base_rate": float(y.mean()),
        "logloss_model": float(log_loss(y, p)),
        "logloss_base": float(log_loss(y, base)),
        "auc": float(roc_auc_score(y, p)),
        "xg_sum": float(p.sum()),
        "goals": int(y.sum()),
    }


def reliability(shots: pd.DataFrame, xg: pd.Series, bins: int = 10) -> pd.DataFrame:
    """Tabella di affidabilita': xG medio vs gol effettivi, per decile."""
    df = pd.DataFrame({"xg": xg.to_numpy(),
                       "goal": shots["is_goal"].astype(int).to_numpy()})
    df["bin"] = pd.qcut(df["xg"], bins, duplicates="drop")
    out = df.groupby("bin", observed=True).agg(
        n=("goal", "size"),
        xg_mean=("xg", "mean"),
        goal_rate=("goal", "mean"),
    ).reset_index()
    out["diff"] = out["goal_rate"] - out["xg_mean"]
    return out
