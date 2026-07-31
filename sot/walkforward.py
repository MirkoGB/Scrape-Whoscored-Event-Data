"""Protocollo walk-forward e costruzione dei predittori pre-partita.

Regola non negoziabile: per prevedere una partita si usano **esclusivamente**
partite con data strettamente antecedente. Vale per la stima dei parametri,
per la scelta di alpha, per le medie mobili dei predittori e per i baseline.

La suddivisione avviene per **data**, non per giornata: i recuperi
disallineano le giornate ufficiali e userebbero, per una squadra, partite che
al momento della previsione non erano ancora state giocate.
"""

from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd

from . import config


def pre_match_ewm(df: pd.DataFrame, cols: list[str],
                  half_life: float = config.HALF_LIFE_DAYS,
                  by: str = "team") -> pd.DataFrame:
    """Media a decadimento esponenziale delle partite **precedenti**.

    Il valore della partita corrente e' escluso: la riga della prima partita di
    una squadra e' NaN, la seconda usa solo la prima, e cosi' via. Includere la
    partita corrente sarebbe la forma piu' banale di leakage.
    """
    out = pd.DataFrame(index=df.index, columns=cols, dtype=float)

    for _, g in df.groupby(by, sort=False):
        g = g.sort_values("date")
        t = g["date"].to_numpy(dtype="datetime64[ns]").astype("float64") / 86_400e9
        vals = g[cols].to_numpy(dtype=float)

        for i in range(1, len(g)):
            age = t[i] - t[:i]
            w = 0.5 ** (age / half_life)
            v = vals[:i]
            mask = ~np.isnan(v)
            wm = np.where(mask, w[:, None], 0.0)
            denom = wm.sum(axis=0)
            num = np.nansum(np.where(mask, v, 0.0) * wm, axis=0)
            out.loc[g.index[i]] = np.where(denom > 0, num / np.where(denom > 0, denom, 1), np.nan)

    return out


# Predittori candidati: (nome, colonna di origine, lato).
# "att"  = storia della squadra stessa
# "def"  = storia dell'avversario (cio' che l'avversario concede o impone)
CANDIDATES = {
    "xgps_att": ("xg_per_shot", "att"),
    "xgps_def": ("xg_per_shot_conceded", "def"),
    "poss_att": ("possession", "att"),
    "tilt_att": ("field_tilt", "att"),
    "box_att": ("box_touches", "att"),
    "dist_att": ("mean_shot_distance", "att"),
    "ppda_att": ("ppda", "att"),
    "ppda_def": ("ppda", "def"),
}


def build_predictors(team_match: pd.DataFrame,
                     half_life: float = config.HALF_LIFE_DAYS) -> pd.DataFrame:
    """Aggiunge a `team_match` i predittori pre-partita candidati."""
    df = team_match.sort_values("date").reset_index(drop=True).copy()

    src_cols = sorted({c for c, _ in CANDIDATES.values()})
    hist = pre_match_ewm(df, src_cols, half_life=half_life, by="team")
    hist.columns = [f"_ewm_{c}" for c in hist.columns]
    df = pd.concat([df, hist], axis=1)

    # Lato difensivo: la storia dell'avversario, agganciata per (matchId, team).
    opp = df[["matchId", "team"] + list(hist.columns)].rename(
        columns={"team": "opponent", **{c: f"{c}__opp" for c in hist.columns}})
    df = df.merge(opp, on=["matchId", "opponent"], how="left")

    for name, (src, side) in CANDIDATES.items():
        col = f"_ewm_{src}" + ("__opp" if side == "def" else "")
        df[name] = df[col]

    return df.drop(columns=[c for c in df.columns if c.startswith("_ewm_")])


def eligible(df: pd.DataFrame, burn_in: int = config.BURN_IN_ROUND) -> pd.Series:
    """Righe valutabili: la squadra deve avere almeno `burn_in - 1` precedenti.

    Le prime giornate non hanno storia e il modello vi coincide quasi con
    l'intercetta. Valutarle misurerebbe soprattutto il cold start. La soglia e'
    dichiarata, e i baseline sono confrontati sullo **stesso** sottoinsieme.
    """
    return df["team_match_idx"] >= burn_in


def date_splits(df: pd.DataFrame, min_train_matches: int = 30
                ) -> Iterator[tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame]]:
    """Genera (data, train, test) per ogni data di calendario.

    `train` contiene solo righe con data strettamente minore.
    """
    dates = np.sort(df["date"].unique())
    for d in dates:
        train = df[df["date"] < d]
        if train["matchId"].nunique() < min_train_matches:
            continue
        test = df[df["date"] == d]
        if len(test):
            yield pd.Timestamp(d), train, test
