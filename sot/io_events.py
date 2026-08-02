"""Lettura dei 380 CSV WhoScored e cache su Parquet.

Scelte di pulizia dati, tutte deliberate e documentate nel README:

1. `isOwnGoal` e' assente in 358 file su 380 (pandas la emette solo quando in
   quella partita c'e' stato almeno un autogol). Viene forzata a False.
   Stesso trattamento per tutte le colonne booleane derivate da
   `satisfiedEventsTypes`, che seguono la stessa logica.

2. NON si deduplica su `id`. Nella stagione ci sono 30 collisioni di `id`, ma
   l'ispezione mostra che ogni collisione accoppia un evento `OffsideGiven`
   con un evento normale di minuto, squadra e tipo diversi: sono eventi
   genuinamente distinti a cui il feed ha assegnato lo stesso id, non record
   duplicati. Cancellarli perderebbe 30 eventi reali. La chiave unica
   effettiva e' (matchId, teamId, eventId), che ha zero duplicati.
   `eventId` da solo NON e' unico: e' numerato per squadra.

3. La concatenazione dei 380 file in un unico CSV da 1 GB non viene mai letta:
   si leggono i file per-partita, che sono la stessa cosa. La Fase 7A ha
   cancellato quella copia proprio perche' nessun modulo la apriva.
"""

from __future__ import annotations

import json
import ast
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

# Colonne "core" sempre richieste.
CORE_COLS = [
    "id", "eventId", "matchId", "teamId", "h_a", "type", "outcomeType",
    "minute", "second", "expandedMinute", "period",
    "playerId", "playerName", "x", "y", "endX", "endY",
    "isTouch", "isShot", "isGoal", "isOwnGoal",
    "blockedX", "blockedY", "goalMouthY", "goalMouthZ",
    "shotBodyType", "situation", "cardType",
    "startDate", "maxMinute",
]

# Colonne booleane derivate da satisfiedEventsTypes che ci servono.
BOOL_COLS = [
    # tiri
    "shotsTotal", "shotOnTarget", "shotOffTarget", "shotBlocked",
    "shotSixYardBox", "shotPenaltyArea", "shotOboxTotal",
    "shotOpenPlay", "shotCounter", "shotSetPiece", "shotDirectCorner",
    "shotRightFoot", "shotLeftFoot", "shotHead",
    "bigChanceMissed", "bigChanceScored", "bigChanceCreated",
    "goalOwn",
    # I rigori non sono marcati da `situation` (che resta nulla): l'unica
    # traccia e' il qualifier `Penalty`, equivalente all'unione di queste due
    # colonne. L'unione copre tutti i 106 rigori della stagione e, essendo
    # unione di segnati e sbagliati, non rivela l'esito.
    "penaltyScored", "penaltyMissed",
    # possesso / pressing
    "touches", "passAccurate", "passInaccurate",
    "tackleWon", "tackleLost", "interceptionAll", "challengeLost",
    "foulCommitted", "clearanceTotal",
    "defensiveThird", "midThird", "finalThird",
]

ALL_COLS = CORE_COLS + BOOL_COLS + ["qualifiers"]

# Eventi per cui conserviamo la colonna `qualifiers` (stringa pesante):
# servono per ricostruire formazioni, minuti ed espulsioni.
LINEUP_TYPES = ("FormationSet", "FormationChange",
                "SubstitutionOn", "SubstitutionOff", "Card")


def _read_one(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Legge un CSV partita. Ritorna (eventi senza qualifiers, eventi lineup)."""
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in ALL_COLS if c in header]
    df = pd.read_csv(path, usecols=use, low_memory=False)

    # Colonne mancanti (isOwnGoal e booleane non emesse) -> False / NaN.
    for col in BOOL_COLS + ["isOwnGoal", "isShot", "isGoal", "isTouch"]:
        if col not in df.columns:
            df[col] = False
        df[col] = df[col].astype("boolean").fillna(False).astype(bool)

    for col in CORE_COLS:
        if col not in df.columns:
            df[col] = np.nan

    # `cardType` e `situation`/`shotBodyType` sono object misti: pandas scrive
    # False dove il campo e' assente e una stringa dove e' presente. Uniformiamo
    # a stringa/NA, altrimenti Arrow rifiuta la colonna.
    for col in ("cardType", "situation", "shotBodyType", "outcomeType", "period",
                "type", "h_a", "playerName"):
        df[col] = df[col].map(lambda v: v if isinstance(v, str) else pd.NA)
        df[col] = df[col].astype("string")

    lineup = df.loc[df["type"].isin(LINEUP_TYPES),
                    ["matchId", "teamId", "h_a", "type", "period", "minute",
                     "expandedMinute", "playerId", "playerName", "cardType",
                     "maxMinute", "qualifiers"]].copy()

    return df.drop(columns=["qualifiers"]), lineup


def build_cache(force: bool = False) -> None:
    """Costruisce le cache Parquet dai 380 CSV. Idempotente."""
    slim_p = config.EVENTS_SLIM
    lineup_p = config.PROCESSED / "lineup_events.parquet"
    if slim_p.exists() and lineup_p.exists() and not force:
        return

    files = sorted(config.RAW_MATCH_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"nessun CSV in {config.RAW_MATCH_DIR}")

    ev_parts, lu_parts = [], []
    for f in files:
        ev, lu = _read_one(f)
        ev_parts.append(ev)
        lu_parts.append(lu)

    events = pd.concat(ev_parts, ignore_index=True)
    lineup = pd.concat(lu_parts, ignore_index=True)

    events["startDate"] = pd.to_datetime(events["startDate"])
    events["matchId"] = events["matchId"].astype("int64")
    events["teamId"] = events["teamId"].astype("int64")

    events.to_parquet(slim_p, index=False)
    lineup.to_parquet(lineup_p, index=False)


def load_events(force: bool = False) -> pd.DataFrame:
    """Tabella eventi (senza qualifiers), dalla cache."""
    build_cache(force=force)
    return pd.read_parquet(config.EVENTS_SLIM)


def load_lineup_events(force: bool = False) -> pd.DataFrame:
    """Eventi di formazione/sostituzione/cartellino, con qualifiers."""
    build_cache(force=force)
    return pd.read_parquet(config.PROCESSED / "lineup_events.parquet")


def parse_qualifiers(raw: str) -> dict:
    """I qualifiers sono repr Python (apici singoli), non JSON.

    `json.loads` fallisce; serve `ast.literal_eval`.
    """
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        items = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return {}
    return {d["type"]: d.get("value") for d in items if isinstance(d, dict)}


def team_names() -> pd.DataFrame:
    """Mappa (matchId, h_a) -> nome squadra, e teamId -> nome.

    I CSV contengono solo `teamId`: i nomi esistono unicamente nel JSON dei
    calendari, che va incrociato su matchId + casa/trasferta.
    """
    with open(config.MATCHES_JSON, encoding="utf-8") as fh:
        raw = json.load(fh)
    rows = []
    for m in raw:
        mid = int(m["url"].split("/")[2])
        rows.append({"matchId": mid, "h_a": "h", "team": m["home"]})
        rows.append({"matchId": mid, "h_a": "a", "team": m["away"]})
    return pd.DataFrame(rows)


def team_id_map(events: pd.DataFrame) -> dict[int, str]:
    """teamId -> nome squadra, per voto di maggioranza sulle 38 partite."""
    pairs = (events.groupby(["matchId", "teamId"])["h_a"].first()
             .reset_index()
             .merge(team_names(), on=["matchId", "h_a"], how="left"))
    counts = pairs.groupby(["teamId", "team"]).size().reset_index(name="n")
    best = counts.sort_values("n").groupby("teamId").tail(1)
    return dict(zip(best["teamId"], best["team"]))
