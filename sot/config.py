"""Costanti, percorsi e seed. Unico punto in cui si fissa la casualita'."""

from pathlib import Path

# --------------------------------------------------------------------------
# Riproducibilita'
# --------------------------------------------------------------------------
SEED = 42

# --------------------------------------------------------------------------
# Percorsi
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW_MATCH_DIR = DATA / "serie_a_2025_2026"
MATCHES_JSON = DATA / "serie_a_2025_2026_matches.json"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

EVENTS_SLIM = PROCESSED / "events_slim.parquet"
SHOTS_PARQUET = PROCESSED / "shots.parquet"
TEAM_MATCH = PROCESSED / "team_match.parquet"
PLAYER_MATCH = PROCESSED / "player_match.parquet"

for _d in (PROCESSED, REPORTS, FIGURES):
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
