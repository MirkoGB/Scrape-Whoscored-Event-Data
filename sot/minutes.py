"""Ricostruzione di minuti giocati, ruoli e rose dagli eventi.

I minuti NON sono memorizzati nei CSV: il blocco JSON ricco di WhoScored
(`home.players`, `isFirstEleven`, `position`) viene scartato in fase di
scraping da `createEventsDF`. Vanno ricostruiti dagli eventi.

Fonti usate:

* `FormationSet` (period = PreMatch, uno per squadra) — il qualifier
  `InvolvedPlayers` elenca la rosa convocata; i **primi 11 sono i titolari**.
  Il qualifier `PlayerPosition`, allineato posizionalmente, da' il ruolo con
  un codice numerico verificato empiricamente sulla stagione:
      1 = Portiere    (760 occorrenze, esattamente una per squadra-partita,
                       x medio dei tocchi 11.2)
      2 = Difensore   (x medio 39.6)
      3 = Centrocampista (x medio 52.4)
      4 = Attaccante  (x medio 62.3)
  La monotonia di x nel codice conferma la mappatura.
* `SubstitutionOn` / `SubstitutionOff` — entrata e uscita, su `expandedMinute`
  (che include il recupero).
* `Card` con `cardType` di espulsione — chiude i minuti del giocatore.
* `maxMinute` — durata effettiva della partita.

Convenzione: i minuti sono calcolati su `expandedMinute`, quindi una partita
dura tipicamente 94-99 minuti, non 90. Questo e' voluto: il tasso per 90
minuti usato nella Fase 3 divide per 90, e usare i minuti reali evita di
gonfiare i tassi di chi gioca le partite lunghe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import io_events

# Codice 5 = "sostituto": WhoScored non registra il ruolo dei panchinari nel
# FormationSet, li marca tutti con 5. Il ruolo di chi non e' mai titolare va
# quindi dedotto (vedi `season_roles`).
ROLE_BY_CODE = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
SUB_CODE = 5

# cardType che comportano l'uscita dal campo.
SENDING_OFF = {"Red", "SecondYellow"}

# Eventi che solo un portiere puo' produrre.
GK_EVENT_TYPES = ("Claim", "KeeperPickup", "KeeperSweeper", "Punch", "Smother")


def squads(lineup: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rosa convocata per squadra-partita, con ruolo e flag titolare.

    Una riga per (matchId, teamId, playerId).
    """
    if lineup is None:
        lineup = io_events.load_lineup_events()

    fs = lineup[lineup["type"] == "FormationSet"]
    rows = []
    for r in fs.itertuples(index=False):
        q = io_events.parse_qualifiers(r.qualifiers)
        involved = [int(v) for v in str(q.get("InvolvedPlayers", "")).split(",") if v.strip()]
        positions = [int(v) for v in str(q.get("PlayerPosition", "")).split(",") if v.strip()]
        for slot, pid in enumerate(involved):
            code = positions[slot] if slot < len(positions) else np.nan
            rows.append(
                {
                    "matchId": r.matchId,
                    "teamId": r.teamId,
                    "h_a": r.h_a,
                    "playerId": pid,
                    "slot": slot,
                    "is_starter": slot < 11,
                    "role_code": code,
                    "maxMinute": r.maxMinute,
                }
            )
    sq = pd.DataFrame(rows)
    sq["role"] = sq["role_code"].map(ROLE_BY_CODE).fillna("UNK")
    return sq


def match_duration(events: pd.DataFrame) -> pd.Series:
    """Durata effettiva per partita, in minuti espansi.

    Non si usa `maxMinute` da solo: in 15 partite su 380 e' **minore**
    dell'ultimo evento registrato. Esempio: in Napoli-Pisa (1901084)
    `maxMinute` vale 96 ma c'e' una sostituzione al 97' espanso. Prendendo il
    massimo fra i due il conteggio dei minuti torna esatto.
    """
    by_max = events.groupby("matchId")["maxMinute"].max()
    by_evt = events.groupby("matchId")["expandedMinute"].max()
    return by_max.combine(by_evt, max).rename("duration")


def minutes_played(lineup: pd.DataFrame | None = None,
                   events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Minuti giocati per (matchId, teamId, playerId).

    Chi e' in panchina e non entra compare con 0 minuti: serve per non
    confondere "non ha tirato" con "non ha giocato" nella Fase 3.
    """
    if lineup is None:
        lineup = io_events.load_lineup_events()
    if events is None:
        events = io_events.load_events()

    sq = squads(lineup)
    dur = match_duration(events)
    sq["maxMinute"] = sq["matchId"].map(dur).astype(float)

    on = (lineup[lineup["type"] == "SubstitutionOn"]
          .groupby(["matchId", "teamId", "playerId"])["expandedMinute"].min()
          .rename("min_on").reset_index())
    off = (lineup[lineup["type"] == "SubstitutionOff"]
           .groupby(["matchId", "teamId", "playerId"])["expandedMinute"].max()
           .rename("min_off").reset_index())

    cards = lineup[lineup["type"] == "Card"].copy()
    red = (cards[cards["cardType"].isin(SENDING_OFF)]
           .groupby(["matchId", "teamId", "playerId"])["expandedMinute"].min()
           .rename("min_red").reset_index())

    for frame in (on, off, red):
        frame["playerId"] = frame["playerId"].astype("Int64")

    sq["playerId"] = sq["playerId"].astype("Int64")
    df = (sq.merge(on, on=["matchId", "teamId", "playerId"], how="left")
            .merge(off, on=["matchId", "teamId", "playerId"], how="left")
            .merge(red, on=["matchId", "teamId", "playerId"], how="left"))

    # Inizio: 0 per i titolari, minuto di ingresso per i subentrati.
    start = np.where(df["is_starter"], 0.0, df["min_on"].astype("float64"))

    # Fine: la prima tra uscita, espulsione e fine partita.
    end = df[["min_off", "min_red"]].astype("float64").min(axis=1)
    end = end.fillna(df["maxMinute"].astype("float64"))

    played = ~np.isnan(start)
    df["start_min"] = np.where(played, start, np.nan)
    df["end_min"] = np.where(played, end.to_numpy(), np.nan)
    df["minutes"] = np.clip(np.where(played, end.to_numpy() - start, 0.0), 0.0, None)

    return df[["matchId", "teamId", "h_a", "playerId", "role", "role_code",
               "is_starter", "start_min", "end_min", "minutes", "maxMinute"]]


def on_pitch_at(mins: pd.DataFrame, keys: pd.DataFrame,
                minute_col: str = "expandedMinute") -> np.ndarray:
    """Per ogni riga di `keys`, dice se quel giocatore era in campo a quel minuto."""
    j = keys.merge(mins[["matchId", "teamId", "playerId", "start_min", "end_min"]],
                   on=["matchId", "teamId", "playerId"], how="left")
    t = j[minute_col].astype(float)
    return ((j["start_min"] <= t) & (t <= j["end_min"])).fillna(False).to_numpy()


def season_roles(mins: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Ruolo di stagione per ogni giocatore.

    WhoScored marca ogni panchinaro con il codice 5 ("sostituto") e non ne
    registra la posizione, quindi il ruolo non e' leggibile direttamente per
    chi non e' mai stato titolare. Procedura in due passi:

    1. Chi e' stato titolare almeno una volta prende il ruolo **modale** fra
       le partite da titolare (pesato sui minuti).
    2. Per chi non e' mai partito titolare il ruolo si deduce dai dati:
       portiere se produce eventi che solo un portiere puo' produrre
       (parate, uscite, prese); altrimenti il ruolo il cui centroide di x
       medio dei tocchi e' piu' vicino al suo.

    Il passo 2 e' una stima, e i giocatori che ne dipendono sono etichettati
    con `role_inferred = True` per poterli isolare nei report.
    """
    starters = mins[(mins["is_starter"]) & (mins["role_code"].isin(ROLE_BY_CODE))]
    modal = (starters.groupby(["playerId", "role"])["minutes"].sum()
             .reset_index()
             .sort_values("minutes")
             .groupby("playerId").tail(1)[["playerId", "role"]])
    modal["role_inferred"] = False

    known = set(modal["playerId"])
    unknown = sorted(set(mins.loc[mins["minutes"] > 0, "playerId"]) - known)
    if not unknown:
        return modal

    touches = events[events["isTouch"] & events["playerId"].notna()].copy()
    touches["playerId"] = touches["playerId"].astype("int64")

    # Centroidi di x per ruolo, calcolati sui soli titolari con ruolo noto.
    ref = touches.merge(
        starters[["matchId", "teamId", "playerId", "role"]].astype({"playerId": "int64"}),
        on=["matchId", "teamId", "playerId"], how="inner")
    centroids = ref.groupby("role")["x"].mean()

    mean_x = touches[touches["playerId"].isin(unknown)].groupby("playerId")["x"].mean()
    gk_ids = set(touches.loc[touches["type"].isin(GK_EVENT_TYPES), "playerId"])

    rows = []
    for pid in unknown:
        if pid in gk_ids:
            role = "GK"
        elif pid in mean_x.index:
            role = (centroids.drop(labels=["GK"], errors="ignore") - mean_x[pid]).abs().idxmin()
        else:
            role = "UNK"
        rows.append({"playerId": pid, "role": role, "role_inferred": True})

    return pd.concat([modal, pd.DataFrame(rows)], ignore_index=True)


def sending_off_minutes(lineup: pd.DataFrame, mins: pd.DataFrame,
                        duration: pd.Series | None = None) -> pd.DataFrame:
    """Minuti persi perche' la squadra e' rimasta in inferiorita' numerica.

    Non tutte le espulsioni tolgono un uomo dal campo. Sulla stagione ci sono
    85 cartellini di espulsione, ma:

    * **17 hanno `playerId` nullo**: sono espulsioni ad allenatore o staff.
      WhoScored le registra come evento della squadra senza giocatore. Non
      cambiano gli undici in campo.
    * **alcune vanno a giocatori non in campo**: chi era gia' stato sostituito
      (Pezzella al 101' dopo essere uscito al 77') e chi era in panchina. In
      Cremonese-Verona (1901432) tre rossi arrivano fra il 76' e il 77', ma
      due dei tre giocatori non erano in campo.

    Restano 65 espulsioni effettive su 85. Contarle tutte falsava il controllo
    dei minuti su 31 partite su 760.
    """
    cards = lineup[(lineup["type"] == "Card")
                   & (lineup["cardType"].isin(SENDING_OFF))
                   & (lineup["playerId"].notna())].copy()
    empty = pd.DataFrame(columns=["matchId", "teamId", "lost_minutes"])
    if cards.empty:
        return empty
    cards["playerId"] = cards["playerId"].astype("Int64")
    cards = cards[on_pitch_at(mins, cards)]
    if cards.empty:
        return empty

    if duration is not None:
        end = cards["matchId"].map(duration).astype(float)
    else:
        end = cards["maxMinute"].astype(float)
    cards["lost"] = end.to_numpy() - cards["expandedMinute"].astype(float).to_numpy()
    return (cards.groupby(["matchId", "teamId"])["lost"].sum()
            .rename("lost_minutes").reset_index())


def check_minutes(mins: pd.DataFrame, lineup: pd.DataFrame,
                  duration: pd.Series | None = None) -> pd.DataFrame:
    """Diagnostica: minuti totali vs 11 x durata, al netto delle espulsioni.

    L'attesa corretta e' `11 * durata - minuti persi per espulsione`. Senza il
    secondo termine il controllo segnala falsi positivi: la partita
    1901413/Pisa (due espulsioni, al 22' e al 58') totalizza 881 minuti contro
    979, e 881 e' il valore giusto.
    """
    g = mins.groupby(["matchId", "teamId"]).agg(
        tot_minutes=("minutes", "sum"),
        max_minute=("maxMinute", "first"),
        n_players=("playerId", "size"),
        n_played=("minutes", lambda s: (s > 0).sum()),
    ).reset_index()

    g = g.merge(sending_off_minutes(lineup, mins, duration),
                on=["matchId", "teamId"], how="left")
    g["lost_minutes"] = g["lost_minutes"].fillna(0.0)
    g["expected"] = 11.0 * g["max_minute"] - g["lost_minutes"]
    g["diff"] = g["tot_minutes"] - g["expected"]
    g["ratio"] = g["tot_minutes"] / g["expected"]
    return g
