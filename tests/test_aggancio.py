# -*- coding: utf-8 -*-
"""Aggancio fra le due fonti e misura della regola dell'80'.

Due famiglie:

1. **le regole di normalizzazione dei nomi**, provate su casi costruiti in cui
   la risposta e' nota. Sono i 23 casi su 609 che il cognome grezzo sbaglia, e
   ognuno sta qui con il suo nome vero: se un giorno la traslitterazione si
   rompe, si rompe qui e non dentro un aggancio silenziosamente sbagliato;
2. **gli invarianti dell'aggancio sui dati veri** — biiezione, chiavi uniche,
   residui che coincidono con quelli gia' documentati dall'acquisizione.

La seconda famiglia gira sui dati del progetto, e sarebbe circolare se
verificasse il *risultato*. Verifica invece proprieta' strutturali che il
risultato deve avere qualunque esso sia: una squadra non puo' essere agganciata
a due, una partita non puo' avere due `matchId`, un giocatore dei voti non puo'
finire su due giocatori WhoScored.
"""

from __future__ import annotations

import pandas as pd
import pytest

from sot import aggancio as AG, config, presenza as PR


# --------------------------------------------------------------------------
# 1. I nomi
# --------------------------------------------------------------------------

@pytest.mark.parametrize("scritto,atteso", [
    ("Højlund", ["hojlund"]),
    ("Østigård", ["ostigard"]),
    ("Grønbæk", ["gronbaek"]),
    ("Løvik", ["lovik"]),
    ("Sørensen", ["sorensen"]),
    ("Éderson Silva", ["ederson", "silva"]),
    ("Nahuel Estévez", ["nahuel", "estevez"]),
    ("Thórir Helgason", ["thorir", "helgason"]),
])
def test_le_lettere_che_ascii_non_piega(scritto, atteso):
    """`ø` non e' una `o` con un segno sopra: e' un'altra lettera, e NFKD non la
    tocca. Senza la tabella di traslitterazione `Højlund` diventa `hjlund`."""
    assert AG._normalizza(scritto) == atteso


def test_gli_apostrofi_diventano_tutti_lo_stesso_separatore():
    """`N'Dri` e `N´Dri` sono la stessa persona scritta con due caratteri diversi.

    L'apostrofo tipografico della fonte dei voti e l'accento acuto usato da
    WhoScored non sono lo stesso codepoint, ma **finiscono entrambi in uno
    spazio**: il primo perche' lo sostituiamo, il secondo perche' `NFKD` lo
    decompone in spazio piu' segno combinante. Arrivano quindi alla stessa
    forma senza che serva una regola apposta, ed e' il motivo per cui il
    confronto sulla forma attaccata qui non e' nemmeno necessario.
    """
    assert AG._normalizza("N'Dri") == ["n", "dri"]
    assert AG._normalizza("Konan N´Dri") == ["konan", "n", "dri"]
    assert AG._candidati(["n", "dri"], {1: "Konan N´Dri"}) == [1]


def test_la_forma_attaccata_riconcilia_cio_che_i_separatori_dividono():
    """Serve quando una fonte scrive unito cio' che l'altra stacca."""
    assert AG._candidati(["de", "silvestri"], {1: "Lorenzo Desilvestri"}) == [1]


@pytest.mark.parametrize("nome,cognome,iniziali", [
    ("Martinez L.", ["martinez"], ["l"]),
    ("Martinez Jo.", ["martinez"], ["jo"]),
    ("Esposito F.P.", ["esposito"], ["f", "p"]),
    ("Pellegrini Lu.", ["pellegrini"], ["lu"]),
    ("Nicolussi Caviglia", ["nicolussi", "caviglia"], []),
    ("Ilicic", ["ilicic"], []),
])
def test_le_iniziali_si_riconoscono_dal_punto(nome, cognome, iniziali):
    """Non dalla lunghezza: `Jo.` e `Lu.` sono abbreviazioni di due lettere, e un
    criterio sulla lunghezza le confonderebbe con i cognomi corti veri."""
    assert AG._scomponi_fc(nome) == (cognome, iniziali)


def test_le_iniziali_disambiguano_invece_di_essere_buttate():
    """Il caso che ha fatto riscrivere la funzione.

    La versione che toglieva l'iniziale creava l'ambiguita' che poi avrebbe
    dovuto risolvere: `Martinez L.` e `Martinez Jo.` diventavano lo stesso
    `martinez`, con due candidati e nessun modo di sceglierne uno.
    """
    rosa = {1: "Lautaro Martínez", 2: "Josep Martínez"}
    assert AG._candidati(["martinez"], rosa) == [1, 2]      # il cognome non basta
    assert AG._iniziali_compatibili(["l"], rosa[1], ["martinez"])
    assert not AG._iniziali_compatibili(["l"], rosa[2], ["martinez"])
    assert AG._iniziali_compatibili(["jo"], rosa[2], ["martinez"])
    assert not AG._iniziali_compatibili(["jo"], rosa[1], ["martinez"])


def test_l_iniziale_guarda_il_nome_proprio_non_il_cognome():
    """`Se.` di `Esposito Se.` non deve trovarsi da solo dentro `Esposito`."""
    assert not AG._iniziali_compatibili(["se"], "Esposito", ["esposito"])
    assert AG._iniziali_compatibili(["se"], "Sebastiano Esposito", ["esposito"])


def test_il_cognome_puo_essere_contenuto_o_attaccato():
    rosa = {1: "André-Frank Zambo Anguissa"}
    assert AG._candidati(["zambo", "anguissa"], rosa) == [1]   # sottoinsieme
    assert AG._candidati(["anguissa"], rosa) == [1]            # ultimo pezzo
    assert AG._candidati(["zamboanguissa"], rosa) == [1]       # attaccato


def test_un_nome_nullo_non_e_un_candidato():
    """`playerName` e' nullo su qualche riga di WhoScored. Un nome che non c'e'
    non deve agganciare per caso chiunque."""
    assert AG._candidati(["rossi"], {1: None, 2: float("nan")}) == []


# --------------------------------------------------------------------------
# 2. Gli invarianti sui dati veri
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def squadre():
    return AG.mappa_squadre()


@pytest.fixture(scope="module")
def partite(squadre):
    return AG.mappa_partite(squadre)


@pytest.fixture(scope="module")
def giocatori():
    return AG.mappa_giocatori()


def test_venti_squadre_per_stagione(squadre):
    assert (squadre.groupby("stagione").size() == 20).all()
    assert set(squadre["stagione"]) == set(config.SEASONS_STORICHE)


def test_l_aggancio_delle_squadre_e_una_biiezione(squadre):
    """Se due squadre dei voti finissero sulla stessa WhoScored, i voti di una
    andrebbero sui minuti dell'altra e nessun totale se ne accorgerebbe."""
    for chiave in ("teamId_ws", "squadra_id_fc"):
        assert not squadre.duplicated(["stagione", chiave]).any(), chiave


def test_il_margine_delle_squadre_non_regge_per_poco(squadre):
    """Un margine di 1 su 38 sarebbe un aggancio che tiene per caso."""
    assert squadre["margine"].min() >= 10


def test_una_partita_ha_un_solo_matchId(partite):
    p = partite["partite"]
    assert not p.duplicated(["stagione", "partita_id"]).any()
    assert not p.duplicated(["stagione", "matchId"]).any()


def test_i_residui_sono_quelli_gia_documentati(partite):
    """12 partite senza eventi (le `matchCentreData: null` dell'acquisizione) e
    una senza voti (lo spareggio Spezia-Verona). Se questi numeri cambiano, o e'
    cambiato l'aggancio o e' cambiato il grezzo: in entrambi i casi va guardato.
    """
    assert len(partite["solo_fc"]) == 12
    assert set(partite["solo_fc"]["stagione"]) == {"2021-2022", "2022-2023"}
    assert len(partite["solo_ws"]) == 1
    assert partite["solo_ws"].iloc[0]["stagione"] == "2022-2023"


def test_lo_spareggio_non_si_aggancia_alla_giornata_25(partite):
    """La sola coppia ordinata che si ripete in una stagione.

    Senza la scelta per data piu' vicina, la giornata 25 si aggancerebbe a
    **entrambe** le partite, e quella di giugno finirebbe sotto i voti di marzo.
    """
    p = partite["partite"]
    spezia = p[(p["stagione"] == "2022-2023") & (p["giornata"] == 25)
               & (p["casa"] == "Spezia")]
    assert len(spezia) == 1
    assert spezia.iloc[0]["scarto_giorni"] == 0


def test_gli_scarti_di_data_sono_solo_le_partite_riprese(partite):
    """Due sole, entrambe interrotte e riprese in un'altra data."""
    p = partite["partite"]
    fuori = p[p["scarto_giorni"] > 0]
    assert len(fuori) == 2
    assert set(fuori["giornata"]) == {32, 14}


def test_tutti_i_giocatori_sono_agganciati(giocatori):
    assert len(giocatori["irrisolti"]) == 0
    assert len(giocatori["mappa"]) == 609


def test_un_giocatore_dei_voti_non_finisce_su_due_whoscored(giocatori):
    m = giocatori["mappa"]
    for chiave in ("playerId_ws", "giocatore_id_fc"):
        assert not m.duplicated(["teamId_ws", chiave]).any(), chiave


def test_il_calendario_conferma_l_aggancio_dei_giocatori(giocatori):
    """Il calendario non e' la chiave, e' la verifica: se i due insiemi di
    presenze non si sovrapponessero, l'aggancio per nome sarebbe sbagliato."""
    j = giocatori["mappa"]["jaccard"]
    assert j.min() > 0.9
    assert j.mean() > 0.99


def test_il_ruolo_resta_in_due_colonne(giocatori):
    """Vincolo 7: il ruolo di lega (P/D/C/A) e quello posizionale non sono la
    stessa grandezza, e infatti discordano su un giocatore su cinque."""
    m = giocatori["mappa"]
    assert {"ruolo_fc", "ruolo_ws"} <= set(m.columns)
    tradotto = m["ruolo_fc"].map({"p": "GK", "d": "DEF", "c": "MID", "a": "FWD"})
    assert (tradotto != m["ruolo_ws"]).sum() > 50


# --------------------------------------------------------------------------
# 3. La regola dell'80'
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tavola():
    return PR.tavola()


def test_la_soglia_e_dichiarata_non_scelta():
    """Vincolo 1. La soglia viene da `regole_fantacalcio.md` §1.2, decisa
    dall'utente **prima** della misura. Se un giorno qualcuno la scegliesse
    massimizzando `sensibilita_soglia`, diventerebbe un iperparametro adattato
    al campione su cui poi la si valuta."""
    assert PR.SOGLIA_SV == 80.0
    src = (config.ROOT / "sot" / "presenza.py").read_text(encoding="utf-8")
    assert "SOGLIA_SV = 80.0" in src
    # nessuna riga sceglie la soglia da una massimizzazione
    assert "idxmax" not in src and "argmax" not in src


def test_ogni_riga_ha_il_voto_e_i_minuti(tavola):
    """Se l'aggancio perdesse qualcuno, si vedrebbe come minuti mancanti."""
    assert tavola["start_min"].notna().all()
    assert len(tavola) == 11926


def test_l_universo_e_chi_e_sceso_in_campo(tavola):
    """Non la rosa: i panchinari non entrati non hanno riga nei voti, e
    aggiungerli qui dichiarerebbe un s.v. che nessuno ha osservato."""
    assert (tavola["minutes"] > 0).all()
    assert not tavola["allenatore"].any()


def test_la_matrice_di_confusione_torna(tavola):
    c = PR.misura_regola(tavola)["confronto"].set_index("regola")
    r = c.loc["regola 80' (utente)"]
    assert r["concordi"] + r["falsi_sv"] + r["sv_mancati"] == r["righe"]
    assert r["sv_proiettati"] == r["sv_osservati"] - r["sv_mancati"] + r["falsi_sv"]


def test_i_baseline_stanno_accanto_alla_regola(tavola):
    """Vincolo 6. Senza, il 97,8% di accordo sembra un risultato: il baseline che
    non prevede nessun s.v. ne fa gia' 90,5."""
    c = PR.misura_regola(tavola)["confronto"]
    assert len(c) == 3
    nessuno = c[c["regola"].str.contains("nessun")].iloc[0]
    assert nessuno["quota_concordi"] > 0.90
    regola = c.iloc[0]
    assert regola["quota_concordi"] > nessuno["quota_concordi"]


def test_i_titolari_con_sv_sono_tutti_usciti_presto(tavola):
    """La classe di casi fuori dal dominio della regola: chi guarda il minuto
    d'ingresso non vedra' mai un titolare uscito al 15'."""
    tit = tavola[tavola["is_starter"].astype(bool)]
    sv = tit[tit["sv_osservato"]]
    assert len(sv) == 18
    assert (sv["end_min"] < 30).all()


def test_sopra_i_trenta_minuti_non_esiste_un_solo_sv(tavola):
    """Il fatto che la misura ha portato a galla: la regola formale non esiste —
    la fonte lo dichiara — ma la pratica editoriale e' quasi deterministica."""
    sopra = tavola[tavola["minutes"] >= 30]
    assert len(sopra) > 8000
    assert sopra["sv_osservato"].sum() == 0
