"""Baseline stupidi.

Nessun risultato del modello va letto senza questi accanto. Un R^2, un MAE o
un Brier score non dicono nulla finche' non si sa cosa ottiene la media
semplice sullo stesso identico sottoinsieme di partite.

Tutti i baseline sono stimati **solo sul passato**, esattamente come il
modello: un baseline che vede il futuro sarebbe un avversario ingiustamente
forte e renderebbe il confronto inutile in senso opposto.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


#: La colonna bersaglio di default. Vale `sot` perche' e' cio' che le Fasi 1-6
#: hanno pubblicato; il parametro esiste per il blocco E3, che applica gli stessi
#: baseline ai **gol**. Un baseline che cambiasse bersaglio in silenzio sarebbe il
#: modo piu' rapido di rendere due tabelle non confrontabili.
TARGET = "sot"


def league_mean(train: pd.DataFrame, test: pd.DataFrame,
                target: str = TARGET) -> np.ndarray:
    """Media di campionato: un solo numero per tutti."""
    return np.full(len(test), train[target].mean())


def home_away_mean(train: pd.DataFrame, test: pd.DataFrame,
                   target: str = TARGET) -> np.ndarray:
    """Media distinta per casa e trasferta. Cattura il vantaggio del campo."""
    m = train.groupby("is_home")[target].mean()
    overall = train[target].mean()
    return test["is_home"].map(m).fillna(overall).to_numpy()


def team_mean(train: pd.DataFrame, test: pd.DataFrame,
              target: str = TARGET) -> np.ndarray:
    """Media storica della squadra. Ignora l'avversario e il campo.

    E' il baseline serio: gran parte della prevedibilita' dei tiri in porta e'
    semplicemente "questa squadra tira tanto".
    """
    m = train.groupby("team")[target].mean()
    overall = train[target].mean()
    return test["team"].map(m).fillna(overall).to_numpy()


def team_home_mean(train: pd.DataFrame, test: pd.DataFrame,
                   target: str = TARGET) -> np.ndarray:
    """Media della squadra corretta additivamente per casa/trasferta."""
    overall = train[target].mean()
    tm = train.groupby("team")[target].mean()
    ha = train.groupby("is_home")[target].mean() - overall
    return (test["team"].map(tm).fillna(overall)
            + test["is_home"].map(ha).fillna(0.0)).clip(lower=0.05).to_numpy()


BASELINES = {
    "media campionato": league_mean,
    "media casa/trasferta": home_away_mean,
    "media squadra": team_mean,
    "media squadra + campo": team_home_mean,
}
