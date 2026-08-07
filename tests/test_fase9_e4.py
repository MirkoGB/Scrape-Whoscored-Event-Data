# -*- coding: utf-8 -*-
"""Test del blocco E4 — voto base, bonus, piazzati, rigori.

Girano dai Parquet gia' costruiti e dalla cache dei piazzati: non rileggono i
1.889 CSV, tranne i due test che devono farlo per verificare la collisione di
`passFreekick`, che leggono trenta partite. Non toccano la rete. Se i Parquet non
ci sono, i test che ne hanno bisogno si saltano invece di fallire.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, features_giocatore as FG, voto_bonus as VB

RADICE = Path(__file__).resolve().parent.parent

TUTTE = all(config.player_match(season=s).is_file()
            for s in config.SEASONS_STORICHE)
serve_parquet = pytest.mark.skipif(
    not TUTTE, reason="le cinque stagioni non sono state costruite")

C_PIAZZATI = VB.CACHE_PIAZZATI.is_file()
serve_piazzati = pytest.mark.skipif(
    not C_PIAZZATI, reason="manca il derivato dei piazzati: run_fase9_e4.py")


@pytest.fixture(scope="module")
def piazzati():
    return VB.piazzati()


@pytest.fixture(scope="module")
def tab():
    return VB.con_contesto()


# --------------------------------------------------------------------------
# 1. La collisione di `passFreekick` — il risultato metodologico del blocco
# --------------------------------------------------------------------------

@serve_parquet
def test_passfreekick_non_contiene_le_punizioni():
    """La colonna e' il corner. Tre affermazioni, e servono tutte e tre.

    Una sola lascerebbe aperta la lettura "e' un'altra definizione di
    punizione"; insieme dicono che la colonna e' il corner e basta.
    """
    c = VB.collisione_passfreekick().set_index("confronto")
    assert bool(c.loc["passFreekick == passCorner (riga per riga)", "identiche"])
    assert c.loc["passFreekick vs qualifier FreekickTaken", "in_comune"] == 0
    assert c.loc["passFreekick vs qualifier FreekickTaken", "b"] > 0, (
        "senza punizioni vere nel campione l'intersezione vuota non prova niente")
    assert bool(c.loc["passCorner vs qualifier CornerTaken", "identiche"])


def test_il_gate_da_solo_non_avrebbe_fermato_passfreekick():
    """E' il punto: un gate misura la stabilita', non il significato.

    Se un giorno `passFreekick` smettesse di passare il gate, questo test
    fallirebbe e sarebbe giusto: vorrebbe dire che l'argomento del report
    ("passa a pieni voti e nomina una grandezza che non contiene") non regge
    piu' e va riscritto.
    """
    g = VB.gate_colonne().set_index("colonna")
    assert bool(g.loc["passFreekick", "passa_il_gate"])
    assert bool(g.loc["passCorner", "passa_il_gate"])


def test_i_piazzati_non_si_leggono_dalle_colonne_omonime():
    """Nel sorgente, `passFreekick` compare solo dove si confronta, mai dove si
    conta: il conteggio pubblicato viene dal qualifier."""
    src = (RADICE / "sot" / "voto_bonus.py").read_text(encoding="utf-8")
    assert 'punizioni_battute=("q_punizione", "sum")' in src
    assert 'punizioni_colonna=("passFreekick", "sum")' in src, (
        "la colonna va comunque letta, per poter pubblicare la collisione")


# --------------------------------------------------------------------------
# 2. I pattern dei qualifier, e il perche' dell'apice di chiusura
# --------------------------------------------------------------------------

def test_ogni_pattern_identifica_un_solo_qualifier():
    """La guardia che rende sicura la ricerca per sottostringa."""
    v = VB.verifica_pattern()
    assert (v["identificati"] == 1).all()
    assert v["presente_nei_dati"].all()


def test_il_nome_nudo_collide_davvero_e_la_forma_completa_no():
    """Non e' una precauzione teorica: `IndirectFreekickTaken` esiste nei dati.

    Cercando il nome nudo, le punizioni indirette finirebbero dentro le dirette.
    La forma completa lo impedisce perche' pretende un apice **prima** del nome.
    """
    testo = "[{'type': 'IndirectFreekickTaken'}, {'type': 'Zone', 'value': 'C'}]"
    assert "FreekickTaken" in testo, "il nome nudo collide"
    assert VB._pattern("FreekickTaken") not in testo, "la forma completa no"
    assert VB._pattern("IndirectFreekickTaken") in testo


def test_i_qualifier_usati_passano_il_gate_di_e1():
    g = VB.gate_qualifier().set_index("qualifier")
    assert g["ammesso"].all(), f"non ammessi: {list(g.index[~g['ammesso']])}"
    assert (g["stagioni"] == len(config.SEASONS_STORICHE)).all()


# --------------------------------------------------------------------------
# 3. I rigori — due derivazioni indipendenti che devono concordare
# --------------------------------------------------------------------------

@serve_piazzati
def test_i_rigori_dal_qualifier_coincidono_con_le_booleane(piazzati):
    """E' la verifica piu' forte di E4.0 perche' non passa da nessun modello."""
    c = VB.coerenza_rigori(piazzati)
    assert (c["scarto"] == 0).all(), c[["stagione", "scarto"]].to_dict("records")
    assert (c["da_qualifier"] > 0).all()


@serve_piazzati
def test_il_qualifier_penalty_da_solo_conterebbe_quattro_volte_tanto(piazzati):
    """Se un domani qualcuno togliesse il filtro `isShot`, questo test lo vede.

    Il qualifier sta anche sul fallo di chi il rigore l'ha concesso e sul
    portiere che l'ha affrontato: il conteggio nudo e' ~4x quello vero.
    """
    c = VB.coerenza_rigori(piazzati)
    rapporto = c["qualifier_senza_isShot"] / c["da_qualifier"]
    assert (rapporto > 3).all(), rapporto.tolist()


@serve_piazzati
def test_la_conversione_dei_rigori_riproduce_la_fase_1(piazzati):
    """76,4% sulla 2025-26, gia' pubblicato dalla Fase 1."""
    c = VB.coerenza_rigori(piazzati).set_index("stagione")
    assert abs(float(c.loc["2025-2026", "conversione"]) - 0.764) < 0.005


@serve_piazzati
def test_i_corner_concordano_fra_qualifier_e_colonna(piazzati):
    """Il verso positivo della collisione: dove le due strade coincidono,
    coincidono esattamente. E' cio' che rende il disaccordo sulle punizioni
    attribuibile alla colonna e non al parsing dei qualifier."""
    c = VB.coerenza_corner(piazzati)
    assert (c["scarto_corner"] == 0).all()
    assert (c["scarto_punizioni"] > 0).all()


@serve_piazzati
def test_la_quadratura_non_passa_alla_lettera_e_va_detto(piazzati):
    """Il test dichiarato dalla specifica **fallisce**, e il report lo dice.

    Questo test blocca il fatto, non la speranza: se un giorno la distribuzione
    diventasse quella attesa, il report andrebbe riscritto.
    """
    q = VB.quadratura_rigoristi(piazzati).set_index("rigoristi")
    fino_a_due = float(q.loc[q.index <= 2, "quota"].sum())
    assert fino_a_due < 0.6, "la specifica si aspettava la grande maggioranza"

    q2 = VB.quadratura_rigoristi(piazzati, min_rigori=2).set_index("rigoristi")
    assert float(q2.loc[q2.index <= 2, "quota"].sum()) > 0.85, (
        "contando solo chi ne ha battuti almeno due, l'attesa torna")


@serve_piazzati
def test_il_designato_prende_poco_piu_della_meta_dei_rigori(piazzati):
    """E' il numero che E4.3 usa al posto di un'assegnazione secca."""
    s = VB.sintesi_concentrazione(VB.concentrazione_rigoristi(piazzati))
    quota = float(s["quota_primo_mediana"].iloc[0])
    assert 0.5 < quota < 0.7, quota


# --------------------------------------------------------------------------
# 4. I cinque fit di xG — la verifica rimandata due volte
# --------------------------------------------------------------------------

@serve_parquet
def test_i_cinque_fit_hanno_la_stessa_forma():
    """Le interazioni stagione x feature non migliorano fuori campione."""
    f = VB.differenza_fra_fit().set_index("disegno")
    assert f.loc["interazioni stagione x feature", "guadagno_su_intercetta"] <= 0


@serve_parquet
def test_i_cinque_fit_non_hanno_lo_stesso_livello():
    """15,8% di escursione, tre volte la soglia di E1.

    E' il motivo per cui npxG **non** si somma fra stagioni in unita' grezze, ed
    e' anche la spiegazione del verdetto che E1 aveva misurato su `xg_per_90`
    senza potersela dare.
    """
    s = VB.scale_dei_fit()
    escursione = float(s["escursione_relativa"].iloc[0])
    assert escursione > FG.SOGLIA_DERIVA, escursione
    # La forma quasi non si muove: i cinque ordinano i tiri allo stesso modo.
    # "Quasi" e' misurato e non arrotondato a uno — 0,986 non e' 1,000 — ed e'
    # il test fuori campione a dire che quel residuo non serve a prevedere.
    assert (s["corr_col_primo_fit"] > 0.98).all(), (
        "se la forma divergesse, 'sola intercetta' sarebbe falso")
    assert float(s["corr_col_primo_fit"].min()) < 1.0, (
        "una correlazione esattamente 1 vorrebbe dire che il test non guarda")


# --------------------------------------------------------------------------
# 5. Il divario di E4, che questo blocco ha corretto
# --------------------------------------------------------------------------

@serve_parquet
def test_il_numero_pubblicato_resta_riproducibile():
    """Il 52,50 non si cancella: si dice che cosa misurava."""
    from sot import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    s = MA.scomposizione_errore(MA.walkforward(per_stagione=ps), ps)
    s = s.set_index("variante")
    vecchia = 'tasso per presenza noto (era "bonus noti")'
    assert abs(float(s.loc[vecchia, "mae"]) - 52.50) < 0.01
    assert int(s.loc[vecchia, "righe"]) == 2204
    assert abs(float(s.loc["modello completo", "mae"]) - 61.42) < 0.01
    assert int(s.loc["modello completo", "righe"]) == 2678


@serve_parquet
def test_il_divario_dei_bonus_e_molto_piu_piccolo_di_quello_pubblicato():
    """8,9 punti erano campione che cambia piu' componente sbagliata.

    Sulle **stesse** righe il modello completo fa 55,01, non 61,42: il guadagno
    vero del tasso per presenza e' 2,51 punti.
    """
    from sot import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    s = MA.scomposizione_errore(MA.walkforward(per_stagione=ps), ps)
    s = s.set_index("variante")
    vecchia = 'tasso per presenza noto (era "bonus noti")'
    assert abs(float(s.loc[vecchia, "mae_stesse_righe"]) - 55.01) < 0.05
    assert float(s.loc[vecchia, "guadagno_vero"]) < 3.0
    assert float(s.loc["presenze note", "guadagno_vero"]) > 50.0, (
        "le presenze restano il problema, ed e' la cosa che non cambia")


@serve_parquet
def test_voto_e_bonus_sono_due_oracoli_diversi():
    """Costruiti per differenza darebbero lo stesso numero: e' l'identita' che
    ha fatto scoprire il difetto. Presi dalle componenti osservate, no."""
    from sot import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    s = MA.scomposizione_errore(MA.walkforward(per_stagione=ps), ps)
    s = s.set_index("variante")
    assert abs(float(s.loc["voto noto", "mae"])
               - float(s.loc["bonus noti", "mae"])) > 0.05


# --------------------------------------------------------------------------
# 6. Il leakage: che cosa puo' venire da t e che cosa no
# --------------------------------------------------------------------------

def test_ogni_feature_viene_da_t_meno_uno_tranne_le_dichiarate():
    """L'eccezione e' **enumerata**, non dedotta dal nome.

    Un nome che dicesse "noto all'asta" resterebbe vero anche mettendoci QA, e
    sarebbe falso: la guardia e' l'elenco.
    """
    tutte = set(VB.FEATURE_VOTO) | set(VB.FEATURE_BONUS) | set(VB.FEATURE_VOTO_QI)
    for c in tutte:
        assert c.endswith("_prec") or c in VB.COLONNE_DI_T_AMMESSE, c


def test_il_fvm_non_entra_da_nessuna_parte():
    """Il gate di `quotazioni` applicato al punto d'uso, non allo stile."""
    from sot import quotazioni as Q

    for c in VB.COLONNE_LISTONE_AMMESSE:
        assert c not in Q.COLONNE_CONTAMINATE
    src = (RADICE / "sot" / "voto_bonus.py").read_text(encoding="utf-8")
    assert "fvm" not in src.lower().replace("fvm_classic", "").replace(
        "il fvm", ""), "il FVM resta squalificato per l'intera Fase 9"


def test_nessuna_soglia_ricavata_dal_campione():
    """Vietati argmax/idxmax/quantile: le soglie di questo modulo sono
    dichiarate, come l'80' della presenza e le soglie di E1."""
    src = (RADICE / "sot" / "voto_bonus.py").read_text(encoding="utf-8")
    for vietato in ("argmax", "idxmax", ".quantile("):
        assert vietato not in src, vietato
    assert isinstance(VB.ALPHA, float)
    assert isinstance(VB.MIN_PRESENZE_ADDESTRAMENTO, int)
    assert isinstance(VB.SMORZAMENTO_CONVERSIONE, float)


@serve_parquet
def test_la_previsione_non_guarda_la_stagione_bersaglio(tab):
    """Si guasta una stagione di mezzo e si pretende che le previsioni
    precedenti non cambino e le successive si'."""
    from sot import fantapunti as FP

    oss = VB._bersagli(FP.per_giocatore_stagione())
    prima = VB.previsione("2023-2024", tab, oss, "voto_medio", VB.FEATURE_VOTO)
    dopo = VB.previsione("2025-2026", tab, oss, "voto_medio", VB.FEATURE_VOTO)

    guasto = oss.copy()
    sel = guasto["stagione"] == "2024-2025"
    guasto.loc[sel, "voto_medio"] = guasto.loc[sel, "voto_medio"] + 3.0

    prima2 = VB.previsione("2023-2024", tab, guasto, "voto_medio", VB.FEATURE_VOTO)
    dopo2 = VB.previsione("2025-2026", tab, guasto, "voto_medio", VB.FEATURE_VOTO)

    assert np.allclose(prima.to_numpy(), prima2.to_numpy(), equal_nan=True), (
        "guastare il 2024-25 ha cambiato una previsione del 2023-24: leakage")
    assert not np.allclose(dopo.to_numpy(), dopo2.to_numpy(), equal_nan=True), (
        "guastare il passato non ha cambiato il futuro: il test non guarda niente")


# --------------------------------------------------------------------------
# 7. Lo strato feature e i join
# --------------------------------------------------------------------------

@serve_parquet
def test_il_ponte_perde_righe_ma_non_minuti():
    """22% delle righe, 0,13% dei minuti: sono i convocati mai scesi in campo."""
    r = VB.residuo_ponte().iloc[0]
    assert r["quota_righe"] > 0.15
    assert r["quota_minuti"] < 0.01
    assert r["perse_a_zero_minuti"] / r["righe_perse"] > 0.95


@serve_parquet
def test_nessun_join_moltiplica_le_righe(tab):
    """Nessuna chiave disponibile e' unica (una collisione nota su 2,8 milioni
    di righe), quindi la cardinalita' si verifica invece di assumerla."""
    assert len(tab) == len(VB.tabella_e4())
    assert not tab.duplicated(["stagione", "giocatore_id"]).any()


@serve_parquet
def test_il_gate_di_e1_separa_le_candidate_nuove():
    """Cinque passano standardizzate, cinque restano irriducibili — e npxG e'
    fra queste, il che e' coerente con i 15,8% di escursione fra i fit."""
    d = VB.deriva_e4().set_index("candidata")
    assert d.loc["npxg_per_90", "verdetto"] == FG.VERDETTI[2]
    assert d.loc["xa_per_90", "verdetto"] == FG.VERDETTI[1]
    irr = set(d.index[d["verdetto"] == FG.VERDETTI[2]])
    dichiarate = {c.replace("_rel_prec", "") for c in VB.IRRIDUCIBILI}
    assert dichiarate <= irr, dichiarate - irr


# --------------------------------------------------------------------------
# 8. Gli esiti del blocco
# --------------------------------------------------------------------------

@serve_parquet
def test_le_feature_evento_non_aggiungono_niente(tab):
    """Tre varianti su tre negative, tutte dentro il rumore.

    E' il risultato del blocco e **non va sistemato**: il test blocca il segno e
    il fatto che nessuna superi la propria soglia.
    """
    r = VB.confronto(tab=tab)
    t = r["tabella"].set_index("variante")
    mde = r["mde"].set_index("variante")
    for nome in ("E4 voto base", "E4 bonus", "E4 voto + bonus"):
        assert t.loc[nome, "divario_chiuso_pct"] < 0, nome
        assert abs(mde.loc[nome, "t"]) < 2.0, nome


@serve_parquet
def test_qi_da_solo_e_l_unico_che_si_muove_ma_non_passa_bonferroni(tab):
    """Positivo e piccolo, e le due parole vanno tenute insieme.

    Passa la soglia a due code del 5% e **non** quella corretta per sei
    varianti (|t| > 2,64). Va riportato come suggestivo, non come risultato.
    """
    r = VB.confronto(tab=tab)
    mde = r["mde"].set_index("variante")
    t_qi = float(mde.loc["SOLO QI, senza le feature evento", "t"])
    assert t_qi > 1.96
    assert t_qi < 2.64, "se passasse Bonferroni, il report andrebbe riscritto"


@serve_parquet
def test_qi_da_solo_batte_qi_piu_le_feature_evento(tab):
    """Il contrasto con (b), dove QI da solo era PEGGIO del modello completo.

    Le feature evento qui non sono neutre: peggiorano.
    """
    t = VB.confronto(tab=tab)["tabella"].set_index("variante")
    assert (t.loc["SOLO QI, senza le feature evento", "divario_chiuso_pct"]
            > t.loc["E4 + QI", "divario_chiuso_pct"])


@serve_parquet
def test_gli_autogol_non_hanno_effetto_individuale(tab):
    """La specifica lo prevedeva; qui e' verificato invece che assunto."""
    a = VB.autogol_effetto_individuale(tab).set_index("modello")
    assert a.loc["ruolo + effetto individuale", "guadagno"] <= 0.001


@serve_parquet
def test_il_voto_e_quasi_tutto_dentro_il_giocatore():
    """Il tetto di E4.1: l'87-89% della varianza del voto non e' fra i
    giocatori, quindi nessun numero per giocatore puo' prenderla."""
    v = VB.varianza_del_voto().set_index("raggruppamento")
    assert float(v.loc["giocatore", "quota_fra"]) < 0.20
    assert float(v.loc["giocatore", "sd_entro"]) > float(
        v.loc["giocatore", "sd_fra"])


@serve_parquet
def test_spostare_il_designato_vale_piu_del_divario_medio(tab):
    """Sul singolo giocatore l'assegnazione discreta e' la decisione piu' pesante
    del blocco, anche se sulla media di 2.678 righe non si vede."""
    s = VB.sensibilita_designato(tab)
    assert float(s["spostamento"].max()) > 10.0


@serve_parquet
def test_la_conclusione_non_dipende_dalle_irriducibili(tab):
    """Le cinque candidate che E1 dichiara irriducibili entrano in forma `_rel`,
    che E1 dice insufficiente. Togliendole l'esito e' lo stesso, quindi la
    conclusione non poggia su quella scelta."""
    t = VB.confronto(tab=tab)["tabella"].set_index("variante")
    assert t.loc["E4 senza le irriducibili", "divario_chiuso_pct"] < 0
    assert t.loc["E4 voto + bonus", "divario_chiuso_pct"] < 0


# --------------------------------------------------------------------------
# 9. Il blocco non deve aver spostato niente di quello che c'era
# --------------------------------------------------------------------------

@serve_parquet
def test_i_numeri_di_e2_e_e3_sono_invariati():
    """E4 tocca `modello_asta.scomposizione_errore`: il resto deve non muoversi."""
    from sot import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    wf = MA.walkforward(per_stagione=ps)
    mae = float((wf["punti_previsti"] - wf["punti_osservati"]).abs().mean())
    assert abs(mae - 61.42) < 0.01
    assert len(wf) == 2678


def test_events_slim_non_e_stato_allargato():
    """E4 rilegge i CSV per conto proprio **apposta**: allargare `BOOL_COLS`
    avrebbe costretto a rivalidare ogni numero delle Fasi 1-6."""
    from sot import io_events

    for c in ("passCorner", "passFreekick", "passKey", "assist"):
        assert c not in io_events.ALL_COLS, c
    src = (RADICE / "sot" / "voto_bonus.py").read_text(encoding="utf-8")
    assert "build_cache" not in src


def test_le_72_colonne_mai_valorizzate_restano_fuori():
    """La garanzia non e' la disciplina ma l'impossibilita': nessuna delle
    colonne lette da E4 e' fra quelle che non portano mai un valore."""
    if not (RADICE / "data" / "processed").exists():
        pytest.skip("manca la ricognizione del Blocco 0")
    try:
        mai = FG.colonne_mai_valorizzate()
    except FileNotFoundError:
        pytest.skip("manca la ricognizione del Blocco 0")
    assert not (set(VB.COLONNE_LETTE) & mai)
