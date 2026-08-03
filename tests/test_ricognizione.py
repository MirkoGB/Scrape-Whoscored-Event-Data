# -*- coding: utf-8 -*-
"""Invarianti del Blocco 0.

Due famiglie, e la seconda e' quella che conta:

1. le funzioni di misura danno la risposta giusta su dati costruiti in cui la
   risposta e' nota — non sui dati del progetto, che sarebbe circolare;
2. **il modulo non fabbrica la fonte che non ha.** Sono i test che impediscono
   a una sessione futura di chiudere un buco con un segnaposto: nessuna colonna
   di voto compare in `data/mapping/`, `stato_fonte_voti` non crea niente
   guardando, e continua a guardare dove deve.

> **Aggiornato il 2026-08-03**: i voti sono stati acquisiti e la seconda
> famiglia cambia di segno per uno solo dei due buchi. `test_i_voti_sono_arrivati`
> ha sostituito il suo contrario, come la sua stessa docstring prevedeva. **Le
> quotazioni del listone restano fuori dal disco**, e il divieto di segnaposto
> vale ancora per intero su quelle: `test_mapping_non_contiene_colonne_di_voto`
> non e' stato toccato.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from sot import config, ricognizione as R


# --------------------------------------------------------------------------
# 1. Misure su dati costruiti
# --------------------------------------------------------------------------

def _file_df(righe):
    return pd.DataFrame(righe)


def test_calendario_legge_il_matchid_dallurl(tmp_path, monkeypatch):
    """`matchId` sta solo nell'URL: e' l'unica chiave che lega JSON e CSV."""
    cal = [{"date": "x", "home": "A", "away": "B", "score": "1:0",
            "url": "/matches/1575784/live/italia-serie-a-2021-2022-a-b"}]
    d = tmp_path / "whoscored" / "ITA-serie-a" / "2021-2022"
    d.mkdir(parents=True)
    (d / "matches.json").write_text(json.dumps(cal), encoding="utf-8")
    monkeypatch.setattr(config, "RAW", tmp_path)
    out = R.calendario("2021-2022")
    assert out.loc[0, "matchId"] == 1575784


def test_copertura_usa_il_calendario_come_denominatore(monkeypatch):
    """Il denominatore e' il calendario, non 380.

    E' la trappola che nell'acquisizione aveva fatto dichiarare "incompleto" un
    calendario a 381 partite.
    """
    monkeypatch.setattr(R, "calendario", lambda s: pd.DataFrame([
        {"stagione": s, "ordine": i, "matchId": 1000 + i, "casa": f"A{i}",
         "ospite": f"B{i}", "risultato": "1:0", "data_testo": "x"}
        for i in range(381)]))
    f = _file_df([{"stagione": "2022-2023", "matchId": 1000 + i, "n_eventi": 10}
                  for i in range(381)])
    out = R.copertura(f)
    assert out.loc[0, "calendario"] == 381
    assert out.loc[0, "mancanti"] == 0
    assert out.loc[0, "copertura"] == 1.0


def test_copertura_conta_i_mancanti(monkeypatch):
    monkeypatch.setattr(R, "calendario", lambda s: pd.DataFrame([
        {"stagione": s, "ordine": i, "matchId": i, "casa": "A", "ospite": "B",
         "risultato": "", "data_testo": ""} for i in range(10)]))
    f = _file_df([{"stagione": "S", "matchId": i, "n_eventi": 5} for i in range(7)])
    out = R.copertura(f)
    assert out.loc[0, "mancanti"] == 3
    assert out.loc[0, "copertura"] == pytest.approx(0.7)


def test_copertura_segnala_file_con_zero_eventi(monkeypatch):
    monkeypatch.setattr(R, "calendario", lambda s: pd.DataFrame([
        {"stagione": s, "ordine": i, "matchId": i, "casa": "A", "ospite": "B",
         "risultato": "", "data_testo": ""} for i in range(3)]))
    f = _file_df([{"stagione": "S", "matchId": 0, "n_eventi": 5},
                  {"stagione": "S", "matchId": 1, "n_eventi": 0},
                  {"stagione": "S", "matchId": 2, "n_eventi": 7}])
    assert R.copertura(f).loc[0, "file_con_zero_eventi"] == 1


def test_perdita_per_squadra_conta_entrambi_i_lati(monkeypatch):
    """Una squadra perde la partita sia che la giochi in casa sia in trasferta."""
    monkeypatch.setattr(R, "calendario", lambda s: pd.DataFrame([
        {"stagione": s, "ordine": 0, "matchId": 1, "casa": "Atalanta",
         "ospite": "Inter", "risultato": "", "data_testo": ""},
        {"stagione": s, "ordine": 1, "matchId": 2, "casa": "Inter",
         "ospite": "Atalanta", "risultato": "", "data_testo": ""}]))
    f = _file_df([{"stagione": "S", "matchId": 1, "n_eventi": 5}])
    out = R.perdita_per_squadra(f).set_index("squadra")
    assert out.loc["Atalanta", "calendario"] == 2
    assert out.loc["Atalanta", "mancanti"] == 1
    assert out.loc["Inter", "mancanti"] == 1


def test_stabilita_schema_distingue_assente_da_vuota():
    """Colonna mancante dal file e colonna presente ma nulla sono cose diverse.

    E' la trappola `isOwnGoal`: confonderle fa sparire l'unico segnale che dice
    se lo schema si e' mosso.
    """
    colonne = pd.DataFrame([
        # presente ovunque, sempre valorizzata
        {"stagione": "A", "colonna": "x", "file_con_colonna": 10,
         "file_totali": 10, "righe_coperte": 100, "non_falsi": 100},
        {"stagione": "B", "colonna": "x", "file_con_colonna": 10,
         "file_totali": 10, "righe_coperte": 100, "non_falsi": 100},
        # presente ovunque, ma valorizzata solo in B
        {"stagione": "A", "colonna": "y", "file_con_colonna": 10,
         "file_totali": 10, "righe_coperte": 100, "non_falsi": 0},
        {"stagione": "B", "colonna": "y", "file_con_colonna": 10,
         "file_totali": 10, "righe_coperte": 100, "non_falsi": 100},
        # assente del tutto in B
        {"stagione": "A", "colonna": "z", "file_con_colonna": 3,
         "file_totali": 10, "righe_coperte": 30, "non_falsi": 30},
    ])
    colonne["quota_file"] = colonne["file_con_colonna"] / colonne["file_totali"]
    colonne["quota_valorizzata"] = colonne["non_falsi"] / colonne["righe_coperte"]

    out = R.stabilita_schema(colonne).set_index("colonna")
    assert out.loc["z", "stagioni_con_colonna"] == 1      # assente in B
    assert out.loc["y", "stagioni_con_colonna"] == 2      # presente, ma vuota in A
    assert out.loc["y", "escursione_valorizzata"] == pytest.approx(1.0)
    assert out.loc["x", "escursione_valorizzata"] == pytest.approx(0.0)


def test_deriva_qualifier_normalizza_sugli_eventi():
    """Stagioni con un numero diverso di partite non sono confrontabili sui totali."""
    qual = pd.DataFrame([{"stagione": "A", "qualifier": "Q", "n": 1000},
                         {"stagione": "B", "qualifier": "Q", "n": 2000}])
    file_df = pd.DataFrame([{"stagione": "A", "n_eventi": 10_000},
                            {"stagione": "B", "n_eventi": 20_000}])
    out = R.deriva_qualifier(qual, file_df, min_totale=1).set_index("qualifier")
    # Stessa frequenza per evento: il rapporto dev'essere 1, non 2.
    assert out.loc["Q", "rapporto"] == pytest.approx(1.0)


def test_deriva_qualifier_vede_la_sparizione():
    qual = pd.DataFrame([{"stagione": "A", "qualifier": "Q", "n": 8000},
                         {"stagione": "B", "qualifier": "Q", "n": 100}])
    file_df = pd.DataFrame([{"stagione": "A", "n_eventi": 10_000},
                            {"stagione": "B", "n_eventi": 10_000}])
    out = R.deriva_qualifier(qual, file_df, min_totale=1).set_index("qualifier")
    assert out.loc["Q", "rapporto"] == pytest.approx(80.0)


def test_indice_giornata_boccia_un_blocco_incoerente(monkeypatch):
    """Un blocco di dieci con una squadra ripetuta non e' una giornata."""
    righe = []
    for i in range(10):                       # blocco coerente: 20 squadre
        righe.append({"stagione": "S", "ordine": i, "matchId": i,
                      "casa": f"C{i}", "ospite": f"O{i}",
                      "risultato": "", "data_testo": "d"})
    for i in range(10, 20):                   # blocco incoerente: si ripete C0
        righe.append({"stagione": "S", "ordine": i, "matchId": i,
                      "casa": "C0", "ospite": f"O{i}",
                      "risultato": "", "data_testo": ""})
    monkeypatch.setattr(R, "calendario", lambda s: pd.DataFrame(righe))
    out = R.indice_giornata("S")
    assert out["n_blocchi"] == 2
    assert out["blocchi_anomali"] == 1
    assert out["date_vuote"] == 10


def test_anomalie_identita_trova_i_casi_dichiarati():
    reg = pd.DataFrame([
        {"stagione": "S", "playerId": 1, "nome_modale": "Rossi",
         "n_grafie": 1, "n_eventi": 10, "n_squadre": 1,
         "teamId_principale": 1, "squadra_principale": "A"},
        {"stagione": "S", "playerId": 2, "nome_modale": "Rossi",
         "n_grafie": 1, "n_eventi": 10, "n_squadre": 1,
         "teamId_principale": 2, "squadra_principale": "B"},
        {"stagione": "S", "playerId": 3, "nome_modale": "Dimarco",
         "n_grafie": 2, "n_eventi": 10, "n_squadre": 2,
         "teamId_principale": 1, "squadra_principale": "A"},
        {"stagione": "S", "playerId": 4, "nome_modale": "Peluso",
         "n_grafie": 1, "n_eventi": 10, "n_squadre": 1,
         "teamId_principale": 1, "squadra_principale": "A"},
        {"stagione": "S", "playerId": 5, "nome_modale": "Ibañez",
         "n_grafie": 1, "n_eventi": 10, "n_squadre": 1,
         "teamId_principale": 1, "squadra_principale": "A"},
    ])
    a = R.anomalie_identita(reg)
    assert len(a["omonimi"]) == 1                       # Rossi, due playerId
    assert set(a["multisquadra"]["playerId"]) == {3}
    assert set(a["multigrafia"]["playerId"]) == {3}
    assert 4 in set(a["nome_singolo"]["playerId"])      # "Peluso", un nome solo
    assert set(a["nome_non_ascii"]["playerId"]) == {5}  # "Ibañez"


# --------------------------------------------------------------------------
# 2. Il modulo non fabbrica la fonte che non ha
# --------------------------------------------------------------------------

def test_stato_fonte_voti_guarda_i_percorsi_dichiarati():
    out = R.stato_fonte_voti()
    assert len(out) > 0
    assert {"percorso", "esiste", "file_presenti"} <= set(out.columns)
    # Deve guardare sotto raw/fantacalcio per ogni stagione del perimetro.
    for stagione in config.SEASONS_STORICHE:
        assert any(stagione in p for p in out["percorso"])


def test_stato_fonte_voti_non_crea_niente():
    """Accertare non e' preparare il terreno: guardare non crea cartelle.

    Scritto per differenza invece che per assenza. La versione precedente
    pretendeva che `data/raw/fantacalcio/` **non esistesse**, e valeva finche' i
    voti non erano stati acquisiti; ora esistono, e quella forma direbbe una cosa
    diversa da quella che intendeva. L'invariante vero e' che *questa funzione*
    non tocchi il disco, e si misura confrontando prima e dopo.
    """
    prima = set(R.stato_fonte_voti()["percorso"][R.stato_fonte_voti()["esiste"]])
    R.stato_fonte_voti()
    dopo = R.stato_fonte_voti()
    assert set(dopo["percorso"][dopo["esiste"]]) == prima
    # `data/external/voti/` non e' mai stato usato: i voti stanno sotto `raw/`,
    # perche' sono acquisiti da noi e non forniti a mano.
    assert not (config.EXTERNAL / "voti").exists()


def test_i_voti_sono_arrivati():
    """Il fatto su cui il Blocco 0 si era fermato, **datato**: 2026-08-03.

    Questo test era il suo contrario — pretendeva che i voti non fossero sul
    disco — e la sua docstring diceva che un fallimento sarebbe stato un buon
    fallimento, da aggiornare insieme al report e non da cancellare. E' quello
    che e' successo: la D1 del Blocco 0 e' chiusa, la via scelta e' la vista HTML
    pubblica, l'esito sta in `reports/voti_fantacalcio.md`.

    **La D2 resta aperta**, ed e' la ragione per cui il test guarda le due cose
    separatamente invece di dichiarare chiusa la seconda fonte: le quotazioni del
    listone non sono state acquisite, e sono la verifica principale del progetto.
    """
    stato = R.stato_fonte_voti()
    voti = stato[stato["percorso"].str.contains("fantacalcio")]
    assert voti["esiste"].all(), (
        "mancano stagioni di voti: rilancia "
        "`python -m acquisition.fantacalcio.scrape_voti`"
    )
    assert (voti["file_presenti"] > 0).all()


def test_mapping_non_contiene_colonne_di_voto():
    """Vieta il segnaposto: nessun file di mapping puo' avere una colonna voti.

    Una colonna vuota chiamata `voto` verrebbe letta a valle come "aggancio
    fallito" invece che "aggancio mai tentato", che e' una differenza sostanziale.
    """
    d = R.MAPPING_DIR
    if not d.exists():
        pytest.skip("mapping non ancora generato")
    vietate = {"voto", "fantavoto", "voto_redazione", "id_fantacalcio",
               "nome_fantacalcio", "quotazione"}
    for p in d.glob("*.csv"):
        cols = {c.strip().lower() for c in pd.read_csv(p, nrows=0).columns}
        assert not (cols & vietate), f"{p.name} contiene {cols & vietate}"


def test_esposizione_regola_80_non_e_il_tasso_di_errore():
    """La funzione non deve esporre nulla che somigli a un tasso d'errore.

    Il tasso d'errore ha bisogno dell's.v. osservato. Una colonna con quel nome
    qui dentro sarebbe un numero inventato con l'aria di una misura.
    """
    out = R.esposizione_regola_80()
    proibite = {"errore", "tasso_errore", "falsi_positivi", "falsi_negativi",
                "sv_osservato"}
    assert not (set(out.columns) & proibite)
    assert "sv_proiettato" in out.columns


@pytest.mark.parametrize("soglia", [70.0, 80.0, 90.0])
def test_esposizione_regola_80_e_monotona(soglia):
    """Alzando la soglia, le righe marcate s.v. non possono aumentare."""
    bassa = R.esposizione_regola_80(soglia)["sv_proiettato"].iloc[0]
    alta = R.esposizione_regola_80(soglia + 5.0)["sv_proiettato"].iloc[0]
    assert alta <= bassa


def test_ingressi_per_minuto_somma_a_uno():
    g = R.ingressi_per_minuto()
    assert g["quota"].sum() == pytest.approx(1.0)
