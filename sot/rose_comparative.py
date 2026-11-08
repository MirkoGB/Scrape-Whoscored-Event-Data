"""Fase B: snapshot descrittivi. Nessuna previsione o regola di lega implicita."""
from __future__ import annotations

import pandas as pd

from sot.rose import RoseError
from sot import voti as V

CLUB_NAMES = {"AC Milan": "Milan", "Parma Calcio 1913": "Parma"}
WS_METRICS = {"minutes": "minuti", "shots": "tiri", "sot": "sot",
              "goals": "gol_ws", "xg": "xg_interno"}
BONUS = V.COLONNE_BONUS + ["ammonizione", "espulsione"]


def unique(frame, keys, label):
    if frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise RoseError(f"{label}: chiavi mancanti o duplicate {keys}")


def calendar_bridge(partite, team_match, official, cutoff, ws_results):
    """La giornata viene dalla Lega; data e risultato effettivi dalle due fonti."""
    official = official[official.giornata.between(1, 5)].copy()
    unique(official, ["casa", "trasferta"], "Calendario ufficiale")
    if official.groupby("giornata").size().to_dict() != dict.fromkeys(range(1, 6), 10):
        raise RoseError("Calendario ufficiale G1-G5 incompleto")
    for _, group in official.groupby("giornata"):
        teams = pd.concat([group.casa, group.trasferta])
        if teams.nunique() != 20:
            raise RoseError("Squadra ripetuta nella giornata ufficiale")
    unique(partite, ["partita_id"], "Partite FC")
    unique(partite, ["casa", "trasferta"], "Partite FC")
    if len(partite) != len(official):
        raise RoseError("Numero partite FC diverso dal calendario ufficiale G1-G5")
    fc = official[["giornata", "casa", "trasferta"]].merge(
        partite, on=["casa", "trasferta"], how="left", validate="one_to_one",
        suffixes=("_ufficiale", ""))
    if fc.partita_id.isna().any() or not fc.giornata.eq(fc.giornata_ufficiale).all():
        raise RoseError("Voti e calendario ufficiale non concordano sulle giornate")
    unique(team_match, ["matchId", "teamId"], "Team-match WS")
    home = team_match[team_match.is_home.eq(1)].copy()
    away = team_match[team_match.is_home.eq(0)].copy()
    home["casa"] = home.team.replace(CLUB_NAMES)
    home["trasferta"] = home.opponent.replace(CLUB_NAMES)
    unique(home, ["casa", "trasferta"], "Partite WS")
    ws = home[["matchId", "date", "casa", "trasferta", "teamId", "opponentId", "goals"]].merge(
        away[["matchId", "goals"]], on="matchId", validate="one_to_one", suffixes=("_casa_ws", "_trasferta_ws"))
    # I gol da tiri escludono le autoreti: il risultato viene dal tabellino,
    # non da team_match.goals (Milan-Venezia G2 è un caso concreto).
    results = ws_results.copy()
    results["matchId"] = results.url.str.extract(r"/matches/(\d+)/")[0].astype(int)
    unique(results, ["matchId"], "Risultati WS")
    scores = results.score.str.extract(r"^(\d+)\s*:\s*(\d+)$")
    results["risultato_casa_ws"] = pd.to_numeric(scores[0])
    results["risultato_trasferta_ws"] = pd.to_numeric(scores[1])
    ws = ws.merge(results[["matchId", "risultato_casa_ws", "risultato_trasferta_ws"]],
                  on="matchId", how="left", validate="one_to_one")
    out = fc.merge(ws, on=["casa", "trasferta"], how="left", validate="one_to_one")
    if out.matchId.isna().any():
        raise RoseError("Copertura WS incompleta per G1-G5")
    if not (pd.to_datetime(out.data).eq(pd.to_datetime(out.date))).all():
        raise RoseError("Date effettive FC/WS divergenti: verificare recuperi")
    if not (out.gol_casa.eq(out.risultato_casa_ws) & out.gol_trasferta.eq(out.risultato_trasferta_ws)).all():
        raise RoseError("Risultati FC/WS divergenti")
    if pd.to_datetime(out.data).gt(pd.Timestamp(cutoff)).any():
        raise RoseError("Partita oltre il cutoff statistico")
    return out.drop(columns="giornata_ufficiale").sort_values(["giornata", "partita_id"])


def strict_sum(series):
    """Zero solo se osservato: anche un parziale ignoto rende il totale ignoto."""
    return None if series.empty or series.isna().any() else float(series.sum())


def ratio(value, denominator, factor=1):
    return None if value is None or denominator is None or denominator <= 0 else value * factor / denominator


def aggregate_votes(rows):
    rows = rows[~rows.allenatore].copy()
    unique(rows, ["partita_id", "giocatore_id"], "Voti giocatore-partita")
    result = {"copertura_fc": "osservata" if len(rows) else "assente",
              "righe_fc": len(rows), "club_fc_osservati": sorted(rows.squadra.dropna().unique().tolist()),
              "ruoli_fc_osservati": sorted(rows.ruolo.dropna().unique().tolist()),
              "ingressi_fc": strict_sum(rows.subentrato), "uscite_fc": strict_sum(rows.sostituito)}
    for scale in ("redazione", "statistico", "italia"):
        valid = rows[rows[f"voto_{scale}"].notna()]
        result.update({f"presenze_voto_{scale}": len(valid) if len(rows) else None,
                       f"sv_{scale}": int(rows[f"codice_sv_{scale}"].notna().sum()) if len(rows) else None,
                       f"voti_mancanti_{scale}": int((rows[f"voto_{scale}"].isna() & rows[f"codice_sv_{scale}"].isna()).sum()) if len(rows) else None,
                       f"media_voto_{scale}": ratio(strict_sum(valid[f"voto_{scale}"]), len(valid)),
                       f"media_fantavoto_fonte_{scale}": ratio(strict_sum(valid[f"fantavoto_{scale}"]), len(valid))})
    rated = rows[rows.voto_redazione.notna()]
    for col in BONUS:
        result[col] = strict_sum(rows[col])
        result[f"{col}_su_righe_a_voto"] = strict_sum(rated[col])
        result[f"{col}_per_voto"] = ratio(strict_sum(rated[col]), len(rated))
    result["gol_totali_fc"] = (result["gol_segnati"] + result["rigori_segnati"]
                                if result["gol_segnati"] is not None and result["rigori_segnati"] is not None else None)
    result["fantavoto_lega"] = None
    result["motivo_fantavoto_lega"] = "Regole di lega incomplete; FV fonte distinto dal punteggio di lega"
    return result


def aggregate_ws(rows, lineup, shots, team_match, rated_match_ids=()):
    unique(rows, ["campionato", "matchId", "playerId"], "Player-match WS")
    n = len(rows)
    out = {"copertura_ws": "osservata" if n else "assente",
           "righe_ws": n, "convocazioni_osservate": n if n else None,
           "presenze_effettive": int(rows.stato.isin(["titolare", "subentrato"]).sum()) if n else None,
           "titolare": strict_sum(rows.is_starter),
           "ingressi_ws": int(rows.stato.eq("subentrato").sum()) if n else None,
           "panchine_senza_ingresso": int(rows.stato.eq("panchina").sum()) if n else None,
           "club_ws_osservati": sorted(rows.team.dropna().unique().tolist()),
           "xg_fit": sorted(rows.xg_fit.dropna().unique().tolist()),
           "xg_confrontabile_tra_stagioni": False,
           "xa_provider": None}
    if n:
        pairs = rows[["matchId", "playerId"]]
        lu = lineup.merge(pairs, on=["matchId", "playerId"], how="inner", validate="many_to_one")
        sh = shots.merge(pairs, on=["matchId", "playerId"], how="inner", validate="many_to_one")
        out["uscite_ws"] = int(lu[lu.type.eq("SubstitutionOff")].matchId.nunique())
        scored = sh[sh.is_goal.eq(True)]
        out["gol_su_azione_ws"] = int((scored.shotOpenPlay.eq(True) | scored.shotCounter.eq(True)).sum())
        out["gol_rigore_ws"] = int(scored.penaltyScored.eq(True).sum())
        clubs = rows.teamId.unique()
        scope = team_match[team_match.teamId.isin(clubs)]
        out["partite_club_osservati"] = int(scope.matchId.nunique())
    else:
        out.update(uscite_ws=None, gol_su_azione_ws=None, gol_rigore_ws=None, partite_club_osservati=None)
    for source, field in WS_METRICS.items():
        out[field] = strict_sum(rows[source])
    for field in ("tiri", "sot", "gol_ws", "xg_interno"):
        out[f"{field}_per90"] = ratio(out[field], out["minuti"], 90)
    rated = rows[rows.matchId.isin(rated_match_ids)]
    out["presenze_voto_con_ws"] = len(rated) if n else None
    for source, field in WS_METRICS.items():
        out[f"{field}_su_righe_a_voto"] = strict_sum(rated[source])
        out[f"{field}_per_voto_appaiato"] = ratio(strict_sum(rated[source]), len(rated))
    return out


def team_context(team_match, official, team_name, bridge):
    name = CLUB_NAMES.get(team_name, team_name)
    rows = team_match[team_match.team.replace(CLUB_NAMES).eq(name)]
    if rows.empty:
        return {"club": name, "copertura": "assente"}
    result = {"club": name, "copertura": "osservata", "partite": len(rows),
              "avversari_affrontati": rows.sort_values("date").opponent.replace(CLUB_NAMES).tolist()}
    for field in ("shots", "sot", "xg", "shots_conceded", "sot_conceded", "xg_conceded"):
        result[field] = strict_sum(rows[field])
        result[f"{field}_per_partita"] = ratio(result[field], len(rows))
    home = bridge[bridge.casa.eq(name)]
    away = bridge[bridge.trasferta.eq(name)]
    result["goals"] = strict_sum(pd.concat([home.gol_casa, away.gol_trasferta]))
    result["goals_per_partita"] = ratio(result["goals"], len(rows))
    result["goals_conceded"] = strict_sum(pd.concat([home.gol_trasferta, away.gol_casa]))
    result["goals_conceded_per_partita"] = ratio(result["goals_conceded"], len(rows))
    result["prossime_5"] = []
    for r in official[official.giornata.between(6, 10) & (official.casa.eq(name) | official.trasferta.eq(name))].itertuples():
        result["prossime_5"].append(dict(giornata=r.giornata, data=r.data_programmata,
                                       avversario=r.trasferta if r.casa == name else r.casa,
                                       casa=r.casa == name))
    return result


def compare(current, historical):
    fields = ["media_voto_redazione", "media_fantavoto_fonte_redazione", "tiri_per90", "sot_per90", "gol_ws_per90"]
    return {field: current.get(field) - historical.get(field)
            if current.get(field) is not None and historical.get(field) is not None else None
            for field in fields}
