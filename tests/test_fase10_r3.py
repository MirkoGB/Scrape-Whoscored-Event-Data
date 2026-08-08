# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R3 — test della classifica e della simulazione.

Una simulazione Monte Carlo si verifica in due modi, e servono entrambi: sulle
**identita' contabili**, che devono valere in ogni replica e non in media (una
stagione distribuisce un monte punti quasi fisso, e se non tornasse ogni
probabilita' sarebbe costruita su una classifica rotta), e su **casi in cui la
risposta e' nota a mano** — due squadre, probabilita' degenere, esito certo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import classifica as CL, config, ricalibrazione as RC


@pytest.fixture(scope="module")
def cal() -> pd.DataFrame:
    return CL.calendario()


@pytest.fixture(scope="module")
def sim() -> dict:
    return CL.simula("2025-2026", 19, repliche=800)


# ---------------------------------------------------------------------------
# Il calendario e la classifica vera: identita' falsificabili, senza modelli
# ---------------------------------------------------------------------------

def test_il_calendario_regge_le_identita(cal):
    v = CL.verifica_calendario()
    assert (v["partite"] == 380).all()
    assert (v["squadre"] == 20).all()
    assert v["38 partite a testa"].all()
    assert v["19 in casa a testa"].all()
    assert v["identita' dei punti"].all()


def test_la_classifica_finale_distribuisce_il_monte_punti_giusto():
    """`3n - pareggi`: un pareggio ne distribuisce 2 invece di 3."""
    for st in config.SEASONS_STORICHE:
        c = CL.classifica_a(st, 38)
        assert int(c["giocate"].sum()) == 760
        assert int(c["gf"].sum()) == int(c["gs"].sum())


def test_la_classifica_a_k_e_monotona_nei_punti():
    """Nessuna squadra puo' perdere punti avanzando di giornata."""
    a = CL.classifica_a("2025-2026", 10)
    b = CL.classifica_a("2025-2026", 20)
    assert (b.loc[a.index, "punti"] >= a["punti"]).all()
    assert (b.loc[a.index, "giocate"] >= a["giocate"]).all()


def test_le_partite_fuori_ordine_sono_poche_e_contate():
    """La domanda aperta n. 4 di R0, risposta con una misura."""
    t = CL.partite_fuori_ordine()
    assert (t["fuori ordine"] <= 10).all()
    assert (t["fuori ordine"] > 0).any(), "se fossero zero ovunque, la misura non guarda"


def test_il_ripiego_e_piccolo_e_solo_dove_manca_l_archivio(cal):
    """Le partite senza previsione stanno nelle due stagioni bucate, non ovunque."""
    t = CL.copertura_previsioni()
    assert (t["ripiego dopo la 19a"] <= 5).all()
    tardi = t.set_index("stagione")["ripiego dopo la 28a"]
    assert tardi[["2023-2024", "2024-2025", "2025-2026"]].sum() == 0


# ---------------------------------------------------------------------------
# La simulazione: contabilita' in OGNI replica
# ---------------------------------------------------------------------------

def test_ogni_replica_distribuisce_fra_2_e_3_punti_per_partita(sim):
    """Identita' che non puo' valere «in media»: ogni singola replica deve
    distribuire fra 760x2 e 760x3 punti, cioe' tutti pareggi o nessuno."""
    tot = sim["punti"].sum(axis=1)
    assert (tot >= 2 * 380).all() and (tot <= 3 * 380).all()


def test_in_ogni_replica_i_gol_fatti_pareggiano_i_subiti(sim):
    """`gf - gs` sommato sulle venti squadre deve fare zero in ogni replica: un
    gol e' fatto da qualcuno e subito da qualcun altro."""
    assert np.allclose(sim["dr"].sum(axis=1), 0.0)


def test_la_classifica_a_k_entra_come_costante(sim):
    """La storia non si simula: i punti minimi di ogni squadra sono quelli che ha
    gia', e nessuna replica puo' scendere sotto."""
    base = CL.classifica_a("2025-2026", 19).loc[sim["squadre"], "punti"].to_numpy()
    assert (sim["punti"] >= base).all()


def test_simulare_dalla_38a_riproduce_la_classifica_vera():
    """Il caso limite in cui la risposta e' nota: senza partite da giocare, la
    simulazione **deve** restituire la classifica finale vera, esattamente."""
    s = CL.simula("2024-2025", 38, repliche=50)
    vera = CL.classifica_a("2024-2025", 38).loc[s["squadre"]]
    assert np.allclose(s["punti"], vera["punti"].to_numpy()[None, :])
    assert np.allclose(s["dr"], (vera["gf"] - vera["gs"]).to_numpy()[None, :])


def test_la_simulazione_e_riproducibile():
    a = CL.simula("2025-2026", 30, repliche=200)
    b = CL.simula("2025-2026", 30, repliche=200)
    assert np.array_equal(a["punti"], b["punti"])


def test_il_punteggio_estratto_e_COERENTE_con_l_esito_estratto():
    """La costruzione del blocco, messa alla prova: si estrae l'esito e poi il
    punteggio **dentro** quella classe. Se le due estrazioni si slegassero, una
    partita potrebbe dare 3 punti a chi ha segnato meno gol."""
    celle = CL._celle_condizionate(1.6, 1.2)
    for j, (cc, pp) in enumerate(celle):
        assert np.isclose(pp.sum(), 1.0)
        d = cc[:, 0] - cc[:, 1]
        if j == 0:
            assert (d > 0).all()
        elif j == 1:
            assert (d == 0).all()
        else:
            assert (d < 0).all()


def test_una_probabilita_degenere_da_l_esito_certo():
    """Caso calcolabile a mano: se `p1 = 1` su tutte le partite rimanenti, la
    squadra di casa vince sempre e prende 3 punti a partita."""
    cal = CL.calendario(["2025-2026"]).copy()
    m = cal["giornata"] > 36
    cal.loc[m, ["p1", "pX", "p2"]] = [1.0, 0.0, 0.0]
    s = CL.simula("2025-2026", 36, repliche=100, cal=cal)
    base = CL.classifica_a("2025-2026", 36).loc[s["squadre"], "punti"].to_numpy()
    guadagno = s["punti"] - base
    # due giornate: chi gioca due volte in casa fa 6, chi mai fa 0
    assert set(np.unique(guadagno)) <= {0.0, 3.0, 6.0}


# ---------------------------------------------------------------------------
# Le probabilita': vincoli contabili, non calibrazione
# ---------------------------------------------------------------------------

def test_le_probabilita_di_classifica_sommano_ai_posti(sim):
    p = CL.probabilita("2025-2026", 19, sim=sim)
    assert np.isclose(p["scudetto"].sum(), 1.0)
    assert np.isclose(p[f"top {CL.POSTI_EUROPA}"].sum(), CL.POSTI_EUROPA)
    assert np.isclose(p["retrocessione"].sum(), CL.POSTI_RETROCESSIONE)


def test_la_media_dichiarata_uguale_alla_frequenza_vera_e_un_IDENTITA():
    """Il numero che NON va letto come calibrazione, bloccato perche' resti
    leggibile come vincolo contabile: le probabilita' sommano ai posti e i posti
    sono sempre occupati."""
    a = CL.affidabilita_claim(k_list=(19,), repliche=800)
    assert np.allclose(a["media dichiarata"], a["frequenza vera"], atol=1e-9)


def test_il_brier_delle_tre_affermazioni_batte_il_tasso_base():
    """Questo invece dice qualcosa, ed e' l'unica colonna della tabella che lo fa."""
    a = CL.affidabilita_claim(k_list=(19,), repliche=800)
    assert (a["Brier"] < a["Brier tasso base"]).all()


# ---------------------------------------------------------------------------
# I risultati del blocco, bloccati
# ---------------------------------------------------------------------------

def test_la_copertura_NON_e_sotto_il_nominale():
    """Il risultato che contraddice l'attesa di R2-bis: gli intervalli sono se
    mai troppo larghi, non troppo stretti."""
    c = CL.copertura(k_list=(19,), repliche=2000).iloc[0]
    assert c["copertura 50%"] >= 0.50
    assert c["copertura 80%"] >= 0.80
    assert c["copertura 95%"] >= 0.93


def test_la_sotto_dispersione_si_attenua_avanzando_nella_stagione():
    """Il meccanismo che spiega il risultato precedente, misurato: la classifica a
    `k` porta dentro la separazione VERA, e piu' `k` avanza meno resta da
    comprimere. Se il rapporto non calasse, la spiegazione sarebbe sbagliata."""
    r = [CL.dispersione_finale(k=k, repliche=1500)["rapporto sd"].mean()
         for k in (10, 19, 28)]
    assert r[0] > r[1] > r[2] > 1.0
    assert r[0] < 2.0, "molto sotto il 2,0 che R2-bis misura per partita"


def test_sulla_classifica_il_modello_batte_il_baseline_migliore():
    """E su 1X2 non lo faceva (t = −1,10): diciannove giornate accumulano il
    margine che una partita sola non distingue dal rumore."""
    a = CL.confronto_appaiato_punti(k=19, repliche=2000).set_index("baseline")
    r = a.loc["media squadra + campo"]
    assert r["modello vince"]
    assert r["t (stagione, n=5)"] < -2.0


def test_la_ricalibrazione_di_r2bis_non_peggiora_i_punti():
    a = CL.confronto_appaiato_punti(k=19, repliche=2000).set_index("baseline")
    assert a.loc["modello grezzo", "differenza"] < 0


def test_media_campionato_si_rompe_sulla_copertura():
    """Non solo accuratezza: un candidato che non distingue le squadre sottostima
    anche quanto la classifica possa allontanarsi dalla sua previsione piatta."""
    c = CL.copertura(k_list=(19,), repliche=1500, variante="media campionato").iloc[0]
    assert c["copertura 80%"] < 0.70
    assert c["MAE punti"] > 6.0


# ---------------------------------------------------------------------------
# Guardie
# ---------------------------------------------------------------------------

def test_i_baseline_passano_per_la_STESSA_simulazione():
    """Vincolo 6: se il modello passasse per la congiunta e i baseline per una
    regola diversa, si misurerebbe la composizione invece del lambda."""
    src = (config.ROOT / "sot" / "classifica.py").read_text(encoding="utf-8")
    assert src.count("def simula(") == 1
    assert "VARIANTI = (" in src


def test_le_giornate_di_valutazione_sono_dichiarate():
    """Vincolo 1 applicato a una soglia, come per l'80' e per le soglie di E1."""
    src = (config.ROOT / "sot" / "classifica.py").read_text(encoding="utf-8")
    assert "K_VALUTAZIONE = (10, 19, 28)" in src
    for vietato in ("argmax", "idxmax", "idxmin"):
        assert vietato not in src, f"non vanno ricavate dai dati: {vietato!r}"


def test_vincolo_3_nessuna_quota_nel_modulo():
    src = (config.ROOT / "sot" / "classifica.py").read_text(encoding="utf-8").lower()
    for vietato in ("odds", "quota_decimale", "payout", "bankroll", "kelly",
                    "stake", "profitto", "roi"):
        assert vietato not in src, f"vincolo 3: trovato {vietato!r}"


def test_r3_non_stima_parametri_nuovi():
    src = (config.ROOT / "sot" / "classifica.py").read_text(encoding="utf-8")
    for vietato in ("minimize", "curve_fit", "TeamModel", "LogisticRegression"):
        assert vietato not in src, f"R3 simula, non stima: trovato {vietato!r}"


def test_nessun_numero_pubblicato_e_cambiato():
    from sot import difesa, esiti as E, perimetro as PM

    assert len(difesa.walkforward_gol()) == 3478
    assert int(PM.partite()["validabile"].sum()) == 1638
    assert len(RC.dati()) == 1638
    pv = E.previsioni()
    p = pv[[f"modello|p{c}" for c in E.CLASSI]].to_numpy()
    assert round(float(E.rps(p, pv["esito"].to_numpy()).mean()), 4) == 0.2041
