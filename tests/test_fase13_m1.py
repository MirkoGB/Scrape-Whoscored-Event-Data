# -*- coding: utf-8 -*-
"""Fase 13 / M1 — le metriche avanzate da dati evento.

Due famiglie di test, e la prima non tocca i dati veri: la **partizione delle
zone** e' una proprieta' geometrica e va provata su tutto il campo, non solo sui
punti che la Serie A 2025-26 ha prodotto. Un buco in un angolo che nessun tocco
ha mai visitato resterebbe invisibile sui dati veri e comparirebbe su un altro
campionato — cioe' esattamente dove la Fase 13 sta andando.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import features, metriche_evento as ME


# --------------------------------------------------------------------------
# La partizione, provata sulla geometria e non sul campione
# --------------------------------------------------------------------------
def _griglia(passo: float = 0.5) -> pd.DataFrame:
    a = np.arange(0.0, 100.0 + passo / 2, passo)
    xx, yy = np.meshgrid(a, a)
    return pd.DataFrame({"x": xx.ravel(), "y": yy.ravel()})


def test_zone_partizionano_tutto_il_campo():
    """Ogni punto del campo cade in ESATTAMENTE una zona.

    Se due zone si sovrapponessero i tocchi si conterebbero due volte; se
    lasciassero un buco le quote non sommerebbero a 1.
    """
    g = _griglia()
    z = ME.zona(g["x"], g["y"])
    assert z.notna().all(), "esistono punti senza zona"
    assert set(z.unique()) == set(ME.ZONE), set(z.unique()) ^ set(ME.ZONE)


def test_ogni_zona_e_non_vuota_e_contigua_in_x():
    """Nessuna zona e' vuota, e le tre fasce centrali sono ordinate in x.

    Una zona vuota vorrebbe dire una soglia sbagliata che la partizione da sola
    non vedrebbe: la partizione regge anche se una zona non contiene niente.
    """
    g = _griglia()
    g["z"] = ME.zona(g["x"], g["y"])
    conte = g["z"].value_counts()
    for z in ME.ZONE:
        assert conte.get(z, 0) > 0, f"zona vuota: {z}"

    x_med = g.groupby("z")["x"].mean()
    assert x_med["area_dif"] < x_med["terzo_dif"] < x_med["terzo_medio"] \
        < x_med["terzo_off"] < x_med["area_off"]


@pytest.mark.parametrize("x,y,atteso", [
    (5.0, 50.0, "area_dif"),      # dentro la propria area
    (5.0, 5.0, "terzo_dif"),      # stesso x, fuori dalla banda y: NON e' area
    (50.0, 50.0, "terzo_medio"),
    (95.0, 50.0, "area_off"),     # dentro l'area avversaria
    (95.0, 95.0, "terzo_off"),    # stesso x, fuori banda y
    (70.0, 50.0, "terzo_off"),
])
def test_punti_notevoli(x, y, atteso):
    """La banda `y` conta quanto la `x`: un punto sul fondo NON e' in area."""
    z = ME.zona(pd.Series([x]), pd.Series([y]))
    assert z.iloc[0] == atteso


def test_geometria_non_duplicata():
    """Le costanti dell'area si IMPORTANO da `features`, non si riscrivono.

    L'area di rigore del progetto e' una sola, per la stessa ragione per cui la
    definizione di tiro in porta sta solo in `shots.py`. Un secondo 84.29
    scritto a mano si sfaserebbe al primo che ne cambia uno solo.
    """
    src = Path(ME.__file__).read_text(encoding="utf-8")
    albero = ast.parse(src)
    importa_da_features = any(
        isinstance(n, ast.ImportFrom) and n.module and "features" in n.module
        for n in ast.walk(albero)
    )
    assert importa_da_features
    assert ME.BOX_X_DIFENSIVO == pytest.approx(100.0 - features.BOX_X)
    # e le costanti importate non sono state ridefinite nel modulo
    nomi_riassegnati = {
        t.id
        for n in ast.walk(albero) if isinstance(n, ast.Assign)
        for t in n.targets if isinstance(t, ast.Name)
    }
    for c in ("BOX_X", "BOX_Y_LO", "BOX_Y_HI", "FINAL_THIRD_X"):
        assert c not in nomi_riassegnati, f"{c} ridefinita invece che importata"


# --------------------------------------------------------------------------
# Le soglie sono dichiarate PRIMA, non ricavate dal campione
# --------------------------------------------------------------------------
def test_soglie_sono_letterali_e_non_scelte_sui_dati():
    """Vincolo 1 applicato a una soglia, come gia' per l'80' (Fase 8), le
    `SOGLIA_*` di E1 e le `LINEE_TIRI` di V0.

    Una soglia scelta col massimo di una griglia sul campione su cui poi la si
    valuta e' un iperparametro adattato al bersaglio.
    """
    src = Path(ME.__file__).read_text(encoding="utf-8")
    albero = ast.parse(src)
    # si guarda il CODICE, non la prosa: docstring e commenti sono esclusi
    # perche' spiegare perche' una cosa NON si fa non va punito (lezione V0).
    vietati = {"argmax", "idxmax", "quantile", "minimize", "curve_fit"}
    trovati = {
        n.attr if isinstance(n, ast.Attribute) else n.id
        for n in ast.walk(albero)
        if isinstance(n, ast.Attribute) or isinstance(n, ast.Name)
    }
    assert not (trovati & vietati), trovati & vietati

    assert ME.SOGLIA_PROGRESSIVO_M == 10.0
    assert ME.RAGGIO_PROFONDO_M == 20.0
    assert ME.CAMPO_M == (105.0, 68.0)


def test_conversione_metri_coerente_col_campo_dichiarato():
    """La soglia dei 10 m e' NOMINALE: poggia sul campo 105x68 assunto."""
    assert ME.M_PER_X == pytest.approx(1.05)
    assert ME.M_PER_Y == pytest.approx(0.68)
    # 10 m in unita' Opta di x
    assert ME.SOGLIA_PROGRESSIVO_M / ME.M_PER_X == pytest.approx(9.5238, abs=1e-4)


# --------------------------------------------------------------------------
# I progressivi su dati costruiti, dove la risposta e' nota
# --------------------------------------------------------------------------
def _ev(righe):
    df = pd.DataFrame(righe)
    df["isTouch"] = True
    return df


def test_progressivi_su_casi_noti():
    """Quattro passaggi scelti, un esito atteso ciascuno.

    **`prog_per_distanza` non richiede la riuscita**, ed e' voluto: e' la
    lettura "lunghezza >= 10 m e diretto in avanti", che sui dati veri da'
    231,57 per squadra-partita. La riuscita entra solo nella lettura scelta
    dall'utente (`prog_riusciti`). Tenere le tre colonne separate serve
    esattamente a non dover scegliere qui.
    """
    ev = _ev([
        # dx = +10.5 m, riuscito -> tentato, riuscito, e anche per distanza
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Successful",
             x=10, y=50, endX=20, endY=50),
        # stessa geometria ma fallito -> tentato e per distanza, NON riuscito
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Unsuccessful",
             x=10, y=50, endX=20, endY=50),
        # lungo 13.6 m ma tutto laterale: avanzamento 0 -> nessuna delle tre
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Successful",
             x=10, y=20, endX=10, endY=40),
        # dx = +2.1 m, lungo 14.4 m in diagonale -> SOLO per distanza
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Successful",
             x=10, y=20, endX=12, endY=41),
    ])
    g = ME.progressione(ev).iloc[0]
    assert g["prog_tentati"] == 2       # i due da +10.5 m
    assert g["prog_riusciti"] == 1      # di quelli, il solo riuscito
    assert g["prog_per_distanza"] == 3  # i due sopra + il diagonale


def test_riusciti_sono_un_sottoinsieme_dei_tentati(events):
    """`prog_riusciti <= prog_tentati` su ogni riga: e' un vincolo logico."""
    g = ME.progressione(events)
    assert (g["prog_riusciti"] <= g["prog_tentati"]).all()
    assert (g["passaggi_riusciti"] <= g["passaggi"]).all()


def test_le_tre_letture_sono_grandezze_DIVERSE(events):
    """Se coincidessero, tenerle separate sarebbe teatro.

    Il vincolo 7 dice di non fondere due definizioni finche' non e' misurato che
    siano la stessa cosa: qui si misura che NON lo sono.
    """
    g = ME.progressione(events)
    assert not g["prog_tentati"].equals(g["prog_riusciti"])
    assert not g["prog_tentati"].equals(g["prog_per_distanza"])
    # e i livelli medi stanno nell'ordine misurato, con margine ampio
    assert g["prog_riusciti"].mean() < g["prog_tentati"].mean() \
        < g["prog_per_distanza"].mean()


def test_ingresso_in_area_non_conta_gli_scarichi_interni():
    """Un passaggio DENTRO l'area non e' un ingresso in area."""
    ev = _ev([
        # da fuori a dentro -> ingresso
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Successful",
             x=70, y=50, endX=90, endY=50),
        # gia' dentro, resta dentro -> NON ingresso
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Successful",
             x=88, y=45, endX=92, endY=55),
        # da fuori a dentro ma fallito -> NON ingresso
        dict(matchId=1, teamId=1, type="Pass", outcomeType="Unsuccessful",
             x=70, y=50, endX=90, endY=50),
    ])
    assert ME.progressione(ev).iloc[0]["ingressi_area"] == 1


# --------------------------------------------------------------------------
# Il vincolo 7 sulle due derivazioni di "riuscito"
# --------------------------------------------------------------------------
def test_passAccurate_e_un_sottoinsieme_stretto_di_successful(events):
    """La ragione per cui si usa `outcomeType` e non `passAccurate`.

    Se un giorno `accurate_ma_non_successful` smettesse di essere zero, le due
    colonne non sarebbero piu' annidate e la scelta andrebbe rifatta.
    """
    v = ME.verifica_definizioni_riuscito(events)
    assert v["accurate_ma_non_successful"] == 0
    assert v["successful_ma_non_accurate"] > 0
    assert v["outcometype_e_completa"]
    # i non marcati sono piu' LUNGHI: e' il motivo per cui scartarli sarebbe
    # un errore sistematico proprio sulla popolazione dei progressivi
    assert v["lunghezza_media_senza_flag"] > v["lunghezza_media_con_flag"]


# --------------------------------------------------------------------------
# La tabella finale sui dati veri
# --------------------------------------------------------------------------
def test_una_riga_per_squadra_partita(events):
    m = ME.metriche_evento(events)
    assert len(m) == 760
    assert not m.duplicated(subset=["matchId", "teamId"]).any()
    assert m["matchId"].nunique() == 380
    assert (m.groupby("matchId").size() == 2).all()


def test_quote_per_zona_sommano_a_uno(events):
    m = ME.metriche_evento(events)
    q = m[[f"quota_tocchi_{z}" for z in ME.ZONE]].sum(axis=1)
    assert np.allclose(q.dropna(), 1.0)


def test_verifica_partizione_sui_dati_veri(events):
    v = ME.verifica_partizione(events)
    assert v["senza_zona"] == 0
    assert v["quote_sommano_a_1"]
    assert sorted(v["zone_osservate"]) == sorted(ME.ZONE)


def test_il_numero_scelto_dall_utente_e_riproducibile(events):
    """`prog_riusciti` ~ 88,9 per squadra-partita sulla 2025-26.

    E' il numero su cui l'utente ha preso la decisione del 2026-08-14: se si
    muovesse, la decisione sarebbe stata presa su un'altra grandezza.
    """
    g = ME.progressione(events)
    assert g["prog_riusciti"].mean() == pytest.approx(88.89, abs=0.05)
    assert g["prog_tentati"].mean() == pytest.approx(137.81, abs=0.05)
    assert g["prog_per_distanza"].mean() == pytest.approx(231.57, abs=0.05)


def test_nessuna_squadra_partita_sparisce(events):
    """Il join e' `outer`: una riga senza passaggi validi resta con zero.

    E' la trappola di V0 — ricostruire l'universo dai soli tiri fa sparire dal
    denominatore le squadre-partita con zero tiri, che esistono davvero.
    """
    ev = events[events["matchId"] == events["matchId"].iloc[0]]
    squadre = set(ev["teamId"].unique())
    # si tolgono TUTTI i passaggi di una delle due squadre
    vittima = sorted(squadre)[0]
    mutilato = ev[~((ev["teamId"] == vittima) & (ev["type"] == "Pass"))]
    m = ME.metriche_evento(mutilato)
    assert set(m["teamId"]) == squadre, "una squadra e' sparita dal denominatore"


def test_il_modulo_non_stima_niente():
    """M1 conta e misura, come R0 e V0. Nessun fit, nessun iperparametro."""
    src = Path(ME.__file__).read_text(encoding="utf-8")
    albero = ast.parse(src)
    nomi = {
        n.attr if isinstance(n, ast.Attribute) else n.id
        for n in ast.walk(albero)
        if isinstance(n, (ast.Attribute, ast.Name))
    }
    assert not (nomi & {"fit", "TeamModel", "Ridge", "GLM", "predict"})


def test_deep_completion_e_dichiarata_diversa_dallo_standard():
    """Il nome della colonna dice cio' che contiene.

    La definizione standard esclude i cross; in `events_slim` non c'e' nessun
    flag di cross, quindi la colonna NON puo' chiamarsi `deep_completions`.
    E' `passFreekick` (E4) applicato in anticipo: un nome che promette piu' di
    cio' che c'e' dentro produce una tabella dell'ordine di grandezza giusto e
    del contenuto sbagliato.
    """
    g_cols = ME.progressione.__doc__ or ""
    assert "completamenti_profondi_cross_inclusi" in inspect.getsource(ME)
    assert "deep_completions" not in inspect.getsource(ME).replace(
        "`deep_completions`", "")
