# -*- coding: utf-8 -*-
"""Test della Fase 6F — il piano dati.

Un piano non si valida con un p-value: si valida verificando che (a) sia
coerente con se' stesso, (b) non affermi cose false sul codice, (c) la sola
cosa che calcola — la simulazione sui nuovi arrivi — sia corretta e non abbia
spostato la proiezione pubblicata.

Il vincolo piu' importante di tutto il blocco e' l'ultimo: 6F **non deve
cambiare nessun numero pubblicato**, e con `sd_nuovi=None` il Monte Carlo deve
restare identico bit per bit.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import (config, data_plan as DP, model_player as MP,
                 project_2627 as P, squad_2627 as SQ)

ROOT = Path(__file__).resolve().parent.parent
N_SIM_TEST = 4000


# --------------------------------------------------------------- fixture
@pytest.fixture(scope="module")
def proiezione(player_match, team_match):
    proj, s, model, du = P.build_projection(player_match, team_match, tau=3.0)
    return proj, s, model, du


# ------------------------------------------------------ coerenza del piano
def test_ogni_blocco_6a_6e_compare_nel_piano():
    """Il piano deve dire qualcosa su ciascun blocco eseguito, altrimenti e'
    un piano parziale che si spaccia per completo."""
    sbloccati = {d["sblocca"] for d in DP.DOMANDE_APERTE}
    assert {"6A", "6B", "6C", "6D", "6E"} <= sbloccati


def test_granularita_dichiarate_esistono():
    livelli = {g[0] for g in DP.GRANULARITA}
    for d in DP.DOMANDE_APERTE:
        assert d["granularita"] in livelli, d["id"]


def test_id_domande_univoci():
    ids = [d["id"] for d in DP.DOMANDE_APERTE]
    assert len(ids) == len(set(ids))


def test_chiavi_uniformi():
    attese = set(DP.DOMANDE_APERTE[0].keys())
    for d in DP.DOMANDE_APERTE:
        assert set(d.keys()) == attese, d["id"]


def test_solo_6d_richiede_eventi():
    """E' l'affermazione centrale del blocco: gli eventi grezzi servono solo
    per ricalcolare field tilt, PPDA e xG interno, cioe' solo al blocco 6D."""
    con_eventi = [d for d in DP.DOMANDE_APERTE if d["eventi"]]
    assert len(con_eventi) == 1
    assert con_eventi[0]["sblocca"] == "6D"


def test_le_domande_sul_livello_stanno_sulla_granularita_piu_grossolana():
    """Conseguenza della Fase 6A: il livello non contiene il modello di
    squadra, quindi si risponde con totali di stagione."""
    per_id = {d["id"]: d for d in DP.DOMANDE_APERTE}
    for i in ("D1", "D2", "D5"):
        assert per_id[i]["granularita"] == "G1"


# ------------------------------------------ affermazioni sul codice, verificate
def test_provenienza_dei_nuovi_arrivi_davvero_assente():
    """Il piano dichiara che il campionato di provenienza non e' nel
    repository. Se qualcuno lo aggiungesse a `NEW_SIGNINGS` senza aggiornare il
    piano, il piano direbbe il falso."""
    for entry in SQ.NEW_SIGNINGS:
        assert len(entry) == 3, entry           # (nome, playerId, ruolo)
        nome, pid, ruolo = entry
        assert pid is None
        assert ruolo in ("GK",) + MP.ROLES


def test_sei_nuovi_arrivi_di_movimento():
    """Il numero sei e' citato ovunque nel piano: va ancorato al codice."""
    non_gk = [n for n in SQ.NEW_SIGNINGS if n[2] != "GK"]
    assert len(non_gk) == 6


def test_il_piano_non_scarica_niente():
    """6F non deve introdurre nessun accesso alla rete, in nessuna forma."""
    vietati = ("requests", "urllib", "http.client", "socket", "selenium",
               "webdriver", "urlopen", "aiohttp", "httpx")
    for f in (ROOT / "sot" / "data_plan.py", ROOT / "scripts" / "run_phase6f.py"):
        testo = f.read_text(encoding="utf-8")
        # si guardano solo le righe di import, non la prosa delle docstring
        imports = [r for r in testo.splitlines()
                   if re.match(r"\s*(import|from)\s", r)]
        for v in vietati:
            assert not any(v in r for r in imports), (f.name, v)


def test_nessuno_script_della_proiezione_importa_il_piano():
    """Come per `calendar_2627`: il piano misura, non entra nella proiezione."""
    for nome in ("run_phase3.py", "run_phase5.py"):
        testo = (ROOT / "scripts" / nome).read_text(encoding="utf-8")
        assert "data_plan" not in testo, nome


# --------------------------------------------- l'errore standard da esposizione
def test_se_a_esposizione_nulla_e_il_tetto_del_modello():
    tau = 3.0
    assert DP.se_da_esposizione(0.5, 0.0, tau) == pytest.approx(
        1.0 / np.sqrt(2.0 * tau))


def test_se_decresce_con_i_minuti():
    tau = 3.0
    valori = [DP.se_da_esposizione(0.3, m, tau) for m in DP.MINUTI_GRID]
    assert all(a > b for a, b in zip(valori, valori[1:]))


def test_approssimazione_di_fisher_riproduce_player_effect_se(proiezione,
                                                              player_match,
                                                              team_match):
    """`se_da_esposizione` e' un'approssimazione della diagonale esatta: il
    piano la usa per estrapolare a esposizioni non osservate, quindi va
    verificata dove l'esatta esiste."""
    _, _, model, du = proiezione
    esatta = P.player_effect_se(model, du)

    lam = model.predict(du)
    attesi = (pd.DataFrame({"playerId": du["playerId"].to_numpy(), "lam": lam})
              .groupby("playerId")["lam"].sum())
    approx = 1.0 / np.sqrt(attesi + 2.0 * model.tau)

    cmp = pd.DataFrame({"a": approx, "e": esatta}).dropna()
    assert len(cmp) > 400
    rapporto = (cmp["e"] / cmp["a"])
    assert float(rapporto.median()) == pytest.approx(1.0, abs=0.01)
    assert float(np.corrcoef(cmp["a"], cmp["e"])[0, 1]) > 0.99


def test_sd_prior_solo_sui_nuovi(proiezione):
    proj, _, model, _ = proiezione
    sd = DP.sd_prior_nuovi(proj, model, 1800.0, 0.0, 3.0)
    is_new = proj["is_new"].to_numpy()
    assert np.all(sd[~is_new] == 0.0)
    assert np.all(sd[is_new] > 0.0)


def test_incertezza_di_trasferimento_allarga(proiezione):
    proj, _, model, _ = proiezione
    a = DP.sd_prior_nuovi(proj, model, 1800.0, 0.0, 3.0)
    b = DP.sd_prior_nuovi(proj, model, 1800.0, 1.0, 3.0)
    is_new = proj["is_new"].to_numpy()
    assert np.all(b[is_new] > a[is_new])


# ------------------------------------------------- il vincolo che conta di piu'
def test_sd_nuovi_none_non_cambia_un_bit(proiezione):
    """Il parametro aggiunto per la Fase 6F non deve spostare la proiezione
    pubblicata: con `None` il Monte Carlo e' identico all'originale."""
    proj, s, model, _ = proiezione
    a = P.monte_carlo(proj, s, model, r=26.0, n_sim=N_SIM_TEST)
    b = P.monte_carlo(proj, s, model, r=26.0, n_sim=N_SIM_TEST, sd_nuovi=None)
    assert np.array_equal(a, b)


def test_sd_nuovi_zero_toglie_la_fonte(proiezione):
    """Con prior nullo i nuovi arrivi smettono di contribuire varianza, cioe'
    il parametro agisce dove deve."""
    proj, s, model, _ = proiezione
    v = P.monte_carlo(proj, s, model, r=26.0, n_sim=N_SIM_TEST,
                      sources=("new_signings",),
                      sd_nuovi=np.zeros(len(proj))).var()
    assert v == pytest.approx(0.0, abs=1e-9)


def test_un_prior_piu_stretto_non_allarga(proiezione):
    """Monotonia: meno incertezza sui nuovi arrivi, meno varianza dalla loro
    fonte. Se non valesse, la simulazione del piano non misurerebbe niente."""
    proj, s, model, _ = proiezione
    vs = []
    for minuti in (0, 900, 1800, 3000):
        sd = DP.sd_prior_nuovi(proj, model, minuti, 0.0, 3.0)
        vs.append(P.monte_carlo(proj, s, model, r=26.0, n_sim=N_SIM_TEST,
                                sources=("new_signings",), sd_nuovi=sd).var())
    assert all(a > b for a, b in zip(vs, vs[1:]))


def test_prior_pubblicato_piu_stretto_del_tetto_del_modello(proiezione):
    """Il fatto scomodo che il piano riporta: il prior "gonfiato" dei nuovi
    arrivi (1.5 x la dispersione fra giocatori) e' piu' STRETTO di quello che
    il modello darebbe a un giocatore senza esposizione."""
    _, _, model, _ = proiezione
    eff = model.player_effects()["v"].to_numpy()
    pubblicato = 1.5 * float(np.std(eff[np.abs(eff) > 1e-9]))
    tetto = DP.se_da_esposizione(0.3, 0.0, model.tau)
    assert pubblicato < tetto


# ---------------------------------------------------------- il conto per il 6D
def test_righe_per_potenza_riproduce_il_t_di_fase6d():
    """Con i numeri per riga di `poss_att` nel regime maturo il `t`
    ricostruito deve essere quello che la Fase 6D riporta."""
    p = DP.righe_per_potenza(0.004076449507324901, 660, 0.005788883258148282)
    assert p["t_atteso_ora"] == pytest.approx(1.4200797158768528, rel=1e-9)


def test_righe_per_potenza_scala_col_quadrato():
    a = DP.righe_per_potenza(0.004, 660, 0.006)
    b = DP.righe_per_potenza(0.008, 660, 0.006)   # se doppio -> 4x le righe
    assert b["n_righe_servite"] / a["n_righe_servite"] == pytest.approx(4.0)


def test_piu_potenza_richiede_piu_righe():
    a = DP.righe_per_potenza(0.004, 660, 0.006, potenza=0.80)
    b = DP.righe_per_potenza(0.004, 660, 0.006, potenza=0.95)
    assert b["n_righe_servite"] > a["n_righe_servite"]


def test_potenza_da_t_coerente_con_predictor_power():
    """La potenza qui ricostruita deve coincidere con quella di Fase 6D: 11%
    nell'acerbo contro l'alternativa dichiarata."""
    t = 0.005788883258148282 / 0.007499
    assert DP.potenza_da_t(t) == pytest.approx(0.11, abs=0.01)


@pytest.mark.skipif(not (config.REPORTS / "phase6_predittori.csv").exists(),
                    reason="serve run_phase6d.py")
def test_piano_6d_dalla_tabella_di_fase6d():
    pred = pd.read_csv(config.REPORTS / "phase6_predittori.csv")
    tab = DP.piano_6d(pred)
    assert set(tab["regime"]) == {"maturo", "acerbo", "acerbo disgiunto"}
    # nessun regime ha gia' la potenza che servirebbe
    assert (tab["potenza_ora"] < 0.80).all()
    # e tutti chiedono piu' righe di quante ne producano in una stagione
    assert (tab["stagioni_campionato"] > 1.0).all()
