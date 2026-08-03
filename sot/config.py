"""Costanti, percorsi e seed. Unico punto in cui si fissa la casualita'."""

from pathlib import Path

# --------------------------------------------------------------------------
# Riproducibilita'
# --------------------------------------------------------------------------
SEED = 42

# --------------------------------------------------------------------------
# Tassonomia: campionato e stagione
#
# Unico posto in cui un campionato e una stagione hanno un nome. Prima della
# Fase 7 la coppia era incollata nel nome di una cartella
# (`data/serie_a_2025_2026/`) e non esisteva posto per una seconda stagione.
#
# Due scelte che sembrano cosmetiche e non lo sono:
#
# 1. La stagione e' `2025-2026`, non `2025-26` (il secondo anno a due cifre e'
#    ambiguo a cavallo di secolo) e non `2526` (e' la forma degli URL di
#    football-data.co.uk: adottarla farebbe entrare la convenzione di UNA fonte
#    nella struttura di tutte).
# 2. Il campionato e' `ITA-serie-a`, non `I1`. Stessa ragione: `I1` e' il codice
#    di una fonte. I codici delle fonti vivono qui dentro, in
#    LEAGUE_CODES, e si leggono al punto d'uso; non diventano nomi di cartella.
# --------------------------------------------------------------------------
SEASON_RE = r"^\d{4}-\d{4}$"

# Il valore di `whoscored` e' cio' che serve a comporre l'URL della competizione
# (`/regions/<regione>/tournaments/<torneo>/<slug>`). E' `None` dove non e' stato
# verificato: meglio un KeyError che un URL inventato che porta a un'altra
# competizione senza dirlo.
LEAGUE_CODES = {
    # cartella          football-data.co.uk   WhoScored
    "ITA-serie-a": {
        "football_data": "I1",
        "whoscored": {"regione": 108, "torneo": 5, "slug": "italy-serie-a"},
    },
    "ENG-premier-league":  {"football_data": "E0",  "whoscored": None},
    "ESP-la-liga":         {"football_data": "SP1", "whoscored": None},
    "GER-bundesliga":      {"football_data": "D1",  "whoscored": None},
    "FRA-ligue-1":         {"football_data": "F1",  "whoscored": None},
}

# Perimetro pubblicato delle Fasi 0-6. Le altre coppie campionato-stagione
# esistono nella tassonomia ma non hanno dati finche' la Fase 7 non li porta.
LEAGUE = "ITA-serie-a"
SEASON = "2025-2026"

# Perimetro storico dichiarato dall'utente in `docs/regole_fantacalcio.md` §5 e
# §7.1 (decisione 3): cinque stagioni complete. La 2025-26 e' l'unica in cui
# coesistono i minuti WhoScored e l's.v. osservato, quindi l'unica su cui la
# regola dell'80' e' falsificabile — le altre quattro servono a portare i minuti
# indietro, non a misurare.
#
# **La 2021-22 e' la prima stagione di ritorno del pubblico** dopo le
# restrizioni: il vantaggio del campo di quel periodo non e' confrontabile con
# quello delle successive, e va dichiarato accanto a ogni stima che lo
# attraversi (§5 dello stesso documento).
SEASONS_STORICHE = (
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
    "2025-2026",
)

# --------------------------------------------------------------------------
# Percorsi
#
# Tre alberi separati, e la separazione corrisponde a tre regole diverse:
#   raw/        grezzo, non si trasforma e non si sovrascrive mai;
#   processed/  interamente rigenerabile, cancellabile senza perdita;
#   external/   fornito a mano, provenienza da accertare caso per caso.
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
MANIFEST = RAW / "manifest.json"
EXTERNAL = DATA / "external"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"


def _check_season(season: str) -> str:
    """Rifiuta una stagione mal formata invece di costruire un percorso sbagliato.

    Un percorso costruito su `2025-26` non fallisce: crea silenziosamente una
    cartella accanto a quella giusta, e i dati si dividono in due senza che
    nessuno se ne accorga. Meglio l'eccezione.
    """
    import re
    if not re.match(SEASON_RE, season):
        raise ValueError(
            f"stagione {season!r} non conforme a {SEASON_RE} "
            "(attesa la forma 2025-2026, non 2025-26 ne' 2526)"
        )
    return season


def _check_league(league: str) -> str:
    if league not in LEAGUE_CODES:
        raise ValueError(
            f"campionato {league!r} non in LEAGUE_CODES: {sorted(LEAGUE_CODES)}"
        )
    return league


def raw_dir(fonte: str, league: str = None, season: str = None) -> Path:
    """Cartella del grezzo di una fonte per una coppia campionato-stagione."""
    league = _check_league(LEAGUE if league is None else league)
    season = _check_season(SEASON if season is None else season)
    return RAW / fonte / league / season


def processed_dir(league: str = None, season: str = None) -> Path:
    """Cartella degli elaborati per una coppia campionato-stagione."""
    league = _check_league(LEAGUE if league is None else league)
    season = _check_season(SEASON if season is None else season)
    return DATA / "processed" / league / season


def processed_league_dir(league: str = None) -> Path:
    """Cartella degli elaborati che **attraversano** le stagioni.

    Serve a cio' che confronta stagione con stagione — il primo caso e' la
    verifica di stabilita' del criterio di rilevazione. Metterlo dentro una
    delle cinque cartelle di stagione direbbe una cosa falsa: quel Parquet non
    appartiene a nessuna delle cinque.
    """
    league = _check_league(LEAGUE if league is None else league)
    return DATA / "processed" / league


# I NOMI di queste costanti non cambiano dalla Fase 0: cambia solo il loro
# valore. E' cio' che rende la riorganizzazione della Fase 7A invisibile a
# valle — nessun modulo fuori da questo file costruisce percorsi a mano.
RAW_MATCH_DIR = raw_dir("whoscored") / "events"
MATCHES_JSON = raw_dir("whoscored") / "matches.json"
PROCESSED = processed_dir()
PROCESSED_LEAGUE = processed_league_dir()

EVENTS_SLIM = PROCESSED / "events_slim.parquet"
SHOTS_PARQUET = PROCESSED / "shots.parquet"
TEAM_MATCH = PROCESSED / "team_match.parquet"
PLAYER_MATCH = PROCESSED / "player_match.parquet"

# Cache multi-stagione: i tiri delle cinque stagioni storiche e la presenza
# delle colonne file per file. Non appartiene a nessuna stagione, quindi non
# sta sotto PROCESSED.
SHOTS_ALL_SEASONS = PROCESSED_LEAGUE / "phase7_tiri_multistagione.parquet"
FILES_ALL_SEASONS = PROCESSED_LEAGUE / "phase7_colonne_multistagione.parquet"

for _d in (PROCESSED, PROCESSED_LEAGUE, REPORTS, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Modello
# --------------------------------------------------------------------------
HALF_LIFE_DAYS = 150.0          # decadimento esponenziale dei pesi
BURN_IN_ROUND = 6               # prima giornata valutata in walk-forward
OVER_LINE = 4.5                 # soglia binaria per il Brier score

# --------------------------------------------------------------------------
# Riferimenti esterni per il controllo di sanita' (Fase 0).
# Non sono target da inseguire: se i numeri divergono, la divergenza e' il
# risultato e va segnalata, non corretta cambiando la definizione di SoT.
# --------------------------------------------------------------------------
REF_LEAGUE_MEAN = 4.03
REF_HOME_MEAN = 4.43
REF_AWAY_MEAN = 3.63
REF_COMO_MEAN = 5.11
REF_N_MATCHES = 380
SANITY_TOLERANCE = 0.05         # 5%, come da specifica

# Proiezione top-down di riferimento per il 2026-27 (modello di persistenza su
# 21 stagioni, coefficienti 0.591 sull'ultima stagione e 0.247 sulla penultima).
REF_TOPDOWN_PER_MATCH = 4.90
REF_TOPDOWN_SEASON = 186
REF_TOPDOWN_PI80 = (152, 222)

# Geometria del campo in coordinate Opta (0-100 su entrambi gli assi).
GOAL_X = 100.0
GOAL_Y = 50.0
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
GOAL_WIDTH_M = 7.32
