# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2 — test delle metriche e dei numeri pubblicati.

Le metriche si verificano su casi in cui la risposta e' **nota a mano**, non sui
risultati del progetto: e' la regola che `tests/test_validate.py` segue dalla
Fase 4, e la ragione e' che validare una metrica sui propri risultati e'
circolare.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import config, esiti as E, perimetro as PM


@pytest.fixture(scope="module")
def pv() -> pd.DataFrame:
    return E.previsioni()


# ---------------------------------------------------------------------------
# Le metriche, su casi calcolabili a mano
# ---------------------------------------------------------------------------

def test_rps_previsione_perfetta_vale_zero():
    p = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    assert np.allclose(E.rps(p, np.array(["1", "X", "2"])), 0.0)


def test_rps_previsione_pessima_vale_uno():
    """Tutta la massa sull'estremo opposto: il massimo possibile."""
    p = np.array([[0.0, 0.0, 1.0]])
    assert np.allclose(E.rps(p, np.array(["1"])), 1.0)


def test_rps_conosce_l_ordine_e_la_logloss_no():
    """Il motivo per cui l'RPS e' la metrica principale, messo alla prova.

    Esito vero `1`. Due previsioni sbagliate allo stesso modo per la log-loss —
    entrambe danno 0.2 alla classe giusta — ma una mette il resto sul pareggio
    e l'altra sulla vittoria opposta. L'RPS deve distinguerle, la log-loss no.
    """
    vicina = np.array([[0.2, 0.8, 0.0]])
    lontana = np.array([[0.2, 0.0, 0.8]])
    y = np.array(["1"])
    assert E.rps(vicina, y)[0] < E.rps(lontana, y)[0]
    assert np.isclose(E.logloss(vicina, y)[0], E.logloss(lontana, y)[0])


def test_rps_e_fra_zero_e_uno(pv):
    p = pv[[f"modello|p{c}" for c in E.CLASSI]].to_numpy()
    v = E.rps(p, pv["esito"].to_numpy())
    assert v.min() >= 0.0 and v.max() <= 1.0


def test_logloss_su_previsione_uniforme():
    p = np.full((3, 3), 1 / 3)
    assert np.allclose(E.logloss(p, np.array(["1", "X", "2"])), np.log(3))


def test_le_probabilita_sommano_a_uno(pv):
    for cand in ["modello", *PM.BASELINE]:
        s = pv[[f"{cand}|p{c}" for c in E.CLASSI]].sum(axis=1)
        assert np.allclose(s, 1.0)


def test_over_decresce_con_la_linea(pv):
    for cand in ["modello", *PM.BASELINE]:
        a = pv[f"{cand}|over1.5"].to_numpy()
        b = pv[f"{cand}|over2.5"].to_numpy()
        c = pv[f"{cand}|over3.5"].to_numpy()
        assert (a > b).all() and (b > c).all()


# ---------------------------------------------------------------------------
# Vincolo 1: niente stima su dati che seguono il bersaglio
# ---------------------------------------------------------------------------

def test_il_tasso_base_1x2_guarda_solo_il_passato(pv):
    """Guastando la coda della stagione, le righe precedenti non devono muoversi.

    E' lo stesso disegno dei test di leakage su `walkforward_r` (Fase 4).
    """
    base = E._tasso_base(pv)
    rotto = pv.sort_values(["stagione", "matchId"]).reset_index(drop=True).copy()
    meta = len(rotto) // 2
    rotto.loc[meta:, "esito"] = "X"
    dopo = E._tasso_base(rotto)
    # Le righe della PRIMA stagione, prima del guasto, non possono cambiare.
    n_prima = int((rotto["stagione"] == rotto["stagione"].iloc[0]).sum())
    k = min(n_prima, meta)
    assert np.allclose(base[:k], dopo[:k])
    assert not np.allclose(base[meta:], dopo[meta:])


def test_il_tasso_base_over_guarda_solo_il_passato(pv):
    """Il difetto che questo blocco ha commesso e corretto: ora e' bloccato."""
    base = E._tasso_base_over(pv, 2.5)
    rotto = pv.sort_values(["stagione", "matchId"]).reset_index(drop=True).copy()
    meta = len(rotto) // 2
    rotto.loc[meta:, "gol_totali"] = 99
    dopo = E._tasso_base_over(rotto, 2.5)
    n_prima = int((rotto["stagione"] == rotto["stagione"].iloc[0]).sum())
    k = min(n_prima, meta)
    assert np.allclose(base[:k], dopo[:k])
    assert not np.allclose(base[meta:], dopo[meta:])


def test_il_tasso_base_non_e_la_media_dell_intero_campione(pv):
    """Se coincidesse, il walk-forward non starebbe facendo niente."""
    wf = E._tasso_base_over(pv, 2.5)
    intero = float((pv["gol_totali"] > 2.5).mean())
    assert not np.allclose(wf, intero)


# ---------------------------------------------------------------------------
# I numeri pubblicati
# ---------------------------------------------------------------------------

def test_perimetro_invariato(pv):
    """R2 non deve aver cambiato il conteggio di R0."""
    assert len(pv) == 1638


def test_partite_senza_baseline_e_identica_a_r0():
    """`con_baseline=True` non deve cambiare l'uscita di default.

    Se la aggiungesse o togliesse righe, ogni numero di R0 sarebbe da rifare.
    """
    a = PM.partite()
    b = PM.partite(con_baseline=True)
    assert len(a) == len(b)
    assert int(a["validabile"].sum()) == int(b["validabile"].sum()) == 1638
    for c in a.columns:
        assert c in b.columns
        if pd.api.types.is_numeric_dtype(a[c]):
            assert np.allclose(a[c].to_numpy(), b[c].to_numpy(), equal_nan=True)


def test_rps_pubblicato(pv):
    v = E.valutazione(pv).set_index("candidato")
    assert abs(v.loc["modello", "RPS"] - 0.2041) < 5e-4
    assert abs(v.loc["media squadra + campo", "RPS"] - 0.2057) < 5e-4


def test_su_1x2_il_modello_batte_l_ignoranza(pv):
    a = E.confronto_appaiato(pv, "RPS").set_index("baseline")
    for b in ("media campionato", "media casa/trasferta", "tasso base 1X2"):
        assert a.loc[b, "t"] < -5
        assert bool(a.loc[b, "oltre il rumore"])


def test_su_1x2_il_modello_NON_batte_la_forza_di_squadra(pv):
    """Il risultato negativo del blocco: dentro il rumore, come in Fase 2 e 4.

    Non va "sistemato". Se un giorno passasse, deve essere per un modello nuovo
    e non per una metrica scelta dopo aver guardato.
    """
    a = E.confronto_appaiato(pv, "RPS").set_index("baseline")
    r = a.loc["media squadra + campo"]
    assert r["differenza"] < 0          # il segno e' a favore del modello
    assert abs(r["t"]) < 2.0            # ma non supera il rumore
    assert not bool(r["oltre il rumore"])


def test_su_over_under_l_ordine_si_rovescia(pv):
    """Il risultato non previsto: sui totali i baseline si scambiano i ruoli."""
    a = E.confronto_appaiato(pv, "Brier O2.5").set_index("baseline")
    # contro la media di campionato il modello NON vince
    assert a.loc["media campionato", "differenza"] > 0
    # contro i baseline di squadra vince, e oltre il rumore
    assert a.loc["media squadra + campo", "differenza"] < 0
    assert bool(a.loc["media squadra + campo", "oltre il rumore"])


def test_il_modello_e_l_unico_decente_su_entrambe(pv):
    """L'argomento con cui R2 giustifica il modello, messo in un test.

    Nessun baseline e' contemporaneamente vicino al modello su RPS e su O2.5.
    """
    v = E.valutazione(pv).set_index("candidato")
    m_rps, m_o25 = v.loc["modello", "RPS"], v.loc["modello", "Brier O2.5"]
    for b in PM.BASELINE:
        vicino_rps = v.loc[b, "RPS"] < m_rps * 1.02
        vicino_o25 = v.loc[b, "Brier O2.5"] < m_o25 * 1.02
        assert not (vicino_rps and vicino_o25), (
            f"{b} e' vicino al modello su entrambe: l'argomento di §4 cade"
        )


def test_il_totale_di_gol_e_quasi_imprevedibile():
    """Il fatto che spiega §4, e che ha corretto la spiegazione scritta prima.

    Nessun candidato supera 0,11 di correlazione fra somma prevista e totale
    vero. Se un giorno qualcuno la superasse, §4 andrebbe riscritta — e questo
    test lo rende visibile invece che silenzioso.
    """
    d = E.dispersione_somma().set_index("candidato")
    c = d["corr con il totale vero"].dropna()
    assert c.max() < 0.11
    assert d.loc["modello", "corr con il totale vero"] == pytest.approx(c.max())


def test_l_ordine_della_dispersione_spiega_l_ordine_del_brier(pv):
    """Meno dispersione sulla somma = Brier migliore, dato che la corr e' ~0.1."""
    d = E.dispersione_somma().set_index("candidato")["sd"]
    v = E.valutazione(pv).set_index("candidato")["Brier O2.5"]
    for a, b in (("media campionato", "modello"), ("modello", "media squadra")):
        assert d[a] < d[b]
        assert v[a] < v[b]


def test_le_medie_di_squadra_non_disperdono_piu_del_vero():
    """La frase che la misura ha smentito, tenuta come test.

    Serve perche' la spiegazione sbagliata era plausibile: senza il numero
    accanto, qualcuno la riscriverebbe.
    """
    d = E.dispersione_somma().set_index("candidato")["sd"]
    assert d["media squadra"] < d["**osservato**"]


def test_il_modello_e_sotto_sicuro_su_1x2(pv):
    """Pendenza sopra 1.0, segno OPPOSTO a quello della Fase 4. E' il risultato."""
    p1 = E.pendenza_calibrazione(pv, "modello", "1")
    p2 = E.pendenza_calibrazione(pv, "modello", "2")
    assert p1["pendenza"] > 1.0 and p2["pendenza"] > 1.0
    assert p1["z vs 1.0"] > 2.0 or p2["z vs 1.0"] > 2.0
    # e il baseline di squadra e' meglio calibrato del modello
    pb = E.pendenza_calibrazione(pv, "media squadra + campo", "1")
    assert abs(pb["pendenza"] - 1.0) < abs(p1["pendenza"] - 1.0)


def test_media_campionato_non_e_identificata(pv):
    """Come in Fase 4, e per la stessa ragione: logit quasi costante."""
    r = E.pendenza_calibrazione(pv, "media campionato", "1")
    assert r["errore standard"] > 0.5


# ---------------------------------------------------------------------------
# Il pavimento
# ---------------------------------------------------------------------------

def test_il_pavimento_tocca_una_riga_sola():
    p = E.righe_pavimentate().set_index("candidato")
    assert int(p.loc["media squadra", "righe_pavimentate"]) == 1
    assert int(p.loc["modello", "righe_pavimentate"]) == 0


def test_senza_pavimento_la_logloss_sarebbe_infinita():
    """Il motivo per cui il pavimento esiste, verificato invece che asserito."""
    from sot import risultato as R

    p = PM.partite(con_baseline=True)
    d = p[p["validabile"]]
    m = d[(d["media squadra_casa"] <= 0) | (d["media squadra_trasferta"] <= 0)]
    assert len(m) == 1
    r = m.iloc[0]
    # la squadra con lambda zero ha segnato davvero
    zero_in_casa = r["media squadra_casa"] <= 0
    assert (r["gol_casa"] if zero_in_casa else r["gol_trasferta"]) > 0
    # e la congiunta a lambda 0 mette probabilita' zero sull'esito osservato
    pj = R.congiunta(max(r["media squadra_casa"], 0.0),
                     max(r["media squadra_trasferta"], 0.0), 0.0)
    assert pj[int(r["gol_casa"]), int(r["gol_trasferta"])] == 0.0


# ---------------------------------------------------------------------------
# Guardie
# ---------------------------------------------------------------------------

def test_vincolo_3_nessuna_quota_nel_modulo():
    """Nessun linguaggio da scommessa in R2. Il vincolo 3 non e' aggirabile."""
    src = (config.ROOT / "sot" / "esiti.py").read_text(encoding="utf-8").lower()
    for vietato in ("odds", "quota_decimale", "payout", "bankroll", "kelly",
                    "stake", "profitto", "roi", "edge_scommessa"):
        assert vietato not in src, f"vincolo 3: trovato {vietato!r}"


def test_r2_non_stima_parametri_nuovi():
    src = (config.ROOT / "sot" / "esiti.py").read_text(encoding="utf-8")
    for vietato in ("minimize", "curve_fit", "TeamModel", "walkforward_predict"):
        assert vietato not in src, f"R2 non stima: trovato {vietato!r}"


def test_le_linee_sono_dichiarate_non_scelte():
    """Vincolo 1 applicato a una soglia, come per l'80' e per le soglie di E1."""
    src = (config.ROOT / "sot" / "esiti.py").read_text(encoding="utf-8")
    assert "LINEE = (1.5, 2.5, 3.5)" in src
    for vietato in ("argmax", "idxmax", "quantile(" ):
        assert vietato not in src.replace("pd.qcut", ""), (
            f"le linee non vanno ricavate dai dati: trovato {vietato!r}")


def test_nessun_numero_pubblicato_e_cambiato():
    from sot import difesa

    assert len(difesa.walkforward_gol()) == 3478
    p = PM.partite()
    assert int(p["validabile"].sum()) == 1638
