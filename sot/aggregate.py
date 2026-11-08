"""Costruzione delle due tabelle di lavoro della Fase 1, **per una stagione**.

`team_match`   760 righe (380 partite x 2 squadre)
`player_match` una riga per giocatore convocato per partita

Da qui in poi si lavora sui Parquet: gli eventi grezzi non vengono piu' letti.

Nota sulle squadre-partita a zero tiri: la tabella parte dall'elenco completo
delle 760 coppie (matchId, teamId) presenti negli eventi, non dal groupby dei
tiri. Altrimenti una squadra che non ha tirato sparirebbe dal campione invece
di comparire con 0, e la media di campionato risulterebbe gonfiata. Non e'
un'ipotesi: **esistono squadre-partita con zero tiri**, una nel 2021-22 e
Pisa-Cremonese del 2026-05-10.

Le due colonne aggiunte dalla Fase 9 / E0
-----------------------------------------
`stagione`  quale stagione e' questa riga. Senza, cinque tabelle concatenate
            non sono distinguibili e un `groupby` che dimentica la stagione
            mescola cinque regimi di annotazione diversi.

`stato`     titolare / subentrato / panchina. **Non aggiunge dati**: i convocati
            non impiegati erano gia' nella tabella con 0 minuti fin dalla Fase 1.
            Rende leggibile la differenza fra "convocato e mai entrato" e "dato
            mancante", che e' il bersaglio del blocco E2. Vedi `stato_impiego`
            per il quarto stato, che non ha un'etichetta perche' non ha una riga.

`xg_fit`    **quale fit di xG ha prodotto la colonna `xg` di questa riga.** Non
            e' ridondante rispetto a `stagione`, ed e' il punto: l'xG interno
            si stima **una stagione per volta** — CLAUDE.md lo vieta su piu'
            stagioni insieme perche' i suoi ingressi derivano (`shotCounter`
            3.4% -> 7.7% dei tentativi, `shotOpenPlay` -7.5 punti fra 2021-22 e
            2025-26). Ne segue che `xg` sta su **cinque scale diverse**, e
            senza questa colonna niente lo direbbe: qualcuno sommerebbe xG
            2021-22 e 2025-26 credendo di sommare la stessa grandezza.

            E' un'etichetta di **provenienza**, non una conversione. Non esiste
            e non va costruita una colonna `xg` confrontabile fra stagioni
            dentro questa tabella: la comparabilita' e' un fatto dello strato
            feature (blocco E1), non del derivato. Qui la deriva si porta
            avanti; normalizzarla via cancellerebbe un fatto misurato, ed e' il
            vincolo 4.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, features, io_events, minutes as mins_mod, shots as shots_mod, xg as xg_mod


def _base_team_match(events: pd.DataFrame, league: str = None,
                     season: str = None) -> pd.DataFrame:
    """Scheletro: tutte le 760 coppie squadra-partita, con data e avversario."""
    base = (events.groupby(["matchId", "teamId"])
            .agg(h_a=("h_a", "first"), date=("startDate", "first"))
            .reset_index())

    opp = base[["matchId", "teamId"]].rename(columns={"teamId": "opponentId"})
    base = base.merge(opp, on="matchId")
    base = base[base["teamId"] != base["opponentId"]].reset_index(drop=True)

    base["is_home"] = (base["h_a"] == "h").astype(int)

    names = io_events.team_id_map(events, league, season)
    base["team"] = base["teamId"].map(names)
    base["opponent"] = base["opponentId"].map(names)

    # Indice cronologico della partita per ciascuna squadra (1..38).
    # NON e' la giornata ufficiale: i recuperi la disallineano. La validazione
    # walk-forward usa comunque la data, non questo indice.
    base = base.sort_values(["teamId", "date"]).reset_index(drop=True)
    base["team_match_idx"] = base.groupby("teamId").cumcount() + 1

    return base


def etichetta_fit(league: str = None, season: str = None) -> str:
    """L'identita' del fit di xG che ha prodotto una riga: `campionato/stagione`.

    **Fino alla Fase 13 era la sola stagione, e non basta piu'.** E0 aveva
    stabilito che `xg_fit` non e' ridondante rispetto a `stagione` perche' l'xG
    interno si stima una stagione per volta, quindi i fit sono **cinque**. Con
    G2 i campionati diventano cinque e i fit **venticinque**: `"2025-2026"`
    identificherebbe cinque logistiche diverse, e la colonna direbbe una cosa
    falsa proprio nel momento in cui serve.

    E' lo stesso ragionamento di E0 applicato un piano piu' su, e la ragione per
    cui non si poolano i campionati e' la stessa per cui non si poolano le
    stagioni: E4 ha misurato che fra sole stagioni il livello dell'xG si muove
    del 15,8%.
    """
    league = config.LEAGUE if league is None else league
    season = config.SEASON if season is None else season
    return f"{league}/{season}"


def build_shots(events: pd.DataFrame, season: str = None,
                league: str = None) -> pd.DataFrame:
    """Tabella dei tiri con xG cross-fitted **su questa stagione soltanto**.

    `xg_fit` registra quale fit ha prodotto la colonna: vedi `etichetta_fit`.
    Il fit e' per costruzione quello della coppia campionato-stagione che si sta
    costruendo — ma "per costruzione" e' esattamente il tipo di cosa che smette
    di essere vera in silenzio, quindi si scrive.
    """
    sh = shots_mod.shot_frame(events)
    sh = sh.join(xg_mod.fit_predict_xg(sh))
    sh["xg_fit"] = etichetta_fit(league, season)
    return sh


def build_team_match(events: pd.DataFrame, shots: pd.DataFrame,
                     league: str = None, season: str = None) -> pd.DataFrame:
    base = _base_team_match(events, league, season)

    parts = [
        features.shot_context(shots),
        features.team_context(events),
        features.ppda(events),
    ]
    out = base
    for p in parts:
        out = out.merge(p, on=["matchId", "teamId"], how="left")

    count_cols = ["shots", "sot", "goals", "big_chances", "box_touches"]
    out[count_cols] = out[count_cols].fillna(0).astype(int)
    out["xg"] = out["xg"].fillna(0.0)

    # xG e distanza concessi: gli stessi valori, visti dall'avversario.
    conceded = out[["matchId", "teamId", "xg", "shots", "sot", "xg_per_shot"]].rename(
        columns={"teamId": "opponentId", "xg": "xg_conceded",
                 "shots": "shots_conceded", "sot": "sot_conceded",
                 "xg_per_shot": "xg_per_shot_conceded"})
    out = out.merge(conceded, on=["matchId", "opponentId"], how="left")

    out["campionato"] = config.LEAGUE if league is None else league
    out["stagione"] = config.SEASON if season is None else season
    out["xg_fit"] = etichetta_fit(league, season)

    cols = ["campionato", "stagione", "matchId", "date", "team", "teamId", "opponent", "opponentId",
            "is_home", "team_match_idx",
            "shots", "sot", "goals", "xg", "xg_per_shot", "big_chances",
            "mean_shot_distance", "possession", "field_tilt", "box_touches",
            "ppda", "def_actions",
            "shots_conceded", "sot_conceded", "xg_conceded", "xg_per_shot_conceded",
            "xg_fit"]
    return out[cols].sort_values(["date", "matchId", "is_home"]).reset_index(drop=True)


# Gli stati dell'impiego. Sono TRE nella tabella e QUATTRO nella realta': il
# quarto e' l'assenza di riga, e non ha un nome qui perche' non ha una riga a
# cui attaccarlo. Vedi `stato_impiego`.
STATI_IMPIEGO = ("titolare", "subentrato", "panchina")


def stato_impiego(pm: pd.DataFrame) -> pd.Series:
    """Da `is_starter` + `minutes` allo stato di impiego, come etichetta.

    **Non aggiunge dati: li rende leggibili.** I convocati non impiegati erano
    gia' in `player_match` fin dalla Fase 1 — 28.472 righe a zero minuti sulle
    cinque stagioni, il 32,6% della tabella — perche' `minutes.squads()` legge
    l'intera rosa da `InvolvedPlayers` del `FormationSet`, dove i panchinari
    stanno con `role_code = 5`. Ma erano leggibili solo da chi sapeva che
    `minutes == 0` significa "convocato e mai entrato" e non "dato mancante", e
    quella e' esattamente la distinzione che un modello dell'impiego non puo'
    permettersi di sbagliare.

        titolare     nei primi 11 di `InvolvedPlayers`
        subentrato   entrato dalla panchina (ha un `SubstitutionOn`)
        panchina     convocato e mai entrato, 0 minuti

    **Il quarto stato e' l'assenza della riga**: chi non e' stato convocato
    affatto — fuori lista, infortunato, squalificato, ceduto — non compare. Non
    ha un valore in questa colonna perche' non ha una riga, e chi ricostruisce
    l'impiego deve costruirsi il denominatore della rosa da fuori invece di
    contare le righe. E' un limite del derivato, non un difetto: WhoScored
    registra i convocati, non i tesserati.

    Un titolare ha sempre minuti > 0 (il suo `start_min` e' 0), quindi i tre
    stati sono una **partizione** e non si sovrappongono: verificato riga per
    riga da un test.
    """
    import numpy as np
    return pd.Series(
        np.where(pm["is_starter"], "titolare",
                 np.where(pm["minutes"] > 0, "subentrato", "panchina")),
        index=pm.index, dtype="object")


def build_player_match(events: pd.DataFrame, shots: pd.DataFrame,
                       lineup: pd.DataFrame, league: str = None,
                       season: str = None) -> pd.DataFrame:
    mins = mins_mod.minutes_played(lineup, events)
    roles = mins_mod.season_roles(mins, events)

    sh = shots.dropna(subset=["playerId"]).copy()
    sh["playerId"] = sh["playerId"].astype("int64")
    per_player = sh.groupby(["matchId", "teamId", "playerId"]).agg(
        shots=("is_sot", "size"),
        sot=("is_sot", "sum"),
        goals=("is_goal", "sum"),
        xg=("xg", "sum"),
    ).reset_index()
    per_player["playerId"] = per_player["playerId"].astype("Int64")

    out = mins.merge(per_player, on=["matchId", "teamId", "playerId"], how="left")
    for c in ["shots", "sot", "goals"]:
        out[c] = out[c].fillna(0).astype(int)
    out["xg"] = out["xg"].fillna(0.0)

    # Ruolo di stagione (quello per-partita e' assente per i panchinari).
    out = out.drop(columns=["role", "role_code"]).merge(roles, on="playerId", how="left")

    names = (events.dropna(subset=["playerId"])
             .assign(playerId=lambda d: d["playerId"].astype("int64"))
             .groupby("playerId")["playerName"].first())
    out["playerName"] = out["playerId"].map(names)

    meta = _base_team_match(events, league, season)[
        ["matchId", "teamId", "team", "opponent", "is_home", "date", "team_match_idx"]]
    out = out.merge(meta, on=["matchId", "teamId"], how="left")

    out["campionato"] = config.LEAGUE if league is None else league
    out["stagione"] = config.SEASON if season is None else season
    out["xg_fit"] = etichetta_fit(league, season)
    out["stato"] = stato_impiego(out)

    cols = ["campionato", "stagione", "matchId", "date", "team", "teamId", "opponent", "is_home",
            "team_match_idx", "playerId", "playerName", "role", "role_inferred",
            "stato", "is_starter", "minutes", "shots", "sot", "goals", "xg", "xg_fit"]
    return out[cols].sort_values(["date", "matchId", "teamId", "minutes"],
                                 ascending=[True, True, True, False]).reset_index(drop=True)


def run(force: bool = False, league: str = None,
        season: str = None) -> dict[str, pd.DataFrame]:
    """Costruisce e salva le tabelle di Fase 1 per **una** stagione.

    Senza argomenti fa esattamente quello che faceva prima della Fase 9: la
    coppia pubblicata, negli stessi percorsi.
    """
    events = io_events.load_events(force=force, league=league, season=season)
    lineup = io_events.load_lineup_events(league=league, season=season)

    shots = build_shots(events, season, league)
    team = build_team_match(events, shots, league, season)
    player = build_player_match(events, shots, lineup, league, season)

    shots.to_parquet(config.shots_parquet(league, season), index=False)
    team.to_parquet(config.team_match(league, season), index=False)
    player.to_parquet(config.player_match(league, season), index=False)

    return {"shots": shots, "team_match": team, "player_match": player}


def load_team_match(league: str = None, season: str = None) -> pd.DataFrame:
    return pd.read_parquet(config.team_match(league, season))


def load_player_match(league: str = None, season: str = None) -> pd.DataFrame:
    return pd.read_parquet(config.player_match(league, season))
