# -*- coding: utf-8 -*-
"""Fase 6D — il test dei predittori in un altro regime, e la sua potenza.

Il rischio di questo blocco e' uno solo, e non e' un bug di calcolo: leggere
un `t` sotto soglia su cento righe come se dicesse "il predittore non serve".
I test qui dentro bloccano le tre affermazioni da cui dipende quella lettura:

* la potenza e' calcolata giusta, cioe' su dati simulati in cui la risposta e'
  nota il test rifiuta con la frequenza dichiarata;
* restringere il regime e' **solo** un filtro di valutazione: nessuna riga di
  previsione cambia, altrimenti i due esiti non sarebbero confrontabili;
* la soglia e i regimi sono dichiarati in un posto solo, e il regime maturo
  coincide con il campione della Fase 2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from sot import config, predictor_power as PP, walkforward as wf


# --------------------------------------------------------- la potenza, sui numeri
def test_la_potenza_a_effetto_nullo_e_la_dimensione_del_test():
    """Con effetto zero la potenza deve valere P(t > soglia), non zero.

    E' il pavimento con cui vanno confrontate le potenze riportate: un 11% va
    letto come "poco piu' del 2.3% che si ottiene tirando a caso".
    """
    assert np.isclose(PP.potenza(0.0, 1.0), stats.norm.sf(PP.T_KEEP))
    assert np.isclose(PP.potenza(0.0, 0.003), stats.norm.sf(PP.T_KEEP))


def test_l_effetto_minimo_da_la_potenza_obiettivo():
    """MDE e potenza sono l'una l'inversa dell'altra: il giro deve chiudere."""
    for se in (0.001, 0.004, 0.02):
        mde = PP.effetto_minimo(se)
        assert np.isclose(PP.potenza(mde, se), PP.POTENZA_OBIETTIVO, atol=1e-9)


def test_la_potenza_cresce_con_l_effetto_e_cala_col_rumore():
    se = 0.005
    p = [PP.potenza(d, se) for d in (0.0, 0.005, 0.010, 0.020)]
    assert all(b > a for a, b in zip(p, p[1:]))
    assert PP.potenza(0.01, 0.005) > PP.potenza(0.01, 0.010)


def test_la_potenza_dichiarata_e_quella_vera_su_dati_simulati():
    """Controllo per simulazione: se l'effetto vero e' delta, la frequenza con
    cui il test appaiato supera la soglia deve essere la potenza calcolata.

    E' l'unico modo di validare una potenza senza circolarita': si genera un
    caso in cui la risposta e' nota, invece di verificarla sui risultati del
    progetto.
    """
    rng = np.random.default_rng(config.SEED)
    n, delta, sd = 100, 0.01, 0.07
    se = sd / np.sqrt(n)
    atteso = PP.potenza(delta, se)

    d = rng.normal(delta, sd, size=(4000, n))
    t = d.mean(axis=1) / (d.std(axis=1, ddof=1) / np.sqrt(n))
    empirica = float(np.mean(t > PP.T_KEEP))

    assert abs(empirica - atteso) < 0.02, (empirica, atteso)


# ------------------------------------------------------------- la molteplicita'
def test_il_massimo_atteso_di_otto_nulle_e_quello_citato_in_fase_2():
    """1.42 non e' un caso: e' il massimo atteso di otto normali standard.

    La Fase 2 ci ha letto il proprio `t` massimo. Se questo numero cambiasse,
    quella lettura andrebbe rifatta.
    """
    atteso = PP.t_atteso_massimo(8)
    assert np.isclose(atteso, 1.4236, atol=1e-3)

    rng = np.random.default_rng(config.SEED)
    simulato = float(rng.standard_normal((20000, 8)).max(axis=1).mean())
    assert abs(simulato - atteso) < 0.02


def test_il_p_del_massimo_e_uniforme_sotto_l_ipotesi_nulla():
    rng = np.random.default_rng(config.SEED)
    t_max = rng.standard_normal((5000, PP.FAMIGLIA)).max(axis=1)
    p = np.array([PP.p_del_massimo(v) for v in t_max])
    assert abs(float(np.mean(p < 0.05)) - 0.05) < 0.01
    assert abs(float(np.mean(p < 0.50)) - 0.50) < 0.03


def test_la_soglia_di_famiglia_e_piu_severa_di_quella_dichiarata():
    """La soglia usata resta `T_KEEP`; quella di famiglia si riporta accanto.

    Se `soglia_sidak` scendesse sotto `T_KEEP`, la correzione riportata nel
    report smetterebbe di essere una correzione.
    """
    assert PP.soglia_sidak(PP.FAMIGLIA) > PP.T_KEEP
    assert PP.soglia_sidak(1) < PP.soglia_sidak(8) < PP.soglia_sidak(100)


# ------------------------------------------- il tetto in campione e la sua lettura
def test_il_tetto_toglie_il_sovradattamento_di_un_parametro():
    assert PP.tetto_corretto(1.5) == 1.0
    assert PP.tetto_corretto(0.4) == 0.0        # troncato, non negativo
    assert PP.p_rapporto_verosimiglianza(0.0) == 1.0
    # 2 x 1.92 = 3.84 e' il 5% di un chi-quadro a un grado di liberta'
    assert np.isclose(PP.p_rapporto_verosimiglianza(1.9207), 0.05, atol=1e-3)


def test_un_guadagno_in_campione_negativo_non_diventa_un_alternativa():
    """Un tetto negativo non e' un'alternativa sensata per un test a una coda:
    deve dare la dimensione del test, non una potenza inventata."""
    assert PP.potenza(PP.tetto_corretto(-2.0) / 100, 0.005) == pytest.approx(
        stats.norm.sf(PP.T_KEEP))


# ------------------------------------------------------------------- i regimi
def test_i_regimi_sono_dichiarati_e_disgiunti_dove_devono_esserlo():
    assert PP.REGIMI["acerbo"] == (1, 8)
    assert PP.REGIMI["maturo"][0] == config.BURN_IN_ROUND
    assert PP.REGIMI["acerbo disgiunto"][1] == config.BURN_IN_ROUND - 1

    prev = pd.DataFrame({"team_match_idx": np.arange(1, 39)})
    acerbo = PP.maschera(prev, "acerbo")
    maturo = PP.maschera(prev, "maturo")
    disg = PP.maschera(prev, "acerbo disgiunto")

    assert not (disg & maturo).any(), "il regime disgiunto non deve toccare il maturo"
    assert (disg <= acerbo).all(), "il disgiunto e' un sottoinsieme dell'acerbo"
    assert (acerbo & maturo).sum() == 8 - config.BURN_IN_ROUND + 1


def test_la_soglia_e_dichiarata_in_un_posto_solo():
    """`run_phase2.py` non deve avere una propria copia di `T_KEEP`.

    Due soglie che divergono renderebbero il test di Fase 2 e quello di Fase 6D
    non confrontabili, ed e' esattamente il confronto che il report fa.
    """
    import importlib.util

    path = config.ROOT / "scripts" / "run_phase2.py"
    spec = importlib.util.spec_from_file_location("run_phase2", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.T_KEEP is PP.T_KEEP


# ------------------------------------- restringere il regime non tocca le previsioni
@pytest.fixture(scope="module")
def prev_finto():
    """Previsioni finte, ma con la forma vera: due squadre, dieci partite."""
    rng = np.random.default_rng(config.SEED)
    n_team, n_match = 4, 10
    rows = []
    for t in range(n_team):
        for i in range(1, n_match + 1):
            rows.append({"matchId": i * 10 + t, "team": f"T{t}",
                         "team_match_idx": i,
                         "date": pd.Timestamp("2025-08-23") + pd.Timedelta(days=7 * i),
                         "sot": rng.poisson(4.0)})
    out = pd.DataFrame(rows)
    out["lam_base"] = 4.0
    out["lam_poss_att"] = 4.0 + 0.2 * (out["sot"] - 4.0)   # predittore utile
    out["lam_ppda_att"] = 4.0 - 0.2 * (out["sot"] - 4.0)   # predittore dannoso
    return out


def test_il_regime_e_solo_un_filtro_di_valutazione(prev_finto):
    """Le righe di un regime devono avere gli **stessi** lambda del campione
    intero: se cambiassero, il regime starebbe ristimando qualcosa."""
    m = PP.maschera(prev_finto, "acerbo")
    a = PP.confronto(prev_finto, "acerbo", candidati=("poss_att",))
    tutte = PP.confronto(prev_finto, "maturo", candidati=("poss_att",))

    atteso = float(np.sum(
        PP._ll(prev_finto.loc[m, "sot"], prev_finto.loc[m, "lam_poss_att"])
        - PP._ll(prev_finto.loc[m, "sot"], prev_finto.loc[m, "lam_base"])))
    assert np.isclose(a.iloc[0]["d_oos"], atteso)
    assert a.iloc[0]["n"] == int(m.sum())
    assert tutte.iloc[0]["n"] == int(PP.maschera(prev_finto, "maturo").sum())


def test_il_segno_del_guadagno_e_quello_giusto(prev_finto):
    """Su un predittore costruito utile il `t` e' positivo, su uno dannoso
    negativo. Banale, ed e' il motivo per cui va verificato: se fosse invertito
    tutto il resto del report sarebbe letto al contrario."""
    tab = PP.confronto(prev_finto, "acerbo",
                       candidati=("poss_att", "ppda_att")).set_index("predittore")
    assert tab.loc["poss_att", "t"] > 0
    assert tab.loc["ppda_att", "t"] < 0
    assert tab.loc["ppda_att", "d_oos"] < 0


# ----------------------------------------------------------- sui dati veri
def test_il_regime_maturo_e_il_campione_della_fase_2(team_match):
    """`maschera(..., "maturo")` deve selezionare esattamente le righe che
    `walkforward.eligible` seleziona: e' l'affermazione su cui poggia il
    "accanto, non al posto" del report."""
    df = team_match
    prev = pd.DataFrame({"team_match_idx": df["team_match_idx"]})
    assert np.array_equal(PP.maschera(prev, "maturo"),
                          wf.eligible(df).to_numpy())


@pytest.mark.skipif(not (config.PROCESSED / "phase6d_predittori.parquet").exists(),
                    reason="serve run_phase6d.py")
def test_il_predittore_compra_penalita_non_adattamento(team_match):
    """La spiegazione del report va verificata, non asserita: aggiungere un
    predittore collineare con l'attacco **abbassa la penalita' ridge** e
    migliora l'obiettivo, anche quando la verosimiglianza grezza peggiora."""
    df = wf.build_predictors(team_match)
    prev = pd.read_parquet(config.PROCESSED / "phase6d_predittori.parquet")
    righe = PP.righe_del_regime(df, prev, "maturo")

    base = PP.penalita(righe)
    con = PP.penalita(righe, ("poss_att",))

    assert con["obiettivo"] < base["obiettivo"], "l'obiettivo deve migliorare"
    assert con["penalita"] < base["penalita"], "la penalita' deve scendere"
    assert con["loglik"] < base["loglik"], (
        "nel regime maturo il guadagno grezzo e' negativo: se un giorno "
        "diventasse positivo, la sezione 2 del report va riscritta")
