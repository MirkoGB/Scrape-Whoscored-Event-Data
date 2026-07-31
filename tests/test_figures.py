# -*- coding: utf-8 -*-
"""Le figure devono dire quello che dice il testo.

Non si testa l'estetica. Si testa che ogni figura si costruisca, che ogni
elemento che il README cita esista davvero, e soprattutto che l'**enfasi** vada
sull'elemento giusto: una figura che evidenzia la squadra sbagliata o che
colora i nuovi arrivi come i confermati e' peggio di nessuna figura, perche'
sembra corretta.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import figures as F, model_player as MP

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def calib():
    return pd.DataFrame(
        {"calib_slope": [0.965, 0.955, 0.785, 0.747, np.nan],
         "calib_se": [0.083, 0.197, 0.075, 0.080, np.nan],
         "calib_z_vs_1": [-0.42, -0.23, -2.86, -3.15, np.nan]},
        index=["modello", "media casa/trasferta", "media squadra + campo",
               "media squadra", "media campionato"])


@pytest.fixture
def rel():
    return pd.DataFrame({"p_mean": [0.15, 0.35, 0.55, 0.75],
                         "freq": [0.18, 0.32, 0.57, 0.80],
                         "se": [0.04, 0.04, 0.05, 0.09],
                         "n": [72, 150, 95, 20]})


def _colori_barre(ax):
    return [p.get_facecolor() for p in ax.patches]


# --------------------------------------------------------------- costruzione
def test_ogni_figura_si_costruisce(calib, rel):
    """Nessuna deve sollevare, e tutte devono avere un titolo."""
    cand = pd.DataFrame({"predittore": [f"p{i}" for i in range(8)],
                         "t": np.linspace(-1.2, 1.4, 8)})
    cmp_ = pd.DataFrame({"vs": ["a", "b"], "d_mae": [0.14, 0.045],
                         "t_mae": [4.1, 1.95], "se_mae": [0.034, 0.023]})
    rat = pd.DataFrame({"team": list("ABCDE"), "neutro": [5.0, 4.3, 3.9, 3.2, 2.6]})
    proj = pd.DataFrame({"name": [f"g{i}" for i in range(6)],
                         "is_new": [False] * 4 + [True] * 2,
                         "contributo": [1.0, 0.7, 0.4, 0.2, 0.12, 0.1]})
    sim = np.random.default_rng(0).normal(190, 30, 5000)

    figg = [
        F.calibrazione_pendenza(calib, "modello"),
        F.affidabilita(rel, rel, "modello", "baseline", 4.5),
        F.predittori_scartati(cand, soglia=2.0),
        F.vantaggio_sui_baseline(cmp_, {"a": 0.034, "b": 0.023}),
        F.ratings_squadra(rat, evidenzia="B"),
        F.proiezione_como(sim, 150, 190, 240, 186, (152, 222)),
        F.contributo_giocatori(proj, top=6),
    ]
    for fig in figg:
        # I titoli sono allineati a sinistra: `get_title()` senza `loc`
        # leggerebbe quello centrato, che e' vuoto.
        assert fig.axes and fig.axes[0].get_title(loc="left").strip()
        import matplotlib.pyplot as plt
        plt.close(fig)


# ------------------------------------------------------------------- enfasi
def test_la_pendenza_evidenzia_il_modello(calib):
    fig = F.calibrazione_pendenza(calib, "modello")
    ax = fig.axes[0]
    etichette = [t.get_text() for t in ax.get_yticklabels()]
    assert etichette[-1] == "modello", "il modello deve stare in cima"
    colori = {l.get_color() for l in ax.lines}
    assert F.SERIE_1 in colori and F.DEEMPH in colori


def test_la_pendenza_esclude_cio_che_non_e_identificato(calib):
    """La riga esclusa sparisce, e l'asse si stringe di conseguenza."""
    piena = F.calibrazione_pendenza(calib, "modello")
    ridotta = F.calibrazione_pendenza(calib, "modello",
                                      escludi=("media casa/trasferta",))
    assert len(piena.axes[0].get_yticklabels()) == 4      # la nan e' gia' fuori
    assert len(ridotta.axes[0].get_yticklabels()) == 3
    assert "media casa/trasferta" not in [
        t.get_text() for t in ridotta.axes[0].get_yticklabels()]
    assert any("escluso" in t.get_text() for t in ridotta.axes[0].texts), (
        "l'esclusione va dichiarata nel sottotitolo, non fatta di nascosto")


def test_i_ratings_evidenziano_la_squadra_richiesta():
    rat = pd.DataFrame({"team": list("ABCDE"), "neutro": [5.0, 4.3, 3.9, 3.2, 2.6]})
    ax = F.ratings_squadra(rat, evidenzia="C").axes[0]
    etichette = [t.get_text() for t in ax.get_yticklabels()]
    i = etichette.index("C")
    colori = _colori_barre(ax)
    from matplotlib.colors import to_rgba
    assert colori[i] == to_rgba(F.SERIE_1)
    assert all(c == to_rgba(F.DEEMPH) for j, c in enumerate(colori) if j != i)


def test_i_nuovi_arrivi_hanno_un_colore_proprio():
    """Chi non ha dati non deve sembrare uguale a chi ne ha."""
    proj = pd.DataFrame({"name": list("abcd"), "is_new": [False, True, False, True],
                         "contributo": [1.0, 0.5, 0.3, 0.2]})
    ax = F.contributo_giocatori(proj, top=4).axes[0]
    from matplotlib.colors import to_rgba
    etichette = [t.get_text() for t in ax.get_yticklabels()]
    colori = dict(zip(etichette, _colori_barre(ax)))
    assert colori["b"] == to_rgba(F.SERIE_2) and colori["d"] == to_rgba(F.SERIE_2)
    assert colori["a"] == to_rgba(F.SERIE_1) and colori["c"] == to_rgba(F.SERIE_1)


def test_il_vantaggio_segnala_gli_intervalli_che_toccano_lo_zero():
    """Il colore deve dipendere dall'intervallo, non dalla posizione in lista."""
    cmp_ = pd.DataFrame({"vs": ["netto", "incerto"], "d_mae": [0.14, 0.045],
                         "t_mae": [4.1, 1.95], "se_mae": [0.034, 0.030]})
    ax = F.vantaggio_sui_baseline(cmp_, dict(zip(cmp_["vs"], cmp_["se_mae"]))).axes[0]
    colori = [l.get_color() for l in ax.lines]
    assert F.SERIE_2 in colori, "l'intervallo che tocca lo zero va segnalato"
    assert F.SERIE_1 in colori, "quello che non lo tocca no"


# --------------------------------------------------- niente numeri a mano
def test_nessuna_griglia_di_tau_fuori_dal_modulo_del_modello():
    """`tau` va scelto su **una** griglia sola.

    Il difetto che questo test blocca e' gia' successo: `run_phase3.py`
    passava la propria griglia a `select_tau`, diversa da `MP.TAU_GRID`, e le
    Fasi 3 e 5 sceglievano due tau diversi sugli stessi dati.
    """
    for f in (ROOT / "scripts").glob("*.py"):
        testo = f.read_text(encoding="utf-8")
        assert not re.search(r"select_tau\([^)]*taus\s*=", testo), (
            f"{f.name} passa una griglia di tau propria: usare MP.TAU_GRID")


def test_la_griglia_di_tau_non_e_un_bordo():
    """Il minimo della griglia deve stare sotto l'ottimo, non coinciderci.

    Se la validazione incrociata sceglie l'estremo della griglia, non ha
    scelto: ha esaurito le opzioni. Il valore selezionato sui dati veri e' 3.0.
    """
    assert min(MP.TAU_GRID) < 3.0 < max(MP.TAU_GRID)
    assert list(MP.TAU_GRID) == sorted(MP.TAU_GRID)
