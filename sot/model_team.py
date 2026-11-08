"""Modello within-season dei tiri in porta per squadra-partita.

    log(lambda_ij) = mu + attacco_i + difesa_j + gamma * casa  [+ beta' z_ij]

Stima: Poisson con penalizzazione ridge su attacco e difesa e pesi a
decadimento esponenziale (emivita 150 giorni).

Scelte, e perche':

* La ridge penalizza **solo** attacco e difesa. Senza penalita' i due blocchi
  di dummy non sono identificabili separatamente da `mu` (si puo' aggiungere
  una costante a tutti gli attacchi e toglierla da mu); la penalita' risolve
  l'indeterminatezza tirando entrambi verso zero, che e' anche la regolazione
  che serve con 38 partite per squadra.
* `mu`, `gamma` e i coefficienti dei predittori aggiuntivi restano non
  penalizzati: sono pochi e gia' standardizzati.
* I pesi sono ricalcolati a ogni stima rispetto alla data di previsione, non
  una volta per tutte: in walk-forward la stessa partita ha eta' diverse a
  giornate diverse.
* La standardizzazione dei predittori usa media e deviazione **del solo
  training**. Usare quelle dell'intero campione farebbe rientrare informazione
  dal futuro attraverso la scala.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import config


@dataclass
class TeamModel:
    """Poisson ridge con effetti attacco/difesa e vantaggio del campo."""

    alpha: float = 6.0
    half_life: float = config.HALF_LIFE_DAYS
    extra: tuple[str, ...] = ()

    #: La colonna bersaglio. Il default e' `sot` e **non va cambiato qui**: tutto
    #: cio' che le Fasi 1-6 hanno pubblicato lo assume, e un test verifica che la
    #: previsione con il default sia identica bit per bit a quella di prima che il
    #: parametro esistesse. Lo usa il blocco E3 con `gol_fatti`, dove la stessa
    #: specificazione va **rivalidata per conto suo**: che il modello sia calibrato
    #: sui tiri in porta non dice niente sui gol, ed ereditare quella validazione
    #: sarebbe leggere male il vincolo 7.
    target: str = "sot"

    #: Se `True`, una squadra che non sta in `teams_` **solleva** invece di
    #: scivolare a coefficiente zero. Il default e' `False` e **non va cambiato**:
    #: dentro il walk-forward il coefficiente zero e' il comportamento *giusto*
    #: (una squadra alla sua prima apparizione in un training parziale), e
    #: sollevare romperebbe la Fase 2, E3 e R0-R3. Un test verifica che con
    #: `False` le previsioni siano identiche bit per bit a prima che il parametro
    #: esistesse.
    #:
    #: Serve al ponte della Fase 12 / V4, dove il difetto e' reale e silenzioso:
    #: `df["team"].map(idx)` da' `NaN`, la maschera salta la riga e la dummy resta
    #: a zero, cioe' la squadra viene trattata **come esattamente media** senza
    #: errore ne' avviso. Il caso vero non e' la squadra inventata: e' chiedere
    #: Como-Cremonese nel 2023-24, dove la Cremonese non c'era.
    strict_teams: bool = False

    #: Fase 14 / A2 — il **centro della penalita'**, cioe' verso cosa la ridge
    #: tira attacco e difesa. `None` (il default, che **non va cambiato**) vuol
    #: dire "verso zero", che e' la media di campionato: e' cio' che questo
    #: modello ha sempre fatto, e un test verifica l'identita' bit per bit.
    #:
    #: Un dizionario `{squadra: (attacco, difesa)}` sposta quel centro sui
    #: coefficienti della **stagione precedente**. Serve alle prime giornate di
    #: una stagione nuova, dove la forma within-season non ha niente su cui
    #: stimare: a zero partite giocate la penalita' e' l'unico termine con
    #: informazione dentro, e il fit restituisce il prior.
    #:
    #: **Il prior si scioglie da solo**, e non c'e' nessun decadimento da
    #: sintonizzare: la verosimiglianza cresce con `n` mentre la penalita' resta
    #: fissa, quindi il peso relativo del prior cala partita dopo partita.
    #:
    #: **Porta la forza RELATIVA, non il livello.** `mu` e `gamma` non sono
    #: penalizzati, quindi il livello della stagione nuova lo imparano i dati
    #: nuovi. E' cio' che evita il problema gia' misurato in E4 sui cinque fit di
    #: xG — forma stabile, livello che si muove del 15,8% — e in V0 sui
    #: tentativi, dove il livello si muove del 5,5% fra le cinque stagioni.
    #:
    #: Una squadra **assente** dal dizionario riceve centro zero, cioe' viene
    #: tirata verso la media di campionato. E' l'unico default onesto per una
    #: neopromossa, ed e' il motivo per cui il prior va **centrato** prima di
    #: entrare (vedi `prior_stagione.centra`): se la media dei coefficienti noti
    #: non fosse zero, lo zero delle neopromosse non sarebbe la media di
    #: campionato ma un punto arbitrario accanto.
    prior: dict | None = None

    #: La forza della penalita' **quando c'e' un prior**. `None` = si riusa
    #: `alpha`. E' un parametro separato perche' le due penalita' non chiedono la
    #: stessa cosa: tirare verso la media di campionato e tirare verso «com'era
    #: l'anno scorso» sono due affermazioni di forza diversa, e imporre lo stesso
    #: numero sarebbe una scelta non dichiarata. Si sceglie in walk-forward sulle
    #: sole transizioni storiche (`prior_stagione.scegli_alpha_prior`).
    alpha_prior: float | None = None

    teams_: list = field(default_factory=list, init=False)
    beta_: np.ndarray = field(default=None, init=False)
    mu_: float = field(default=None, init=False)
    center_: np.ndarray = field(default=None, init=False)
    scale_: np.ndarray = field(default=None, init=False)

    # ---------------------------------------------------------------- design
    def _design(self, df: pd.DataFrame) -> np.ndarray:
        n = len(df)
        n_t = len(self.teams_)
        idx = {t: i for i, t in enumerate(self.teams_)}

        X = np.zeros((n, 1 + 2 * n_t + 1 + len(self.extra)))
        X[:, 0] = 1.0

        ai = df["team"].map(idx).to_numpy()
        di = df["opponent"].map(idx).to_numpy()
        rows = np.arange(n)
        ok_a = ~pd.isna(ai)
        ok_d = ~pd.isna(di)

        if self.strict_teams and not (ok_a.all() and ok_d.all()):
            ignote = sorted(set(df.loc[~ok_a, "team"]) | set(df.loc[~ok_d, "opponent"]))
            raise ValueError(
                f"squadre sconosciute al modello: {ignote}. "
                f"Note: {sorted(self.teams_)}. "
                "Senza `strict_teams` la loro dummy resta a zero, cioe' "
                "verrebbero trattate come esattamente medie senza alcun avviso.")

        X[rows[ok_a], 1 + ai[ok_a].astype(int)] = 1.0
        X[rows[ok_d], 1 + n_t + di[ok_d].astype(int)] = 1.0

        X[:, 1 + 2 * n_t] = df["is_home"].to_numpy()

        if self.extra:
            Z = df[list(self.extra)].to_numpy(dtype=float)
            Z = (Z - self.center_) / self.scale_
            X[:, 2 + 2 * n_t:] = np.nan_to_num(Z, nan=0.0)

        return X

    def _penalty_mask(self) -> np.ndarray:
        n_t = len(self.teams_)
        p = np.zeros(1 + 2 * n_t + 1 + len(self.extra))
        p[1:1 + 2 * n_t] = 1.0
        return p

    def _penalty_center(self) -> np.ndarray:
        """Verso dove tira la ridge. Zero ovunque, tranne dove c'e' un prior.

        Il vettore ha la forma di `beta_`, cosi' la penalita' resta la stessa
        espressione con un centro spostato invece di un ramo di codice in piu':
        `alpha * sum(pen * (b - centro)**2)`. Con `prior=None` il centro e' zero
        e l'espressione e' **letteralmente** quella di prima.
        """
        n_t = len(self.teams_)
        c = np.zeros(1 + 2 * n_t + 1 + len(self.extra))
        if not self.prior:
            return c
        for i, t in enumerate(self.teams_):
            v = self.prior.get(t)
            if v is None:
                continue                    # neopromossa: centro zero = media
            att, dif = v
            c[1 + i] = float(att)
            c[1 + n_t + i] = float(dif)
        return c

    def _weights(self, df: pd.DataFrame, as_of: pd.Timestamp) -> np.ndarray:
        age = (as_of - df["date"]).dt.total_seconds().to_numpy() / 86400.0
        return 0.5 ** (np.clip(age, 0.0, None) / self.half_life)

    # ------------------------------------------------------------------- fit
    def fit(self, df: pd.DataFrame, as_of: pd.Timestamp | None = None,
            teams: list | None = None) -> "TeamModel":
        self.teams_ = list(teams) if teams is not None else sorted(
            set(df["team"]) | set(df["opponent"]))

        if self.extra:
            Z = df[list(self.extra)].to_numpy(dtype=float)
            self.center_ = np.nanmean(Z, axis=0)
            sd = np.nanstd(Z, axis=0)
            self.scale_ = np.where(sd > 1e-12, sd, 1.0)

        if as_of is None:
            as_of = df["date"].max()

        X = self._design(df)
        y = df[self.target].to_numpy(dtype=float)
        w = self._weights(df, as_of)
        pen = self._penalty_mask()
        centro = self._penalty_center()
        a = self.alpha if self.prior is None else (
            self.alpha if self.alpha_prior is None else self.alpha_prior)

        def obj(b):
            eta = np.clip(X @ b, -20, 20)
            lam = np.exp(eta)
            nll = np.sum(w * (lam - y * eta))
            grad = X.T @ (w * (lam - y))
            d = b - centro
            reg = a * np.sum(pen * d ** 2)
            greg = 2.0 * a * pen * d
            return nll + reg, grad + greg

        # Si parte dal centro della penalita': con `prior=None` e' il vettore
        # nullo, cioe' esattamente il punto di partenza di prima. Con un prior e'
        # la stagione scorsa, che e' anche la risposta giusta quando le partite
        # nuove sono zero o quasi.
        b0 = centro.copy()
        b0[0] = np.log(max(y.mean(), 0.1))
        res = minimize(obj, b0, jac=True, method="L-BFGS-B",
                       options={"maxiter": 500, "ftol": 1e-12})
        self.beta_ = res.x
        self.mu_ = res.x[0]
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        eta = np.clip(self._design(df) @ self.beta_, -20, 20)
        return np.exp(eta)

    # ---------------------------------------------------------------- ratings
    def ratings(self) -> pd.DataFrame:
        n_t = len(self.teams_)
        return pd.DataFrame({
            "team": self.teams_,
            "attack": self.beta_[1:1 + n_t],
            "defence": self.beta_[1 + n_t:1 + 2 * n_t],
        }).sort_values("attack", ascending=False).reset_index(drop=True)

    @property
    def home_advantage(self) -> float:
        return float(self.beta_[1 + 2 * len(self.teams_)])

    @property
    def extra_coefs(self) -> dict[str, float]:
        n_t = len(self.teams_)
        return dict(zip(self.extra, self.beta_[2 + 2 * n_t:]))


def poisson_loglik(y: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """Log-verosimiglianza Poisson per osservazione, termine costante incluso."""
    from scipy.special import gammaln
    lam = np.clip(lam, 1e-9, None)
    return y * np.log(lam) - lam - gammaln(y + 1.0)
