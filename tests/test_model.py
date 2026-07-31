"""Comportamento del modello di squadra, dei baseline e della NB2."""

import numpy as np
import pandas as pd
import pytest

from sot import baselines as bl, dispersion as D, model_team as MT, walkforward as wf


@pytest.fixture(scope="module")
def fitted(team_match):
    df = wf.build_predictors(team_match)
    return df, MT.TeamModel(alpha=12.0).fit(df)


def test_lambda_positivi_e_plausibili(fitted):
    df, m = fitted
    lam = m.predict(df)
    assert (lam > 0).all()
    assert lam.max() < 20


def test_lambda_medio_vicino_alla_media_osservata(fitted):
    df, m = fitted
    assert abs(m.predict(df).mean() - df["sot"].mean()) < 0.15


def test_vantaggio_del_campo_positivo(fitted):
    """Le squadre di casa tirano piu' in porta: 4.43 contro 3.63."""
    _, m = fitted
    assert 0.05 < m.home_advantage < 0.5


def test_ridge_piu_forte_comprime_i_rating(team_match):
    df = wf.build_predictors(team_match)
    weak = MT.TeamModel(alpha=1.0).fit(df).ratings()
    strong = MT.TeamModel(alpha=50.0).fit(df).ratings()
    assert strong["attack"].std() < weak["attack"].std()


def test_ordinamento_attacco_coerente_coi_dati(fitted):
    """Le squadre con piu' tiri in porta devono avere attacco piu' alto."""
    df, m = fitted
    r = m.ratings().set_index("team")["attack"]
    obs = df.groupby("team")["sot"].mean()
    assert np.corrcoef(r.loc[obs.index], obs)[0, 1] > 0.9


def test_baseline_stimati_solo_sul_passato(team_match):
    df = wf.build_predictors(team_match)
    for _, train, test in wf.date_splits(df):
        for fn in bl.BASELINES.values():
            out = fn(train, test)
            assert len(out) == len(test)
            assert np.isfinite(out).all()
        break


def test_nb2_degenera_nella_poisson_per_r_grande():
    y = np.array([0, 1, 2, 3, 4, 5], dtype=float)
    lam = np.full(6, 4.0)
    from scipy.stats import poisson
    got = D.nb2_loglik(y, lam, 1e6)
    assert np.allclose(got, poisson.logpmf(y, lam), atol=1e-4)


def test_fit_r_recupera_il_vero_parametro():
    rng = np.random.default_rng(0)
    lam = rng.uniform(2, 7, 20000)
    r_true = 25.0
    y = rng.negative_binomial(r_true, r_true / (r_true + lam)).astype(float)
    assert abs(D.fit_r(y, lam) - r_true) / r_true < 0.25


def test_p_over_coerente_con_la_distribuzione():
    lam = np.array([4.0])
    from scipy.stats import poisson
    assert abs(D.p_over(lam, 4.5, None)[0] - poisson.sf(4, 4.0)) < 1e-12
    # Con sovradispersione la coda destra e' piu' pesante.
    assert D.p_over(lam, 7.5, 20.0)[0] > D.p_over(lam, 7.5, None)[0]


def test_calibration_slope_uno_su_dati_ben_calibrati():
    from sot.validate import calibration_slope
    rng = np.random.default_rng(1)
    lam = rng.uniform(1, 8, 5000)
    y = rng.poisson(lam).astype(float)
    slope, se = calibration_slope(y, lam)
    assert abs(slope - 1.0) < 3 * se
