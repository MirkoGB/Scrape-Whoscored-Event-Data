# -*- coding: utf-8 -*-
"""Lega, fantavoto di lega, listone e modello per l'asta.

Il test che conta di piu' e' quello di **leakage**: la previsione della stagione
`t` non deve muoversi di un bit se si guastano i dati della stagione `t` stessa.
E' la forma meccanica del vincolo 1, la stessa gia' usata in
`tests/test_validate.py` per `walkforward_r`, ed e' l'unico modo di verificare
che medie di ruolo, pesi di shrinkage e storia del singolo vengano davvero dal
solo passato.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from acquisition.fantacalcio import pagina as P
from sot import (config, fantapunti as FP, lega as L,
                 modello_asta as MA, quotazioni as Q, voti as V)


# --------------------------------------------------------------------------
# 1. La configurazione di lega
# --------------------------------------------------------------------------

def test_le_fasce_coprono_la_retta_senza_buchi_ne_sovrapposizioni():
    """E' un invariante, non un controllo di stile (§2.1).

    Le fasce dichiarate nel documento prima della decisione 0.1 avevano tutti e
    tre i difetti insieme: 6.75 stava in due fasce, 7.00 esatto in nessuna, e
    cinque fasce davano tre bonus distinti.
    """
    for media in np.arange(0.0, 11.01, 0.01):
        dentro = [f for f in L.FASCE if f.contiene(float(media))]
        assert len(dentro) == 1, (media, dentro)
    # e la copertura vale anche fuori dal dominio dei voti
    assert L.modificatore(-5.0) == -1.0
    assert L.modificatore(1000.0) == +6.0


def test_le_soglie_sono_quelle_decise():
    """`[DECISO 0.1 — 2026-08-03]`. Se cambiano, cambia il valore di ogni
    difensore, e va fatto di proposito."""
    assert L.modificatore(5.99) == -1.0
    assert L.modificatore(6.00) == +1.0
    assert L.modificatore(6.49) == +1.0
    assert L.modificatore(6.50) == +3.0
    assert L.modificatore(6.99) == +3.0
    assert L.modificatore(7.00) == +6.0


def test_n_difensori_dipende_dal_modulo():
    """`[DECISO 0.2]`. Era la contraddizione (2) del Blocco 0: con un `n` fisso
    il test di coerenza di §3.2 sarebbe stato insoddisfacibile per costruzione."""
    assert L.Modulo("3-5-2").n_difensori_modificatore == 3
    assert L.Modulo("4-4-2").n_difensori_modificatore == 4
    assert L.Modulo("5-3-2").n_difensori_modificatore == 5
    assert L.LEGA.difensori_schierabili == {3, 4, 5}


def test_la_rosa_puo_schierare_ogni_modulo_ammesso():
    """L'invariante che §3.2 pretende, e che ora e' soddisfacibile."""
    L.LEGA.verifica()
    for m in L.LEGA.moduli:
        d, c, a = m.reparti
        assert d <= L.LEGA.difensori and c <= L.LEGA.centrocampisti
        assert a <= L.LEGA.attaccanti


def test_una_rosa_che_non_regge_un_modulo_e_rifiutata():
    with pytest.raises(ValueError, match="non e' schierabile"):
        L.Lega(difensori=4).verifica()


def test_senza_budget_il_confronto_non_e_definibile():
    with pytest.raises(ValueError, match="budget"):
        L.Lega(budget_asta=0).verifica()


def test_il_barema_di_lega_non_e_quello_della_fonte():
    """Vincolo 7. Le due differiscono per la porta inviolata, e la differenza e'
    misurata altrove su dati veri: qui si verifica che restino due oggetti."""
    assert "porta_inviolata" in L.BONUS
    assert "porta_inviolata" not in P.BAREME_FONTE
    assert "player_of_the_match" in L.FUORI_DAL_FANTAVOTO
    for voce in ("gol_segnati", "assist", "ammonizione", "espulsione"):
        assert L.BONUS[voce] == P.BAREME_FONTE[voce]


# --------------------------------------------------------------------------
# 2. Il fantavoto di lega, sui dati veri
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def voti_lega():
    return FP.con_fantavoto_lega()


def test_diverge_dalla_fonte_solo_sulle_porte_inviolate(voti_lega):
    """La verifica piu' forte di questo blocco: la divergenza prevista e'
    esattamente +1, solo ai portieri, solo a gol subiti zero. Se comparisse
    altrove, o il barema di lega e' scritto male o quello della fonte e'
    cambiato."""
    s = FP.scarto_dalla_fonte(voti_lega)
    assert len(s) > 500
    assert set(s["scarto"].unique()) == {1.0}
    assert set(s["ruolo"].unique()) == {"p"}
    assert s["porta_inviolata"].all()
    assert (s["gol_subiti"] == 0).all()


def test_un_sv_non_produce_punti(voti_lega):
    """Uno zero al posto di un nullo entrerebbe in ogni media come se fosse una
    prestazione."""
    sv = voti_lega[voti_lega["voto_redazione"].isna()]
    assert len(sv) > 4000
    assert sv["fantavoto_lega"].isna().all()
    assert sv["bonus_lega"].isna().all()
    assert not sv["porta_inviolata"].any()


def test_la_porta_inviolata_e_solo_del_portiere(voti_lega):
    assert (voti_lega.loc[voti_lega["porta_inviolata"], "ruolo"] == "p").all()


# --------------------------------------------------------------------------
# 3. Il listone
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def quote():
    return Q.carica()


def test_cinque_listoni(quote):
    assert set(quote["stagione"]) == set(config.SEASONS_STORICHE)
    assert (quote.groupby("stagione").size() > 600).all()


def test_il_fvm_mancante_resta_nullo_e_non_diventa_zero(quote):
    """La 2021-22 non pubblica il FVM: la fonte scrive `-`. Uno zero direbbe che
    quei giocatori valgono niente, che e' un'altra affermazione."""
    prima = quote[quote["stagione"] == "2021-2022"]
    assert prima["fvm_classic"].isna().all()
    dopo = quote[quote["stagione"] != "2021-2022"]
    assert dopo["fvm_classic"].notna().mean() > 0.99


def test_l_aggancio_col_listone_non_passa_dai_nomi(quote):
    """E' l'unico posto della Fase 8 in cui due tabelle condividono davvero una
    chiave: stessa fonte, stesso dizionario di id."""
    v = V.carica()
    v = v[(~v["allenatore"]) & (v["stagione"] == config.SEASON)]
    ids_voti = set(v["giocatore_id"].dropna().astype(int))
    ids_listone = set(quote[quote["stagione"] == config.SEASON]["giocatore_id"])
    assert len(ids_voti & ids_listone) > 500


def test_un_quotato_senza_presenze_ha_zero_e_non_un_nullo(quote):
    e = Q.con_esito(quote)
    mai = e[e["in_campo"] == 0]
    assert len(mai) > 300
    assert (mai["presenze"] == 0).all()
    assert (mai["gol"] == 0).all()


# --------------------------------------------------------------------------
# 4. Il modello, e il leakage
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def per_stagione(voti_lega):
    return FP.per_giocatore_stagione(voti_lega)


@pytest.fixture(scope="module")
def wf(per_stagione, quote):
    return MA.walkforward(per_stagione, quote)


def test_la_previsione_non_guarda_la_stagione_che_prevede(per_stagione, quote):
    """**Il test che conta.** Si guasta la stagione bersaglio e si pretende che
    la previsione non si muova di un bit; poi si guasta una stagione precedente
    e si pretende che si muova. Il primo controllo da solo passerebbe anche se il
    modello ignorasse tutto: il secondo e' quello che lo rende informativo.
    """
    bersaglio = "2024-2025"
    base = MA.previsione(bersaglio, per_stagione, quote)["punti_previsti"]

    guasta_futuro = per_stagione.copy()
    m = guasta_futuro["stagione"] >= bersaglio
    guasta_futuro.loc[m, ["punti_stagione", "presenze", "voto_medio", "bonus_totale"]] *= 3.0
    dopo = MA.previsione(bersaglio, guasta_futuro, quote)["punti_previsti"]
    pd.testing.assert_series_equal(base, dopo)

    guasta_passato = per_stagione.copy()
    m = guasta_passato["stagione"] < bersaglio
    guasta_passato.loc[m, "presenze"] = 1.0
    diverso = MA.previsione(bersaglio, guasta_passato, quote)["punti_previsti"]
    assert not np.allclose(base.to_numpy(), diverso.to_numpy())


def test_la_prima_stagione_non_e_valutabile(per_stagione, quote):
    with pytest.raises(ValueError, match="non ha stagioni precedenti"):
        MA.previsione(config.SEASONS_STORICHE[0], per_stagione, quote)


def test_quattro_transizioni_e_l_universo_e_il_listone(wf, quote):
    assert set(wf["stagione_prevista"]) == set(MA.STAGIONI_VALUTABILI)
    for stagione, blocco in wf.groupby("stagione_prevista"):
        assert len(blocco) == (quote["stagione"] == stagione).sum()


def test_chi_non_ha_giocato_vale_zero_non_nullo(wf):
    """E' il rischio che l'asta paga, e va previsto — non escluso."""
    mai = wf[wf["presenze_osservate"] == 0]
    assert len(mai) > 300
    assert (mai["punti_osservati"] == 0).all()


def test_il_baseline_che_non_sa_niente_deve_andare_a_caso(wf):
    """Il difetto che questa suite ha trovato davvero.

    Il listone arriva ordinato per `QI` decrescente. Con i pari merito sciolti
    nell'ordine della tabella, il baseline "media di ruolo" — costante dentro un
    ruolo — sceglieva in silenzio i giocatori piu' cari e otteneva la precisione
    di QI. Il confronto era falsato **in favore dell'ignoranza**.
    """
    prec = MA.precisione_top(wf)
    media = prec.groupby("candidato")["precisione"].mean()
    assert media["media di ruolo"] < 0.10
    assert media["modello"] > 2 * media["media di ruolo"]


def test_il_risultato_negativo_contro_fvm_e_riportato(wf):
    """Non e' un test di qualita' del modello: e' un test che il **fatto** resti
    visibile. Se un domani qualcuno facesse salire il modello sopra il FVM, va
    fatto cambiando il modello — e allora questo test va aggiornato con una
    misura nuova, non cancellato per comodita'.
    """
    m = MA.metriche(wf)
    tutte = m[m["stagione"] == "tutte"].set_index("candidato")
    assert tutte.loc["FVM della fonte", "spearman"] > tutte.loc["modello", "spearman"]
    assert tutte.loc["modello", "spearman"] > tutte.loc["media di ruolo", "spearman"]


def test_mae_e_bias_non_si_calcolano_fra_scale_diverse(wf):
    """QI e FVM sono crediti, i punti sono punti: un MAE fra i due sarebbe un
    numero senza significato, e resta `NaN` invece di essere stampato."""
    m = MA.metriche(wf).set_index(["stagione", "candidato"])
    for nome in ("quotazione iniziale QI", "FVM della fonte"):
        assert pd.isna(m.loc[("tutte", nome), "mae"])
        assert pd.notna(m.loc[("tutte", nome), "spearman"])


def test_le_presenze_sono_il_fattore_che_domina_l_errore(wf):
    """Il risultato piu' utile del blocco: conoscere le presenze abbatte il MAE
    di oltre l'80%, conoscere i bonus quasi per niente."""
    s = MA.scomposizione_errore(wf).set_index("variante")
    assert s.loc["presenze note", "mae"] < 0.2 * s.loc["modello completo", "mae"]
    assert s.loc["bonus noti", "mae"] > 0.5 * s.loc["modello completo", "mae"]


def test_il_modificatore_non_entra_nei_punti():
    """Non e' decomponibile per giocatore (§2.2), quindi non puo' stare in una
    colonna per riga — e infatti il modulo non lo importa affatto."""
    src = (config.ROOT / "sot" / "modello_asta.py").read_text(encoding="utf-8")
    assert "modificatore(" not in src
    src_fp = (config.ROOT / "sot" / "fantapunti.py").read_text(encoding="utf-8")
    assert "modificatore(" not in src_fp


# --------------------------------------------------------------------------
# 5. Il modificatore di difesa
# --------------------------------------------------------------------------

from sot import modificatore as MOD  # noqa: E402


@pytest.fixture(scope="module")
def previsione_2627(per_stagione, quote):
    listone = MA.listone_surrogato("2026-2027", config.SEASON, quote)
    return MA.previsione("2026-2027", per_stagione, listone)


def test_la_decisione_03_e_escludi_e_il_meccanismo_resta():
    """La 0.3 e' decisa, ma la guardia che fermava il codice **non si toglie**:
    e' il modo in cui una prossima voce `[DA DECIDERE]` fara' fallire il codice
    invece di prendere un default."""
    assert L.gestione_sv() == "escludi"
    vecchio = L.GESTIONE_SV
    try:
        L.GESTIONE_SV = None
        with pytest.raises(L.DecisioneMancante, match="0.3"):
            L.gestione_sv()
        L.GESTIONE_SV = "inventato"
        with pytest.raises(ValueError):
            L.gestione_sv()
    finally:
        L.GESTIONE_SV = vecchio


def test_una_linea_perfetta_prende_sempre_la_fascia_alta():
    """Controllo su un caso in cui la risposta e' nota: se tutti prendono voto
    e valgono 8, la media e' 8 e il bonus e' +6 in ogni giornata."""
    n = 5
    b = MOD.simula_linea(np.full(n, 8.0), np.full(n, 1e-9), np.ones(n),
                         repliche=50)
    assert np.allclose(b, 6.0)


def test_una_linea_disastrosa_prende_sempre_il_malus():
    n = 4
    b = MOD.simula_linea(np.full(n, 4.0), np.full(n, 1e-9), np.ones(n),
                         repliche=50)
    assert np.allclose(b, -1.0)


def test_se_nessuno_prende_voto_il_bonus_e_zero_non_il_malus():
    """Il caso limite dichiarato: assenza di media non e' media bassa."""
    n = 4
    b = MOD.simula_linea(np.full(n, 4.0), np.full(n, 0.5), np.zeros(n),
                         repliche=50)
    assert np.allclose(b, 0.0)


def test_escludi_alza_la_media_quando_il_peggiore_salta():
    """`escludi` non e' neutro, ed e' il punto della decisione 0.3.

    Una linea con tre da 7 e uno da 4: se il quarto prende sempre voto la media
    e' 6,25, cioe' fascia **+1**; se non la prende mai la media e' 7,0, cioe'
    fascia **+6**. Cinque punti di differenza per giornata, dal solo fatto che
    il peggiore non e' stato giudicato.
    """
    mu = np.array([7.0, 7.0, 7.0, 4.0])
    sd = np.full(4, 1e-9)
    sempre = MOD.simula_linea(mu, sd, np.ones(4), repliche=50).mean()
    mai = MOD.simula_linea(mu, sd, np.array([1.0, 1.0, 1.0, 0.0]), repliche=50).mean()
    assert sempre == pytest.approx(1.0)
    assert mai == pytest.approx(6.0)


def test_il_voto_simulato_sta_sulla_griglia_dei_mezzi_punti():
    """Vicino alle soglie la griglia decide la fascia: simulare su un continuo
    darebbe medie diverse proprio dove conta."""
    x = MOD._arrotonda(np.array([6.24, 6.26, 6.74, 0.1, 99.0]))
    assert set(np.unique(x * 2) % 1) == {0.0}
    assert x.min() >= MOD.VOTO_MIN and x.max() <= MOD.VOTO_MAX


def test_la_simulazione_e_riproducibile():
    a = MOD.simula_linea(np.full(4, 6.2), np.full(4, 0.5), np.full(4, 0.8), repliche=100)
    b = MOD.simula_linea(np.full(4, 6.2), np.full(4, 0.5), np.full(4, 0.8), repliche=100)
    assert np.array_equal(a, b)


def test_la_linea_di_riferimento_e_dichiarata_e_cambia_i_contributi(previsione_2627):
    """§2.2: lo stesso giocatore ha contributi diversi rispetto a linee diverse,
    quindi un contributo senza la sua linea e' incompleto."""
    with pytest.raises(ValueError):
        MOD.linea_riferimento(previsione_2627, 4, universo="inventato")
    a = MOD.linea_riferimento(previsione_2627, 4, "schierabili")
    b = MOD.linea_riferimento(previsione_2627, 4, "tutti i quotati")
    # il mediano dei quotati e' un panchinaro: gioca molto meno
    assert a["p_voto"][1] > b["p_voto"][1]
    assert a["mu"][1] > b["mu"][1]


def test_il_contributo_e_per_modulo_e_non_una_media(previsione_2627):
    """Decisione 0.2: `n_difensori` dipende dal modulo, quindi lo stesso
    difensore ha tre contributi e schiacciarli nasconderebbe l'effetto."""
    c = MOD.contributo_marginale(previsione_2627, repliche=200)
    assert set(c["n_difensori"]) == L.LEGA.difensori_schierabili
    assert set(c["ruolo"]) == {"p", "d"}
    per_gioc = c.groupby("giocatore_id")["contributo_stagione"].nunique()
    assert (per_gioc > 1).mean() > 0.9
    assert "universo" in c.columns


def test_la_media_di_stagione_sbaglia_in_entrambe_le_direzioni(previsione_2627):
    """La misura che §2.2 chiede esplicitamente. Se i due coincidessero, tutta
    la simulazione sarebbe lavoro sprecato — e invece il segno dipende dalla
    linea, che e' il motivo per cui la scorciatoia e' vietata."""
    a = MOD.costo_della_media(previsione_2627, 4, repliche=400,
                              universo="schierabili")["scarto_di_stagione"].iloc[0]
    b = MOD.costo_della_media(previsione_2627, 4, repliche=400,
                              universo="tutti i quotati")["scarto_di_stagione"].iloc[0]
    assert a < 0 < b
    assert abs(a) > 5 and abs(b) > 5


# --------------------------------------------------------------------------
# 6. Il listone surrogato
# --------------------------------------------------------------------------

def test_il_surrogato_dichiara_di_esserlo(quote):
    s = MA.listone_surrogato("2026-2027", config.SEASON, quote)
    assert (s["stagione"] == "2026-2027").all()
    assert (s["stagione_listone"] == config.SEASON).all()
    # i prezzi restano, ma con un nome che dice di quale anno sono
    assert "qi_anno_prima" in s.columns and "fvm_anno_prima" in s.columns
    assert len(s) == (quote["stagione"] == config.SEASON).sum()


def test_il_surrogato_di_una_stagione_inesistente_fallisce(quote):
    with pytest.raises(ValueError, match="nessun listone"):
        MA.listone_surrogato("2026-2027", "2019-2020", quote)


def test_la_lista_dasta_non_ha_una_colonna_crediti():
    """Convertire punti in crediti e' un problema di allocazione con budget, non
    una proporzione (§2.2). Una colonna di zeri sarebbe un segnaposto."""
    src = (config.ROOT / "scripts" / "run_asta_2627.py").read_text(encoding="utf-8")
    # si vieta l'assegnazione, non la parola: il report ne parla apposta
    assert 'prev["crediti' not in src and '"crediti"' not in src
    lista = pd.read_csv(config.REPORTS / "asta_2627_lista.csv")
    assert not [c for c in lista.columns if "credit" in c]
