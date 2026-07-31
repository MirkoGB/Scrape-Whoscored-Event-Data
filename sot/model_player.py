"""Tassi di tiro in porta per giocatore, separati dal contesto di squadra.

    log(lambda_pm) = log(minuti/90)                     <- esposizione
                   + [ mu + attacco_squadra + difesa_avversario + gamma*casa ]
                   + ruolo_p + v_p

Il blocco fra parentesi e' il **contesto**, preso come offset fisso dal modello
di squadra della Fase 2. E' la parte che separa il giocatore dalla squadra: un
attaccante in una squadra dominante tira di piu' perche' la sua squadra
produce piu' tiri, non perche' sia migliore. Senza questo termine si
sovrastima chi si trasferisce verso l'alto e si sottostima il contrario.

IDENTIFICABILITA'
-----------------
`v_p` e `attacco_squadra` sono collineari: si puo' aggiungere una costante a
tutti i giocatori di una squadra e toglierla dal suo attacco. Il vincolo qui
non e' imposto a mano ma **ereditato**: l'attacco di squadra arriva gia'
normalizzato dal modello di Fase 2, dove la penalizzazione ridge lo tira verso
lo zero, cioe' verso la media di campionato. `v_p` misura quindi quanto un
giocatore tira in porta rispetto al suo ruolo, **in una squadra di forza
media contro una difesa media**. E' questa la quantita' portabile fra club.

SHRINKAGE
---------
`v_p` e' penalizzato verso zero (cioe' verso la media del proprio ruolo) con
intensita' `tau`, scelta per validazione incrociata raggruppata per partita.
Con una sola stagione i minuti individuali sono pochi e lo shrinkage non e'
opzionale: senza, il miglior tasso della stagione risulterebbe 6.92 SoT/90 su
26 minuti giocati.

PORTIERI
--------
Esclusi dal modello. Non tirano mai (0 tiri in porta su 72.176 minuti in tutta
la stagione), quindi il loro effetto di ruolo divergerebbe a meno infinito.
Nella ricomposizione contribuiscono esattamente zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.model_selection import GroupKFold

from . import config, model_team

ROLES = ("DEF", "MID", "FWD")

# Griglia di tau. Il minimo deve stare **sotto** l'ottimo, altrimenti la scelta
# e' un artefatto del bordo e non una scelta: la griglia precedente partiva da
# 2.0 e la validazione incrociata sceglieva 2.0, cioe' il suo estremo. Con la
# griglia attuale l'ottimo e' 3.0, che e' interno, e la scelta significa
# qualcosa. La griglia era anche duplicata in `scripts/run_phase3.py`, con
# valori diversi: due fasi sceglievano due tau. Ora c'e' solo questa.
TAU_GRID = (0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 15.0)


def with_context(player_match: pd.DataFrame, team_match: pd.DataFrame,
                 alpha: float = 12.0) -> pd.DataFrame:
    """Aggiunge a ogni riga giocatore-partita l'offset di contesto di squadra."""
    tm = team_match.copy()
    m = model_team.TeamModel(alpha=alpha).fit(tm)
    tm["context"] = np.log(m.predict(tm))

    out = player_match.merge(tm[["matchId", "teamId", "context"]],
                             on=["matchId", "teamId"], how="left")
    return out


def usable(df: pd.DataFrame) -> pd.Series:
    """Righe con esposizione e ruolo modellabile."""
    return (df["minutes"] > 0) & (df["role"].isin(ROLES))


@dataclass
class PlayerModel:
    """Poisson gerarchico con shrinkage verso la media di ruolo."""

    tau: float = 20.0

    players_: list = field(default_factory=list, init=False)
    beta_: np.ndarray = field(default=None, init=False)

    def _design(self, df: pd.DataFrame):
        idx = {p: i for i, p in enumerate(self.players_)}
        n_r, n_p = len(ROLES), len(self.players_)

        X = np.zeros((len(df), n_r + n_p))
        ri = df["role"].map({r: i for i, r in enumerate(ROLES)}).to_numpy()
        X[np.arange(len(df)), ri.astype(int)] = 1.0

        pi = df["playerId"].map(idx).to_numpy()
        known = ~pd.isna(pi)
        X[np.arange(len(df))[known], n_r + pi[known].astype(int)] = 1.0

        offset = df["context"].to_numpy() + np.log(df["minutes"].to_numpy() / 90.0)
        return X, offset

    def fit(self, df: pd.DataFrame, players: list | None = None) -> "PlayerModel":
        self.players_ = list(players) if players is not None else sorted(
            df["playerId"].unique())
        X, offset = self._design(df)
        y = df["sot"].to_numpy(dtype=float)

        pen = np.zeros(X.shape[1])
        pen[len(ROLES):] = 1.0

        def obj(b):
            eta = np.clip(X @ b + offset, -25, 25)
            lam = np.exp(eta)
            nll = np.sum(lam - y * eta)
            grad = X.T @ (lam - y)
            return (nll + self.tau * np.sum(pen * b ** 2),
                    grad + 2.0 * self.tau * pen * b)

        b0 = np.zeros(X.shape[1])
        b0[:len(ROLES)] = np.log(max(y.sum() / max(len(y), 1), 1e-3))
        res = minimize(obj, b0, jac=True, method="L-BFGS-B",
                       options={"maxiter": 2000, "ftol": 1e-12})
        self.beta_ = res.x
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X, offset = self._design(df)
        return np.exp(np.clip(X @ self.beta_ + offset, -25, 25))

    # ------------------------------------------------------------------ output
    @property
    def role_effects(self) -> dict[str, float]:
        return dict(zip(ROLES, self.beta_[:len(ROLES)]))

    def player_effects(self) -> pd.DataFrame:
        return pd.DataFrame({"playerId": self.players_,
                             "v": self.beta_[len(ROLES):]})

    def share_per90(self, df_players: pd.DataFrame) -> np.ndarray:
        """Quota `exp(ruolo + v)`: quanto il giocatore preleva del lambda di squadra.

        Non e' un tasso leggibile: e' il coefficiente da moltiplicare per il
        contesto di squadra e per i minuti/90. Sommato sugli undici in campo
        di una squadra da' circa 1, cioe' ricompone il lambda di squadra.
        """
        eff = self.player_effects().set_index("playerId")["v"]
        role = pd.Series(self.role_effects)
        return np.exp(df_players["role"].map(role).to_numpy()
                      + df_players["playerId"].map(eff).fillna(0.0).to_numpy())

    def rate_per90(self, df_players: pd.DataFrame,
                   neutral_lambda: float = config.REF_LEAGUE_MEAN) -> np.ndarray:
        """Tiri in porta per 90 minuti in una squadra di forza **media**.

        Questa e' la quantita' leggibile e portabile fra club: quanti tiri in
        porta produrrebbe il giocatore ogni 90 minuti se giocasse in una
        squadra di attacco medio, contro una difesa media, a campo neutro.

        Differisce dal tasso grezzo proprio per la correzione di contesto: un
        giocatore di una squadra dominante ha un tasso di modello **inferiore**
        al proprio grezzo, ed e' esattamente cio' che serve per non
        sovrastimarlo quando cambia squadra.
        """
        return self.share_per90(df_players) * neutral_lambda


def select_tau(df: pd.DataFrame, taus=TAU_GRID, n_splits: int = 5,
               seed: int = config.SEED) -> pd.DataFrame:
    """Sceglie tau per validazione incrociata raggruppata per partita.

    Il raggruppamento per `matchId` evita che tiri della stessa partita
    finiscano di qua e di la' dello split.
    """
    from .dispersion import nb2_loglik, R_MAX

    d = df[usable(df)].reset_index(drop=True)
    groups = d["matchId"].to_numpy()
    players = sorted(d["playerId"].unique())

    rows = []
    gkf = GroupKFold(n_splits=n_splits)
    for tau in taus:
        ll = 0.0
        for tr, te in gkf.split(d, groups=groups):
            m = PlayerModel(tau=tau).fit(d.iloc[tr], players=players)
            lam = m.predict(d.iloc[te])
            ll += float(np.sum(nb2_loglik(d.iloc[te]["sot"].to_numpy(), lam, R_MAX)))
        rows.append({"tau": tau, "cv_loglik": ll})
    return pd.DataFrame(rows).sort_values("cv_loglik", ascending=False)
