"""Le metriche di validazione devono essere giuste **prima** di credere ai numeri.

Ogni test qui sotto verifica una proprieta' nota della metrica su dati in cui
la risposta e' calcolabile a mano o simulabile, non sulle stime del progetto.
Un test che confermasse i risultati di Fase 2 sarebbe circolare: se la metrica
e' sbagliata, sono sbagliati anche loro.
"""

import numpy as np
import pandas as pd
import pytest

from sot import config, dispersion as D, validate as V


@pytest.fixture(scope="module")
def rng():
    return np.random.default_rng(config.SEED)


# ------------------------------------------------------- pendenza di calibrazione
def test_pendenza_uno_su_dati_generati_dal_modello(rng):
    """Se i dati vengono davvero da Poisson(lambda), la pendenza deve dare 1."""
    lam = np.exp(rng.normal(1.4, 0.25, 20000))
    y = rng.poisson(lam)
    b, se = V.calibration_slope(y, lam)
    assert abs(b - 1.0) < 3 * se
    assert se < 0.05


def test_pendenza_sotto_uno_se_le_previsioni_sono_troppo_estreme(rng):
    """Lambda gonfiato attorno alla media: previsioni troppo estreme -> b < 1."""
    lam = np.exp(rng.normal(1.4, 0.25, 20000))
    y = rng.poisson(lam)
    lam_estremo = np.exp(np.log(lam.mean()) + 2.0 * (np.log(lam) - np.log(lam.mean())))
    b, se = V.calibration_slope(y, lam_estremo)
    assert b < 1.0 - 3 * se


def test_pendenza_sopra_uno_se_le_previsioni_sono_compresse(rng):
    lam = np.exp(rng.normal(1.4, 0.25, 20000))
    y = rng.poisson(lam)
    lam_compresso = np.exp(np.log(lam.mean()) + 0.5 * (np.log(lam) - np.log(lam.mean())))
    b, se = V.calibration_slope(y, lam_compresso)
    assert b > 1.0 + 3 * se


# ---------------------------------------------------------------- Brier e Murphy
def test_identita_di_murphy(rng):
    """Brier = affidabilita' - risoluzione + incertezza, a meno del binning."""
    lam = np.exp(rng.normal(1.4, 0.3, 5000))
    y = rng.poisson(lam)
    p = D.p_over(lam, config.OVER_LINE)
    d = V.brier_decomposition((y > config.OVER_LINE).astype(float), p)
    assert abs(d["residuo"]) < 0.005
    assert d["affidabilita"] >= 0 and d["risoluzione"] >= 0


def test_previsione_costante_ha_risoluzione_nulla(rng):
    """Un baseline che dice lo stesso numero a tutti non risolve nulla."""
    y = rng.poisson(4.0, 3000)
    p = np.full(len(y), float((y > config.OVER_LINE).mean()))
    d = V.brier_decomposition((y > config.OVER_LINE).astype(float), p)
    assert d["risoluzione"] < 1e-12
    assert d["n_fasce"] == 1
    assert abs(d["brier"] - d["incertezza"]) < 1e-9


def test_ece_nullo_su_previsioni_perfette(rng):
    """Con probabilita' vere e campione grande l'ECE deve andare a zero."""
    lam = np.exp(rng.normal(1.4, 0.3, 50000))
    y = rng.poisson(lam)
    p = D.p_over(lam, config.OVER_LINE)
    assert V.ece((y > config.OVER_LINE).astype(float), p) < 0.02


# ---------------------------------------------------------------------- PIT
def test_pit_uniforme_se_la_predittiva_e_giusta(rng):
    """Il PIT randomizzato e' uniforme solo se **tutta** la predittiva e' giusta."""
    lam = np.exp(rng.normal(1.4, 0.3, 8000))
    y = rng.poisson(lam)
    u = V.pit(y, lam, None)
    assert V.pit_uniformity(u)["p_value"] > 0.01
    assert abs(u.mean() - 0.5) < 0.02


def test_pit_rileva_una_predittiva_troppo_stretta(rng):
    """Dati sovradispersi contro una predittiva Poisson: PIT a U, test rifiuta.

    E' il caso che la pendenza di calibrazione **non** vede: la media resta
    giusta, e' la forma a essere sbagliata.
    """
    lam = np.exp(rng.normal(1.4, 0.3, 8000))
    r_vero = 3.0
    y = rng.negative_binomial(r_vero, r_vero / (r_vero + lam))

    b, se = V.calibration_slope(y, lam)
    assert abs(b - 1.0) < 3 * se, "la media deve restare calibrata"

    res = V.pit_uniformity(V.pit(y, lam, None))
    assert res["p_value"] < 1e-6
    assert res["counts"][0] + res["counts"][-1] > 2.5 * res["expected"]


def test_pit_torna_uniforme_con_la_dispersione_giusta(rng):
    lam = np.exp(rng.normal(1.4, 0.3, 8000))
    r_vero = 3.0
    y = rng.negative_binomial(r_vero, r_vero / (r_vero + lam))
    assert V.pit_uniformity(V.pit(y, lam, r_vero))["p_value"] > 0.01


# ------------------------------------------------------------------ copertura
def test_copertura_almeno_nominale_su_conteggi(rng):
    """Su conteggi la copertura e' conservativa, mai sotto il nominale."""
    lam = np.exp(rng.normal(1.4, 0.3, 20000))
    y = rng.poisson(lam)
    cov = V.interval_coverage(y, lam, None)
    assert (cov["copertura"] >= cov["livello"] - 0.01).all()
    assert cov["ampiezza_media"].is_monotonic_increasing


# -------------------------------------------------- niente stime che vedono avanti
def _dates(n, n_giorni=40):
    giorni = pd.date_range("2025-08-23", periods=n_giorni, freq="7D")
    return pd.Series(np.repeat(giorni, int(np.ceil(n / n_giorni)))[:n])


def _sovradisperso(rng, n):
    """Dati con r finito: su dati Poisson puri r satura a R_MAX e non si muove."""
    lam = np.exp(rng.normal(1.4, 0.3, n))
    y = rng.negative_binomial(4.0, 4.0 / (4.0 + lam)).astype(float)
    return lam, y


def test_r_walkforward_non_usa_il_presente_ne_il_passato(rng):
    """Alterare una data non deve toccare ne' la sua r ne' quelle precedenti.

    Il guasto si mette **a meta'** stagione: metterlo all'ultima data non
    proverebbe nulla, perche' dopo l'ultima non c'e' niente da influenzare.
    """
    n = 1200
    lam, y = _sovradisperso(rng, n)
    d = _dates(n)
    giorni = np.sort(d.unique())
    meta = giorni[len(giorni) // 2]

    r1 = V.walkforward_r(y, lam, d)
    y2 = y.copy()
    y2[(d == meta).to_numpy()] = 40.0
    assert not np.allclose(y, y2), "il guasto non e' stato applicato"
    r2 = V.walkforward_r(y2, lam, d)

    fino_a_meta = (d <= meta).to_numpy()
    dopo = (d > meta).to_numpy()
    assert np.allclose(r1[fino_a_meta], r2[fino_a_meta]), "ha guardato il presente"
    assert not np.allclose(r1[dopo], r2[dopo]), (
        "il guasto deve invece propagarsi alle date successive: se non lo fa, "
        "il test non sta misurando niente")


def test_r_walkforward_non_usa_il_futuro(rng):
    """Alterare la coda della stagione non deve toccare la r di inizio stagione."""
    n = 1200
    lam, y = _sovradisperso(rng, n)
    d = _dates(n)

    giorni = np.sort(d.unique())
    taglio = giorni[int(len(giorni) * 0.7)]

    r1 = V.walkforward_r(y, lam, d)
    y2 = y.copy()
    y2[(d > taglio).to_numpy()] = 40.0
    r2 = V.walkforward_r(y2, lam, d)

    presto = (d <= taglio).to_numpy()
    assert np.allclose(r1[presto], r2[presto])
    assert not np.allclose(r1, r2), "il guasto deve pur farsi sentire piu' avanti"


def test_tasso_base_walkforward_non_ricade_sul_campione_intero(rng):
    """La prima data non puo' conoscere la prevalenza dell'intera stagione."""
    n = 800
    y = rng.poisson(4.0, n).astype(float)
    d = _dates(n)
    base = V.walkforward_base_rate(y, d)

    prima = (d == d.min()).to_numpy()
    assert np.allclose(base[prima], 0.5), "senza passato serve il valore non informativo"

    ultima = (d == d.max()).to_numpy()
    atteso = float((y[~ultima] > config.OVER_LINE).mean())
    assert abs(base[ultima][0] - atteso) < 1e-12


def test_r_walkforward_resta_poisson_finche_il_passato_e_corto(rng):
    n = 200
    lam, y = _sovradisperso(rng, n)
    d = _dates(n, n_giorni=40)
    r = V.walkforward_r(y, lam, d)
    conteggi = pd.Series(r).groupby(d.to_numpy()).first()
    assert conteggi.iloc[0] == D.R_MAX
    assert (conteggi < D.R_MAX).any(), "prima o poi la stima deve partire"


# ------------------------------------------------------------------ confronti
def test_confronto_su_righe_identiche(rng):
    """`compare_models` deve valutare tutti i modelli sullo stesso campione."""
    lam = np.exp(rng.normal(1.4, 0.3, 2000))
    y = rng.poisson(lam)
    preds = {"buono": lam, "costante": np.full(len(y), lam.mean())}
    tab, cmp_ = V.compare_models(y, preds, r=None)

    assert (tab["n"] == len(y)).all()
    assert tab.loc["buono", "mae"] < tab.loc["costante", "mae"]
    assert tab.loc["costante", "sharpness"] == pytest.approx(0.0, abs=1e-12)
    assert cmp_.loc[0, "t_loglik"] > 2 and cmp_.loc[0, "t_mae"] > 2


def test_previsione_costante_non_ha_pendenza_ne_correlazione(rng):
    """Su lambda costante pendenza e correlazione non sono definite: `nan`.

    Meglio `nan` che un numero uscito da una matrice singolare, che verrebbe
    letto come se significasse qualcosa.
    """
    y = rng.poisson(4.0, 1000)
    cost = np.full(len(y), 4.0)
    b, se = V.calibration_slope(y, cost)
    assert np.isnan(b) and np.isnan(se)
    assert np.isnan(V.metrics(y, cost)["corr"])


def test_dispersione_per_modello_non_e_condivisa(rng):
    """Ogni modello deve poter usare la propria r: e' un parametro suo."""
    lam = np.exp(rng.normal(1.4, 0.3, 2000))
    y = rng.poisson(lam)
    cost = np.full(len(y), float(lam.mean()))
    r_map = {"buono": D.fit_r(y, lam), "costante": D.fit_r(y, cost)}
    assert r_map["costante"] < r_map["buono"], (
        "il modello costante deve apparire piu' sovradisperso: la variazione di "
        "lambda che non modella gli si accumula nella dispersione")

    tab, _ = V.compare_models(y, {"buono": lam, "costante": cost}, r=r_map)
    assert tab.loc["costante", "brier"] > tab.loc["buono", "brier"]


def test_segmenti_conservano_l_ordine_delle_categorie(rng):
    lam = np.exp(rng.normal(1.4, 0.3, 900))
    y = rng.poisson(lam)
    seg = pd.qcut(pd.Series(lam), 3, labels=["basso", "medio", "alto"])
    tab = V.metrics_by_segment(y, lam, seg)
    assert list(tab.index) == ["basso", "medio", "alto"]
    assert tab["n"].sum() == len(y)


def test_metriche_per_segmento_coincidono_col_calcolo_diretto(rng):
    lam = np.exp(rng.normal(1.4, 0.3, 900))
    y = rng.poisson(lam)
    seg = pd.Series(np.where(np.arange(len(y)) % 2 == 0, "pari", "dispari"))
    tab = V.metrics_by_segment(y, lam, seg)
    i = (np.arange(len(y)) % 2 == 0)
    assert tab.loc["pari", "mae"] == pytest.approx(np.mean(np.abs(y[i] - lam[i])))


# --------------------------------------------------- coerenza con la distribuzione
def test_cdf_e_p_over_sono_complementari(rng):
    lam = np.exp(rng.normal(1.4, 0.3, 500))
    for r in (None, 8.0):
        p = D.p_over(lam, config.OVER_LINE, r)
        f = D.cdf(np.full(len(lam), np.floor(config.OVER_LINE)), lam, r)
        assert np.allclose(p, 1.0 - f)


def test_dispersione_vettoriale_coincide_con_quella_scalare(rng):
    """`r` per riga deve dare, se costante, lo stesso risultato dello scalare."""
    lam = np.exp(rng.normal(1.4, 0.3, 500))
    r_vec = np.full(len(lam), 12.0)
    assert np.allclose(D.p_over(lam, config.OVER_LINE, 12.0),
                       D.p_over(lam, config.OVER_LINE, r_vec))
    assert np.allclose(D.ppf(0.9, lam, 12.0), D.ppf(0.9, lam, r_vec))
