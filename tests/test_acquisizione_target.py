"""La parametrizzazione campionato-stagione dello scraper WhoScored.

Girano **senza selenium, senza browser e senza rete**: e' il motivo per cui la
risoluzione dei bersagli vive in `acquisition/whoscored/target.py` invece che
dentro lo scraper. I termini d'uso di WhoScored non sono ancora stati accertati
(`docs/regole_fantacalcio.md` §7.1), quindi un test che per verificare la
parametrizzazione dovesse eseguire lo scraper non sarebbe eseguibile affatto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sot import config

ROOT = Path(__file__).resolve().parent.parent
# Stessa via con cui lo script risolve i propri vicini: la cartella non e' un
# pacchetto di proposito (vedi acquisition/__init__.py).
sys.path.insert(0, str(ROOT / "acquisition" / "whoscored"))

import pagina as P  # noqa: E402
import target as T  # noqa: E402


# --------------------------------------------------------------------------
# Dati assenti alla fonte != errore di lettura
#
# Le 12 partite mancanti del 2021-22 e 2022-23 hanno tutte `matchCentreData:
# null`, verificato una per una. Il parser di main.py fallisce li' con
# `substring not found`, che descrive l'incidente meccanico e nasconde il fatto.
# --------------------------------------------------------------------------
SCRIPT_SENZA_DATI = (
    'require.config.params["args"] = {\n  matchId:1575817,\n'
    '  matchCentreData: null,\n  matchCentreEventTypeJson: {"shotSixYardBox":0},\n'
    '  formationIdNameMappings:{"2":"442"}\n};'
)
SCRIPT_CON_DATI = SCRIPT_SENZA_DATI.replace(
    "matchCentreData: null", 'matchCentreData: {"playerIdNameDictionary":{}}')


def test_dati_assenti_riconosciuti():
    assert P.diagnosi(SCRIPT_SENZA_DATI) == P.DATI_ASSENTI
    assert "inutile ritentare" in P.spiega(P.DATI_ASSENTI)


def test_dati_presenti_riconosciuti():
    assert P.diagnosi(SCRIPT_CON_DATI) == P.OK


def test_pagina_inattesa_e_distinta_dai_dati_assenti():
    """Ha senso ritentare una pagina d'errore; non ha senso ritentare una
    partita che la fonte non ha. I due casi non vanno confusi."""
    for html in ("", None, "<html>errore 503</html>"):
        assert P.diagnosi(html) == P.SENZA_MATCHID
    assert "ritentabile" in P.spiega(P.SENZA_MATCHID)


@pytest.mark.parametrize("forma", ["matchCentreData: null", "matchCentreData:null",
                                   "matchCentreData:  null"])
def test_spaziatura_del_valore_nullo(forma):
    assert P.diagnosi(SCRIPT_SENZA_DATI.replace("matchCentreData: null", forma)) \
        == P.DATI_ASSENTI


def test_lo_scraper_separa_i_due_esiti():
    testo = (ROOT / "acquisition" / "whoscored" / "scrape_season.py").read_text(
        encoding="utf-8")
    assert "pagina.DATI_ASSENTI" in testo
    assert "'nodata'" in testo, "l'esito senza dati va contato a parte da 'err'"
    corpo = testo.split("def main(")[1]
    assert "NON si recuperano rilanciando" in corpo


# --------------------------------------------------------------------------
# Le due convenzioni di stagione restano separate
# --------------------------------------------------------------------------
def test_conversione_alla_forma_del_sito():
    assert T.stagione_whoscored("2025-2026") == "2025/2026"
    assert T.stagione_whoscored("2021-2022") == "2021/2022"


@pytest.mark.parametrize("cattiva", ["2025/2026", "2025-26", "2526", "2025"])
def test_la_forma_del_sito_non_e_accettata_in_ingresso(cattiva):
    """Il verso della conversione e' uno solo. Se `2025/2026` fosse accettata
    in ingresso, la forma della fonte entrerebbe nei nomi di cartella — che e'
    esattamente cio' che la tassonomia della Fase 7A evita."""
    with pytest.raises(ValueError):
        T.stagione_whoscored(cattiva)


def test_config_non_conosce_la_forma_del_sito():
    """La barra e' una proprieta' di WhoScored, non della tassonomia."""
    sorgente = (ROOT / "sot" / "config.py").read_text(encoding="utf-8")
    assert "2025/2026" not in sorgente


# --------------------------------------------------------------------------
# Il bersaglio e i percorsi che ne discendono
# --------------------------------------------------------------------------
def test_default_e_il_perimetro_pubblicato():
    t = T.Target()
    assert (t.league, t.season) == (config.LEAGUE, config.SEASON)


def test_i_percorsi_del_default_sono_quelli_delle_fasi_0_6():
    """Il bersaglio di default deve puntare esattamente dove il modello legge:
    se divergesse, lo scraper riempirebbe una cartella che nessuno usa."""
    t = T.Target()
    assert t.dir_partite == config.RAW_MATCH_DIR
    assert t.cache_url == config.MATCHES_JSON


@pytest.mark.parametrize("season", config.SEASONS_STORICHE)
def test_ogni_stagione_storica_ha_percorsi_distinti_e_ben_formati(season):
    t = T.Target(season=season)
    assert season in t.dir_partite.parts
    assert config.LEAGUE in t.dir_partite.parts
    assert t.dir_partite.name == "events"
    assert t.cache_url.name == "matches.json"


def test_le_cinque_stagioni_non_si_sovrascrivono():
    dirs = {T.Target(season=s).dir_partite for s in config.SEASONS_STORICHE}
    assert len(dirs) == len(config.SEASONS_STORICHE)


def test_url_della_competizione():
    t = T.Target()
    assert t.url_competizione("https://it.whoscored.com/") == (
        "https://it.whoscored.com/regions/108/tournaments/5/italy-serie-a"
    )


def test_il_bersaglio_e_immutabile():
    """Uno scraper che gira su cinque stagioni non deve poter riscrivere il
    proprio bersaglio a meta' esecuzione."""
    t = T.Target()
    with pytest.raises(Exception):
        t.season = "2021-2022"


# --------------------------------------------------------------------------
# Cosa viene rifiutato invece di essere inventato
# --------------------------------------------------------------------------
@pytest.mark.parametrize("cattiva", ["2025-26", "2526", "2025/2026", "1999"])
def test_stagione_mal_formata_rifiutata(cattiva):
    with pytest.raises(ValueError):
        T.Target(season=cattiva)


def test_campionato_senza_codici_whoscored_rifiutato():
    """Per gli altri quattro campionati regione e torneo non sono stati
    verificati. Un URL inventato porterebbe a un'altra competizione **senza
    dirlo**, e i CSV finirebbero in una cartella col nome sbagliato."""
    with pytest.raises(ValueError, match="non sono stati verificati"):
        T.Target(league="ENG-premier-league")


def test_campionato_ignoto_rifiutato():
    with pytest.raises(ValueError):
        T.Target(league="I1")


# --------------------------------------------------------------------------
# La CLI
# --------------------------------------------------------------------------
def test_senza_argomenti_sono_tutte_e_cinque():
    """E' la richiesta: cinque stagioni di Serie A. Il default `None` non
    significa 'la stagione corrente'."""
    bersagli = T.targets(None, None)
    assert [t.season for t in bersagli] == list(config.SEASONS_STORICHE)
    assert len(bersagli) == 5


def test_le_stagioni_escono_in_ordine_cronologico():
    b = T.targets(None, ["2024-2025", "2021-2022", "2023-2024"])
    assert [t.season for t in b] == ["2021-2022", "2023-2024", "2024-2025"]


def test_parser_default():
    a = T.parser().parse_args([])
    assert a.league == config.LEAGUE
    assert a.season is None
    assert a.dry_run is False
    assert a.merge is False, "la concatenazione da 1 GB non si scrive per default"
    assert a.sleep >= 5, "una pausa troppo corta fa scattare il blocco della fonte"


def test_parser_una_e_piu_stagioni():
    assert T.parser().parse_args(["--season", "2021-2022"]).season == ["2021-2022"]
    a = T.parser().parse_args(["--season", "2021-2022", "2022-2023"])
    assert a.season == ["2021-2022", "2022-2023"]


def test_parser_rifiuta_un_campionato_fuori_tassonomia():
    with pytest.raises(SystemExit):
        T.parser().parse_args(["--league", "I1"])


# --------------------------------------------------------------------------
# Stato e idempotenza (vincolo 9)
# --------------------------------------------------------------------------
def test_stato_vede_la_stagione_gia_scaricata():
    s = T.stato(T.Target())
    assert s["csv_su_disco"] == 380
    assert s["partite_in_cache"] >= 380
    assert s["da_scaricare"] == 0, (
        "la 2025-26 e' completa: un rilancio non deve avere niente da fare"
    )


@pytest.mark.parametrize("season", config.SEASONS_STORICHE)
def test_stato_e_coerente_con_il_disco(season):
    """Invariante, non fotografia. Una versione precedente di questo test
    asseriva che le altre quattro stagioni fossero vuote: era vero quando e'
    stato scritto e falso venti minuti dopo, perche' lo scaricamento era in
    corso. Un test che descrive uno stato transitorio non e' un test."""
    t = T.Target(season=season)
    s = T.stato(t)
    su_disco = len(list(t.dir_partite.glob("*.csv"))) if t.dir_partite.is_dir() else 0
    assert s["csv_su_disco"] == su_disco
    if s["partite_in_cache"] == 0:
        assert s["da_scaricare"] is None, "senza cache calendario non e' un numero noto"
    else:
        assert s["da_scaricare"] == max(s["partite_in_cache"] - su_disco, 0)


def test_una_stagione_completa_non_ha_niente_da_scaricare():
    """Su una stagione completa un rilancio non deve avere nulla da fare: e'
    l'idempotenza vista da fuori, prima di aprire un browser."""
    s = T.stato(T.Target())
    assert s["csv_su_disco"] == 380
    assert s["da_scaricare"] == 0


def test_lo_scraper_non_sovrascrive_mai_un_csv_gia_presente():
    """Vincolo 9. E' un grep, ma il vincolo che protegge e' quello che costa di
    piu' se salta: un rilancio che riscrivesse il grezzo lo perderebbe in
    silenzio. Il controllo e' che `to_csv` sul percorso di destinazione sia
    preceduto dalla guardia su `exists()`."""
    testo = (ROOT / "acquisition" / "whoscored" / "scrape_season.py").read_text(
        encoding="utf-8")
    corpo = testo.split("def scarica_partite")[1].split("\ndef ")[0]
    assert "if out_path.exists():" in corpo
    assert corpo.index("if out_path.exists():") < corpo.index("to_csv")


# --------------------------------------------------------------------------
# Completezza del calendario
# --------------------------------------------------------------------------
def _calendario(conteggi):
    """Finto calendario: `conteggi` e' {squadra: partite}. Genera accoppiamenti
    fittizi che rispettano quei totali, che e' tutto cio' che la funzione legge."""
    partite, coda = [], []
    for squadra, n in conteggi.items():
        coda += [squadra] * n
    for i in range(0, len(coda), 2):
        partite.append({"home": coda[i], "away": coda[i + 1]})
    return partite


def test_calendario_completo():
    assert T.report_completeness(_calendario({f"S{i}": 38 for i in range(20)}))


def test_calendario_con_una_squadra_incompleta():
    c = {f"S{i}": 38 for i in range(20)}
    c["S0"], c["S1"] = 36, 36
    assert not T.report_completeness(_calendario(c))


def test_lo_spareggio_non_e_un_calendario_incompleto():
    """Il caso vero della 2022-2023: uno stage in piu' (`Serie A Relegation
    Playoff`), 381 partite invece di 380, due squadre a 39.

    Il confronto originale era `!= expected`, quindi le due squadre a 39
    finivano nell'elenco "squadre con MENO di 38". Il calendario era completo e
    veniva dichiarato incompleto: quattro passate di navigazione buttate a
    cercare partite gia' presenti, e un messaggio falso."""
    c = {f"S{i}": 38 for i in range(20)}
    c["S0"], c["S1"] = 39, 39
    partite = _calendario(c)
    assert len(partite) == 381
    assert T.report_completeness(partite), (
        "piu' partite del previsto non e' un calendario incompleto"
    )


def test_spareggio_e_squadra_mancante_insieme():
    """Lo spareggio non deve mascherare un buco vero."""
    c = {f"S{i}": 38 for i in range(20)}
    c["S0"], c["S1"] = 39, 39
    c["S2"] = 30
    assert not T.report_completeness(_calendario(c))


# --------------------------------------------------------------------------
# Il menu `stages`: un banner sopra un controllo e' costato una stagione intera
# --------------------------------------------------------------------------
def _sorgente_scraper():
    return (ROOT / "acquisition" / "whoscored" / "scrape_season.py").read_text(
        encoding="utf-8")


def test_lo_stage_si_seleziona_con_il_ripiego_su_javascript():
    """La 2022-2023 si e' persa qui: `select_by_index` fallisce con
    ElementClickInterceptedException quando un banner copre il menu. Il ripiego
    e' lo stesso gia' usato da `_click_prev_day`."""
    corpo = _sorgente_scraper().split("def _select_stage")[1].split("\ndef ")[0]
    assert "ElementClickInterceptedException" in corpo
    assert "execute_script" in corpo
    assert "change" in corpo, (
        "senza l'evento 'change' la pagina resta sullo stage precedente e si "
        "rileggono le stesse partite"
    )


def test_un_menu_stages_inutilizzabile_non_fa_perdere_la_stagione():
    """Il fallback deve coprire anche l'intercettazione del click, non solo
    l'assenza del menu: era la differenza fra una stagione e zero."""
    corpo = _sorgente_scraper().split("def get_match_urls")[1].split("\ndef ")[0]
    intercetta = corpo.split("except (")[1].split(")")[0]
    for atteso in ("NoSuchElementException", "TimeoutException",
                   "ElementClickInterceptedException"):
        assert atteso in intercetta, atteso
    assert "_select_stage(driver, i)" in corpo


def test_una_stagione_che_fallisce_non_ferma_le_altre():
    """Verificato sul campo: la 2022-2023 si e' interrotta e la 2023-2024 e'
    partita lo stesso, arrivando a 380 CSV."""
    corpo = _sorgente_scraper().split("def main(")[1]
    ciclo = corpo.split("for target in bersagli:")[1].split("print(")[0]
    assert "except Exception" in ciclo
    assert "esiti[str(target)]" in ciclo


def test_la_concatenazione_non_finisce_sotto_raw():
    """E' derivata. `raw/` non ospita derivati, e su cinque stagioni sarebbero
    cinque copie da 1 GB di dati gia' presenti."""
    t = T.Target()
    assert config.RAW not in t.file_unito.parents
    assert "processed" in t.file_unito.parts
