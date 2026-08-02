"""Invarianti della struttura introdotta dalla Fase 7A.

Non sono controlli di stile: sono i vincoli che impediscono alla tassonomia
campionato-stagione di sfaldarsi al primo campionato in piu'. Il refactor della
7A funziona solo finche' `config.py` resta l'unico posto in cui un campionato e
una stagione hanno un nome; il test 4 e' quello che lo tiene.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sot import config

ROOT = Path(__file__).resolve().parent.parent

# I moduli che NON devono conoscere campionato e stagione. `acquisition/` e'
# escluso di proposito: lo scraper WhoScored ha ancora SEASON e COMPETITION_URL
# scritti a mano, cosa che la 7A ha dichiarato e non risolto.
SORGENTI_MODELLO = sorted((ROOT / "sot").glob("*.py")) + sorted(
    (ROOT / "scripts").glob("*.py")
)


# --------------------------------------------------------------------------
# 1. I percorsi si risolvono, e puntano a dati veri
# --------------------------------------------------------------------------
def test_raw_match_dir_contiene_i_380_csv():
    assert config.RAW_MATCH_DIR.is_dir(), config.RAW_MATCH_DIR
    csv = list(config.RAW_MATCH_DIR.glob("*.csv"))
    assert len(csv) == 380, f"attesi 380 CSV partita, trovati {len(csv)}"


def test_matches_json_leggibile_e_completo():
    assert config.MATCHES_JSON.is_file(), config.MATCHES_JSON
    with open(config.MATCHES_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data) >= 380


def test_processed_contiene_i_parquet_delle_fasi_1_2():
    assert config.PROCESSED.is_dir(), config.PROCESSED
    for p in (config.TEAM_MATCH, config.PLAYER_MATCH,
              config.SHOTS_PARQUET, config.EVENTS_SLIM):
        assert p.is_file(), p


def test_i_percorsi_stanno_sotto_la_coppia_campionato_stagione():
    """Il valore delle costanti e' cambiato, i nomi no: e' cio' che rende il
    refactor invisibile ai moduli a valle. Qui si verifica il valore."""
    for p in (config.RAW_MATCH_DIR, config.MATCHES_JSON, config.PROCESSED):
        parti = p.parts
        assert config.LEAGUE in parti, p
        assert config.SEASON in parti, p


# --------------------------------------------------------------------------
# 2. Il formato della stagione
# --------------------------------------------------------------------------
def test_season_e_nella_forma_non_ambigua():
    assert re.match(config.SEASON_RE, config.SEASON)


@pytest.mark.parametrize("cattiva", ["2025-26", "2526", "2025/2026", "2025",
                                     "25-26", "2025_2026", ""])
def test_stagioni_mal_formate_sono_rifiutate(cattiva):
    """Un percorso su `2025-26` non fallisce: crea silenziosamente una cartella
    accanto a quella giusta e i dati si dividono in due. Meglio l'eccezione."""
    with pytest.raises(ValueError):
        config.raw_dir("whoscored", season=cattiva)
    with pytest.raises(ValueError):
        config.processed_dir(season=cattiva)


# --------------------------------------------------------------------------
# 3. La tassonomia dei campionati
# --------------------------------------------------------------------------
def test_league_e_dichiarato():
    assert config.LEAGUE in config.LEAGUE_CODES


def test_ogni_campionato_dichiara_il_codice_della_fonte_tabellare():
    """La corrispondenza `ITA-serie-a` -> `I1` vive in un posto solo. Se il
    blocco 7B la ricostruisse al punto d'uso, `I1` tornerebbe a essere un nome
    di cartella e la convenzione di una fonte entrerebbe nella struttura."""
    for league, codici in config.LEAGUE_CODES.items():
        assert codici.get("football_data"), league
        assert "whoscored" in codici, league


def test_campionati_ignoti_sono_rifiutati():
    with pytest.raises(ValueError):
        config.raw_dir("whoscored", league="I1")
    with pytest.raises(ValueError):
        config.processed_dir(league="Serie A")


# --------------------------------------------------------------------------
# 4. Nessun percorso scritto a mano fuori da config.py
# --------------------------------------------------------------------------
def test_nessun_modulo_nomina_la_vecchia_cartella():
    # `config.py` la nomina, ma nel commento che spiega da dove si viene: e'
    # l'unico posto in cui la vecchia forma ha ancora ragione di comparire.
    colpevoli = [p.name for p in SORGENTI_MODELLO
                 if p.name != "config.py"
                 and "serie_a_2025_2026" in p.read_text(encoding="utf-8")]
    assert not colpevoli, (
        f"{colpevoli} nominano ancora `serie_a_2025_2026`: campionato e "
        "stagione hanno un nome solo in config.py"
    )


def test_nessun_percorso_con_stagione_scritto_a_mano():
    """Senza questo test la prima fretta rimette un percorso a mano, e la
    tassonomia dura fino al secondo campionato.

    Cerca stringhe letterali che contengano una stagione *e* qualcosa di
    filesystem — separatore o estensione. Non basta nominare "2025-26" in una
    docstring: i report parlano di stagioni in prosa continuamente, e vietarlo
    renderebbe il test rumore. Il difetto da bloccare e' il percorso, non la
    parola.
    """
    letterale = re.compile(r"""['"]([^'"]*(?:19|20)\d{2}[-_/]\d{2,4}[^'"]*)['"]""")
    filesystem = re.compile(r"[/\\]|\.(csv|json|parquet|xlsx|png)\b")
    colpevoli = []
    for p in SORGENTI_MODELLO:
        if p.name == "config.py":
            continue
        for n, riga in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "http" in riga:
                continue
            for m in letterale.findall(riga):
                if filesystem.search(m):
                    colpevoli.append(f"{p.name}:{n}: {riga.strip()}")
    assert not colpevoli, "percorsi con stagione fuori da config.py:\n" + "\n".join(colpevoli)


def test_nessuno_legge_il_csv_concatenato_da_1gb():
    """Era 1 GB di concatenazione dei CSV per partita, cancellato dalla 7A.
    `sot/io_events.py` dichiarava gia' di non leggerlo: qui e' verificato."""
    colpevoli = [p.name for p in SORGENTI_MODELLO
                 if "read_csv" in (t := p.read_text(encoding="utf-8"))
                 and "events_concat" in t]
    assert colpevoli in ([], ["tiri_in_porta.py"]), colpevoli


# --------------------------------------------------------------------------
# 5. `raw/` non si scrive dal modello (vincolo 9 della Fase 7)
# --------------------------------------------------------------------------
def test_il_modello_non_scrive_mai_sotto_raw():
    """Grossolano — e' un grep sul sorgente — ma e' il vincolo che costa di piu'
    se salta: il grezzo non si trasforma e non si sovrascrive."""
    scritture = re.compile(r"to_parquet|to_csv|open\([^)]*['\"]w|mkdir|unlink|rmtree")
    colpevoli = []
    for p in SORGENTI_MODELLO:
        for n, riga in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if scritture.search(riga) and ("RAW" in riga or "raw_dir" in riga):
                colpevoli.append(f"{p.name}:{n}: {riga.strip()}")
    assert not colpevoli, "scrittura sotto data/raw/:\n" + "\n".join(colpevoli)


def test_config_non_crea_la_cartella_del_grezzo():
    """`config.py` crea PROCESSED, REPORTS e FIGURES perche' sono rigenerabili.
    Su `raw/` non deve: una cartella creata a vuoto invita a scriverci."""
    sorgente = (ROOT / "sot" / "config.py").read_text(encoding="utf-8")
    corpo = sorgente.split("for _d in (")[-1].split(")")[0]
    assert "RAW" not in corpo, corpo


# --------------------------------------------------------------------------
# 6. La radice resta pulita
# --------------------------------------------------------------------------
def test_niente_scraper_ne_residui_del_fork_in_radice():
    vietati = ["main.py", "Scrape matches.py", "scrape_serie_a_2025_2026.py",
               "utils.py", "tiri_in_porta.py", "test.py", "visuals.py",
               "linecollection.py", "EPV_grid.csv", "tutorial.ipynb",
               "logo.jpg", "serie_a_2025_2026_events.csv", "events.csv"]
    presenti = [f for f in vietati if (ROOT / f).exists()]
    assert not presenti, f"tornati in radice: {presenti}"


def test_lo_scraper_sta_in_acquisition():
    for f in ("main.py", "scrape_matches.py", "scrape_season.py", "utils.py"):
        assert (ROOT / "acquisition" / "whoscored" / f).is_file(), f
