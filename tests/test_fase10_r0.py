# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R0 — test del perimetro.

R0 non stima niente, quindi non c'e' una metrica da verificare su dati simulati.
Cio' che questi test proteggono e' di un'altra specie: **i conteggi pubblicati**,
e le tre proprieta' su cui poggiano. Un conteggio sbagliato in R0 non fallisce da
nessuna parte — si propaga in R1, R2 e R3 come una premessa.

La regola seguita e' quella del repository: dove il numero pubblicato e' il
risultato, il test lo **ricalcola per una strada diversa** invece di richiamare
la stessa funzione, altrimenti verificherebbe che il codice fa quello che fa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import config, perimetro as PM


@pytest.fixture(scope="module")
def p() -> pd.DataFrame:
    return PM.partite()


@pytest.fixture(scope="module")
def wf() -> pd.DataFrame:
    from sot import difesa

    return difesa.walkforward_gol()


# ---------------------------------------------------------------------------
# I conteggi pubblicati
# ---------------------------------------------------------------------------

def test_perimetro_pubblicato(p):
    """1.889 -> 1.739 -> 1.638. Sono i tre numeri del report."""
    casc = PM.cascata(p)
    assert int(casc["acquisite"].sum()) == 1889
    assert int(casc["con_previsione"].sum()) == 1739
    assert int(casc["validabili"].sum()) == 1638


def test_validabili_ricalcolate_dal_walkforward(wf, p):
    """Le 1.638 rifatte dal derivato di E3, senza passare da `partite()`.

    Se la rotazione a livello partita avesse perso o duplicato righe, i due
    conteggi divergerebbero. E' l'unico modo di rendere il numero falsificabile:
    richiamare `cascata()` verificherebbe solo che la somma di una colonna e' la
    somma di quella colonna.
    """
    per_partita = wf.groupby(["stagione", "matchId"])["eligible"].sum()
    atteso = int((per_partita == 2).sum())
    assert atteso == 1638
    assert atteso == int(p["validabile"].sum())


def test_ogni_partita_ha_due_lati(wf):
    """La rotazione e' definita solo se ogni partita ha esattamente due righe."""
    n = wf.groupby(["stagione", "matchId"]).size()
    assert set(n.unique()) == {2}


def test_un_solo_lato_di_casa(wf):
    """`is_home` distingue i due lati. Se fosse costante, si scambierebbero."""
    casa = wf.groupby(["stagione", "matchId"])["is_home"].sum()
    assert set(casa.unique()) == {1}


# ---------------------------------------------------------------------------
# Le tre proprieta' dichiarate
# ---------------------------------------------------------------------------

def test_soglia_eligible_e_verificata_non_assunta(wf):
    """`eligible` <=> `team_match_idx >= 6`, su tutte le righe."""
    v = PM.verifica_soglia_eligible()
    assert v["coincide"] is True
    assert v["discordanti"] == 0
    assert v["soglia"] == PM.IDX_ELIGIBLE == 6


def test_la_soglia_e_falsificabile(wf, monkeypatch):
    """Guastando una riga, la verifica deve accorgersene.

    Senza questo, `coincide=True` potrebbe voler dire «non guarda niente».
    """
    rotto = wf.copy()
    i = rotto.index[rotto["team_match_idx"] >= PM.IDX_ELIGIBLE][0]
    rotto.loc[i, "eligible"] = False
    monkeypatch.setattr(PM, "_walkforward", lambda: rotto)

    v = PM.verifica_soglia_eligible()
    assert v["coincide"] is False
    assert v["discordanti"] == 1


def test_eligible_e_della_squadra_non_della_partita(p):
    """Esistono partite con un lato eligible e l'altro no: sono due, nel 2021-22.

    E' il fatto che giustifica `validabile = elig_casa & elig_trasferta`. Se
    fosse zero, la congiunzione sarebbe indistinguibile da un `or` e nessuno se
    ne accorgerebbe.
    """
    d = PM.disallineamenti(p)
    assert len(d) == 2
    assert set(d["stagione"]) == {"2021-2022"}
    assert set(d["in_ritardo"]) == {"Atalanta", "Salernitana"}


def test_il_lato_in_ritardo_ha_perdite_alla_fonte(p):
    """Il disallineamento cade dove la fonte ha perso partite, e si verifica.

    E' l'affermazione del report, e senza questo test sarebbe un'allusione: si
    ricontano le partite acquisite per squadra e si pretende che **entrambe** le
    squadre in ritardo ne abbiano meno del calendario pieno.
    """
    from sot import multistagione as MS

    tm = MS.carica("team_match")
    acq = (tm[tm["stagione"] == "2021-2022"]
           .groupby("team")["matchId"].nunique())

    d = PM.disallineamenti(p)
    for squadra in d["in_ritardo"]:
        assert acq[squadra] < 38, (
            f"{squadra} e' in ritardo sull'indice ma non ha perdite alla fonte: "
            "la spiegazione pubblicata nel report non regge"
        )
    # E il caso peggiore e' l'Atalanta, che e' la perdita dichiarata non casuale.
    assert acq["Atalanta"] == 35


def test_validabile_e_congiunzione_non_disgiunzione(p):
    """Una partita mezza prevista non e' validabile."""
    mezze = p[p["elig_casa"] != p["elig_trasferta"]]
    assert len(mezze) > 0
    assert not mezze["validabile"].any()


# ---------------------------------------------------------------------------
# Il bersaglio di R2 (vincolo 7)
# ---------------------------------------------------------------------------

def test_le_due_fonti_del_punteggio_concordano(p):
    """WhoScored ricomposto contro la fonte dei voti: zero discordanze."""
    e = PM.verifica_esito(p)
    assert e["confrontabili"] == 1738
    assert e["punteggio_discorde"] == 0
    assert e["esito_discorde"] == 0
    assert e["punteggio_identico"] == e["confrontabili"]


def test_esito_coerente_con_i_gol(p):
    """`esito` e' una funzione dei gol, ricalcolata qui in modo indipendente."""
    atteso = np.where(p["gol_casa"] > p["gol_trasferta"], "1",
                      np.where(p["gol_casa"] == p["gol_trasferta"], "X", "2"))
    assert (p["esito"].to_numpy() == atteso).all()


def test_lam_subiti_coincide_dopo_la_rotazione(p, wf):
    """Il lambda dell'avversario e' quello dell'altro lato della stessa riga."""
    k = wf.set_index(["stagione", "matchId", "team"])["lam_subiti"]
    campione = p.head(200)
    atteso = [k.loc[(s, m, c)] for s, m, c
              in zip(campione["stagione"], campione["matchId"], campione["casa"])]
    assert np.allclose(atteso, campione["lam_trasferta"].to_numpy())


# ---------------------------------------------------------------------------
# La struttura per giornata, che serve a R3
# ---------------------------------------------------------------------------

def test_giornate_piene(p):
    """155 su 175, e la prima piena non e' mai prima della sesta."""
    g = PM.struttura_giornate(p)
    assert int(g["giornate_piene"].sum()) == 155
    assert int(g["giornate_con_previsione"].sum()) == 175
    assert g["prima_piena"].min() >= 6


def test_la_giornata_non_e_team_match_idx(p):
    """Sono due grandezze diverse, e confonderle e' il difetto che E2 ha trovato.

    Se coincidessero, `_giornate()` sarebbe codice morto e R3 potrebbe usare
    l'indice: il test esiste per impedire che qualcuno lo concluda.
    """
    d = p[p["giornata"].notna()]
    assert not (d["giornata"] == d["idx_casa"]).all()
    assert (d["giornata"] != d["idx_casa"]).sum() > 0


def test_una_sola_partita_senza_giornata(p):
    """Lo spareggio Spezia-Verona: residuo gia' dichiarato dall'aggancio."""
    senza = p[p["giornata"].isna()]
    assert len(senza) == 1
    squadre = set(senza["casa"]) | set(senza["trasferta"])
    assert squadre == {"Spezia", "Verona"}


# ---------------------------------------------------------------------------
# Le realizzazioni, che sono l'argomento sull'ordine G1/G2
# ---------------------------------------------------------------------------

def test_realizzazioni_della_classifica(p):
    """Cinque. E' il numero su cui poggia tutta la §5 del report."""
    r = PM.realizzazioni(p)
    r3 = r[r["blocco"] == "R3"]
    assert len(r3) == 1
    assert int(r3["n"].iloc[0]) == 5
    assert int(r3["n"].iloc[0]) == p[p["validabile"]]["stagione"].nunique()


def test_realizzazioni_r2_sono_le_partite_validabili(p):
    r = PM.realizzazioni(p)
    assert (r[r["blocco"] == "R2"]["n"] == 1638).all()


# ---------------------------------------------------------------------------
# Guardie: R0 non stima, e non tocca la rete
# ---------------------------------------------------------------------------

def test_r0_non_stima(p):
    """Nessun fit nel modulo. La ricognizione non produce parametri."""
    src = (config.ROOT / "sot" / "perimetro.py").read_text(encoding="utf-8")
    # Sottostringhe letterali, non pattern: una regex scritta qui non verrebbe
    # compilata e il controllo passerebbe sempre, che e' peggio di non averlo.
    for vietato in (".fit(", "minimize(", "curve_fit", "LogisticRegression",
                    "Ridge(", "polyfit", "TeamModel", "walkforward_predict"):
        assert vietato not in src, f"R0 non deve stimare, trovato {vietato!r}"


def test_r0_non_scrive_sotto_data(p):
    src = (config.ROOT / "sot" / "perimetro.py").read_text(encoding="utf-8")
    for vietato in ("to_parquet", "to_csv", "write_text", "open("):
        assert vietato not in src, f"R0 non scrive: trovato {vietato!r}"


def test_r0_non_tocca_la_rete():
    src = (config.ROOT / "sot" / "perimetro.py").read_text(encoding="utf-8")
    for vietato in ("requests", "urllib", "selenium", "http"):
        assert vietato not in src, f"R0 non tocca la rete: trovato {vietato!r}"


def test_nessun_numero_pubblicato_e_cambiato():
    """R0 legge il derivato di E3 e non lo tocca: i suoi numeri restano.

    E' la guardia che ogni blocco di questo repository porta con se'.
    """
    from sot import difesa

    wf = difesa.walkforward_gol()
    assert len(wf) == 3478
    assert int(wf["eligible"].sum()) == 3278
