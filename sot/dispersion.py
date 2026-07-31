"""Sovradispersione, misurata **condizionatamente a lambda**.

Il rapporto varianza/media calcolato sui dati grezzi vale circa 1.3, ma quel
numero non dice nulla sulla distribuzione condizionata: buona parte di quella
varianza e' la variazione sistematica di lambda fra squadre forti e deboli,
casa e trasferta, che il modello **spiega**. Quello che conta e' quanta
dispersione resta una volta fissato lambda.

Si stima quindi il parametro r della negativa binomiale NB2

    Var(y | lambda) = lambda + lambda^2 / r

tenendo lambda fisso ai valori previsti dal modello. r grande significa
comportamento quasi-Poisson. Sui tiri in porta ci si aspetta r attorno a 40.

Un r inferiore a 10 non va riportato come risultato: e' quasi sempre il
sintomo di un errore di specificazione (lambda sbagliati, leakage al
contrario, righe duplicate) e va indagato prima.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import gammaln
from scipy.stats import nbinom

R_MIN, R_MAX = 0.5, 5000.0
R_SUSPICIOUS = 10.0


def nb2_loglik(y: np.ndarray, lam: np.ndarray, r: float) -> np.ndarray:
    """Log-verosimiglianza NB2 per osservazione, a lambda dato."""
    lam = np.clip(lam, 1e-9, None)
    return (gammaln(y + r) - gammaln(r) - gammaln(y + 1.0)
            + r * np.log(r / (r + lam))
            + y * np.log(lam / (r + lam)))


def fit_r(y: np.ndarray, lam: np.ndarray) -> float:
    """Stima r per massima verosimiglianza, con lambda fissato."""
    def neg(log_r):
        return -np.sum(nb2_loglik(y, lam, float(np.exp(log_r))))

    res = minimize_scalar(neg, bounds=(np.log(R_MIN), np.log(R_MAX)),
                          method="bounded", options={"xatol": 1e-6})
    return float(np.exp(res.x))


def conditional_dispersion(y: np.ndarray, lam: np.ndarray) -> dict:
    """Diagnostica completa: dispersione grezza vs condizionata."""
    y = np.asarray(y, dtype=float)
    lam = np.asarray(lam, dtype=float)

    r = fit_r(y, lam)
    resid = (y - lam) / np.sqrt(np.clip(lam, 1e-9, None))
    pearson_chi2 = float(np.sum(resid ** 2))

    return {
        "raw_var_mean_ratio": float(y.var() / y.mean()),
        "nb2_r": r,
        "implied_var_at_mean": float(lam.mean() + lam.mean() ** 2 / r),
        "mean_lambda": float(lam.mean()),
        "pearson_dispersion": pearson_chi2 / len(y),
        "loglik_poisson": float(np.sum(nb2_loglik(y, lam, R_MAX))),
        "loglik_nb2": float(np.sum(nb2_loglik(y, lam, r))),
        "suspicious": bool(r < R_SUSPICIOUS),
        "n": int(len(y)),
    }


def p_over(lam: np.ndarray, line: float, r=None) -> np.ndarray:
    """P(y > line). Con `r = None` usa la Poisson.

    `r` puo' essere uno scalare oppure un vettore lungo quanto `lam`: serve per
    la validazione walk-forward, dove la dispersione usata per prevedere una
    partita e' stimata solo sulle partite precedenti e quindi cambia riga per
    riga.
    """
    k = int(np.floor(line))
    lam = np.clip(np.asarray(lam, dtype=float), 1e-9, None)
    if r is None:
        from scipy.stats import poisson
        return poisson.sf(k, lam)
    r = np.asarray(r, dtype=float)
    if np.all(r >= R_MAX * 0.99):
        from scipy.stats import poisson
        return poisson.sf(k, lam)
    return nbinom.sf(k, r, r / (r + lam))


def cdf(y: np.ndarray, lam: np.ndarray, r=None) -> np.ndarray:
    """F(y) della predittiva. Complemento di `p_over`, con la stessa firma."""
    y = np.asarray(y, dtype=float)
    lam = np.clip(np.asarray(lam, dtype=float), 1e-9, None)
    out = np.where(y < 0, 0.0, np.nan)
    ok = y >= 0
    if r is None:
        from scipy.stats import poisson
        out[ok] = poisson.cdf(y[ok], lam[ok])
        return out
    r = np.asarray(r, dtype=float)
    if np.all(r >= R_MAX * 0.99):
        from scipy.stats import poisson
        out[ok] = poisson.cdf(y[ok], lam[ok])
        return out
    rr = np.broadcast_to(r, lam.shape)
    out[ok] = nbinom.cdf(y[ok], rr[ok], rr[ok] / (rr[ok] + lam[ok]))
    return out


def ppf(q: float, lam: np.ndarray, r=None) -> np.ndarray:
    """Quantile della predittiva, per gli intervalli di previsione."""
    lam = np.clip(np.asarray(lam, dtype=float), 1e-9, None)
    if r is None:
        from scipy.stats import poisson
        return poisson.ppf(q, lam)
    r = np.asarray(r, dtype=float)
    if np.all(r >= R_MAX * 0.99):
        from scipy.stats import poisson
        return poisson.ppf(q, lam)
    rr = np.broadcast_to(r, lam.shape)
    return nbinom.ppf(q, rr, rr / (rr + lam))
