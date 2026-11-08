"""Genera le schede G1-G5 / 2025-26 dai grezzi locali, senza rete."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from acquisition.fantacalcio.target import TargetVoti
from sot import voti as V
from sot.rose import RoseError, file_info
from sot.rose_comparative import (aggregate_votes, aggregate_ws, calendar_bridge,
                                 compare, team_context, unique)

SEASON = "2026-2027"
HISTORY = "2025-2026"


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso", force_ascii=False))


def fmt(value):
    if value is None:
        return "n.d."
    if isinstance(value, bool):
        return "sì" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", ",")
    return str(value).replace("|", "\\|")


def render_card(card):
    ident = card["identita"]
    current, old = card["corrente"], card["storico_serie_a"]
    lines = [f"# {ident['nome_fc']} — {ident['club_fc']}", "",
             f"ID FC {ident['giocatore_id_fc']} · WS {ident['playerId_ws']} · identità: {ident['stato']}",
             f"Ruoli correnti: {ident['ruolo_classic'].upper()} / {ident['ruolo_mantra']} (listone corrente).",
             "Statistiche 2026/27 congelate a G5, 20 settembre 2026. Confronto: intera stagione 2025/26.",
             "Redazione è una scala descrittiva, non una scelta del provider delle cinque leghe.", "",
             "| Grandezza | 2026/27 G1–G5 | 2025/26 Serie A |", "|---|---:|---:|"]
    fields = [("convocazioni_osservate", "Convocazioni osservate WS"), ("partite_club_osservati", "Partite dei club osservati nel dataset"),
              ("presenze_effettive", "Presenze effettive WS"), ("presenze_voto_redazione", "Presenze a voto Redazione"),
              ("sv_redazione", "Senza voto espliciti"), ("minuti", "Minuti (recupero incluso)"),
              ("titolare", "Da titolare"), ("ingressi_ws", "Ingressi WS"), ("uscite_ws", "Uscite WS"),
              ("media_voto_redazione", "Media voto Redazione"), ("media_fantavoto_fonte_redazione", "Media FV fonte Redazione"),
              ("tiri", "Tiri"), ("tiri_per90", "Tiri / 90'"), ("sot", "Tiri in porta"), ("sot_per90", "SoT / 90'"),
              ("presenze_voto_con_ws", "Presenze a voto appaiate a WS"), ("tiri_per_voto_appaiato", "Tiri / voto appaiato"),
              ("gol_totali_fc", "Gol totali FC"), ("gol_segnati", "Gol non su rigore FC (inclusi piazzati)"),
              ("gol_rigore_ws", "Gol su rigore WS"), ("gol_su_azione_ws", "Gol su azione/contropiede WS"),
              ("assist", "Assist assegnati FC"), ("assist_per_voto", "Assist / voto (sole righe a voto)"),
              ("ammonizione", "Ammonizioni FC"), ("espulsione", "Espulsioni FC"),
              ("gol_subiti", "Gol subiti FC"), ("autoreti", "Autoreti FC"),
              ("rigori_sbagliati", "Rigori sbagliati FC"), ("rigori_parati", "Rigori parati FC"),
              ("xg_interno", "xG interno (fit diversi, non comparabili)"), ("xg_interno_per90", "xG interno / 90' (fit diversi)")]
    lines += [f"| {label} | {fmt(current.get(field))} | {fmt(old.get(field))} |" for field, label in fields]
    lines += ["", "## Copertura e cambiamenti", "",
              f"FC corrente: {current['copertura_fc']}; WS corrente: {current['copertura_ws']}. "
              f"FC storico: {old['copertura_fc']}; WS storico: {old['copertura_ws']}.",
              f"Club FC storici: {', '.join(old['club_fc_osservati']) or 'n.d.'}; "
              f"ruoli FC storici: {', '.join(old['ruoli_fc_osservati']) or 'n.d.'}.",
              f"Cambio club: {fmt(card['cambio_club'])}; cambio ruolo Classic: {fmt(card['cambio_ruolo_classic'])}.",
              f"Ruoli Mantra nel listone storico: {', '.join(card['ruoli_mantra_storici']) or 'n.d.'}; "
              f"cambio Mantra: {fmt(card['cambio_ruolo_mantra'])}.",
              f"Fit xG corrente: {', '.join(current['xg_fit']) or 'n.d.'}; storico: {', '.join(old['xg_fit']) or 'n.d.'}.",
              "n.d. indica dato mancante; zero compare solo su osservazioni presenti. I minuti includono il recupero.",
              "Le partite dei club non provano l'eleggibilità del giocatore in tutte le gare, soprattutto in caso di trasferimento.",
              "FV di lega e xA del provider non disponibili. Notizie su infortuni/disponibilità non acquisite.",
              "Cinque giornate sono un campione ridotto; nessuna proiezione o graduatoria degli scambi.", ""]
    if card["storico_altri_campionati"]:
        lines += ["## Storico 2025/26 negli altri campionati", "",
                  "Collegamento sullo stesso ID WS verificato in Fase A; campionati mantenuti separati.", "",
                  "| Campionato | Presenze | Minuti | Tiri/90 | SoT/90 | Club |", "|---|---:|---:|---:|---:|---|"]
        for league, data in card["storico_altri_campionati"].items():
            lines.append(f"| {league} | {fmt(data['presenze_effettive'])} | {fmt(data['minuti'])} | {fmt(data['tiri_per90'])} | {fmt(data['sot_per90'])} | {', '.join(data['club_ws_osservati'])} |")
    lines += ["", f"Storico: {card['stato_storico']}. Nessun rendimento imputato ai giocatori senza copertura.",
              "", "## Contesto del club attuale", ""]
    ctx = card["contesto_squadra"]
    if ctx.get("copertura") == "osservata":
        lines += [f"Su {ctx['partite']} partite: tiri {fmt(ctx['shots_per_partita'])}, SoT {fmt(ctx['sot_per_partita'])}, "
                  f"gol {fmt(ctx['goals_per_partita'])}, gol subiti {fmt(ctx['goals_conceded_per_partita'])} per partita.",
                  f"Concessi: {fmt(ctx['shots_conceded_per_partita'])} tiri e {fmt(ctx['sot_conceded_per_partita'])} SoT per partita.",
                  "Avversari affrontati: " + ", ".join(ctx["avversari_affrontati"]) + ".", "",
                  "Prossime cinque giornate (programma ufficiale verificato il 6 ottobre 2026):", ""]
        lines += [f"- G{r['giornata']} · {r['data']} · {r['avversario']} ({'casa' if r['casa'] else 'trasferta'})" for r in ctx["prossime_5"]]
    else:
        lines.append("Contesto non disponibile: club non collegato.")
    lines += ["", "## Provenienza", "", "[Fonti, hash, metodo e limiti](../fase_b.md). "
              "Le tre scale di voto e tutti i denominatori sono in `../schede_comparative.json`.", "",
              f"Snapshot: `{card['snapshot_id']}`.", "",
              "Le rose e i club del listone sono correnti alla raccolta, non ricostruiti al cutoff: queste schede non sono un backtest."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/fantacalcio_scambi")
    args = parser.parse_args(argv)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    inputs = []

    def read_json(path):
        inputs.append(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def parquet(path):
        inputs.append(path)
        return pd.read_parquet(path)

    base = ROOT / "data/processed/ITA-serie-a"
    identities = read_json(out / "identita_giocatori.json")
    audit_a = read_json(out / "audit.json")
    rosters = read_json(out / "rose_per_lega.json")
    if audit_a["stagione"] != SEASON:
        raise RoseError("Fase B configurata per 2026/27; Fase A incompatibile")
    unique(pd.DataFrame(identities), ["giocatore_id_fc"], "Identità Fase A")
    official_path = ROOT / "fantacalcio_rose/calendario_ufficiale_2026_2027.csv"
    inputs.append(official_path)
    official = pd.read_csv(official_path)
    sources = read_json(ROOT / "fantacalcio_rose/calendario_fonti.json")
    inputs += [ROOT / f["cache"] for f in sources["fonti"]]
    for g in range(1, 6):
        path = TargetVoti(season=SEASON).percorso(g)
        if not path.is_file():
            raise RoseError("Voti mancanti: eseguire python -m acquisition.fantacalcio.scrape_voti --season 2026-2027 --giornata 1 2 3 4 5")
        inputs.append(path)
    votes, matches = V.costruisci(seasons=[SEASON], verbose=False, giornate=range(1, 6))
    votes = votes[votes.giornata.between(1, 5)].copy()
    matches = matches[matches.giornata.between(1, 5)].copy()
    residuals = V.riconciliazione(votes)
    if len(residuals):
        raise RoseError(f"Fantavoto fonte non riconciliato: {len(residuals)} righe")
    historical = parquet(V.VOTI_PARQUET)
    historical = historical[historical.stagione.eq(HISTORY) & ~historical.allenatore]
    quote_old = parquet(base / "fantacalcio_quotazioni.parquet")
    quote_old = quote_old[quote_old.stagione.eq(HISTORY)]
    inputs.append(ROOT / "data/mapping/aggancio_partite.csv")
    old_bridge = pd.read_csv(inputs[-1])
    old_bridge = old_bridge[old_bridge.stagione.eq(HISTORY)].dropna(subset=["matchId"])
    unique(old_bridge, ["partita_id"], "Ponte storico FC")
    unique(old_bridge, ["matchId"], "Ponte storico WS")
    data = {}
    for season in (SEASON, HISTORY):
        data[season] = {name: parquet(base / season / f"{name}.parquet")
                        for name in ("player_match", "team_match", "shots", "lineup_events")}
    ws_results = pd.DataFrame(read_json(ROOT / "data/raw/whoscored/ITA-serie-a" / SEASON / "matches.json"))
    bridge = calendar_bridge(matches, data[SEASON]["team_match"], official, "2026-09-20", ws_results)
    match_ids = set(bridge.matchId)
    data[SEASON] = {key: df[df.matchId.isin(match_ids)].copy() for key, df in data[SEASON].items()}
    foreign = {}
    for league in ("ENG-premier-league", "ESP-la-liga", "GER-bundesliga", "FRA-ligue-1"):
        folder = ROOT / "data/processed" / league / HISTORY
        foreign[league] = {name: parquet(folder / f"{name}.parquet")
                          for name in ("player_match", "team_match", "shots", "lineup_events")}
    inputs += [Path(__file__), ROOT / "scripts/acquisisci_fonti_fase_b.py", ROOT / "sot/rose_comparative.py", ROOT / "sot/voti.py",
               ROOT / "acquisition/fantacalcio/pagina.py", ROOT / "acquisition/fantacalcio/target.py"]
    manifest = [{**file_info(path), "percorso": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)} for path in inputs]
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    coverage = {league: {"partite": int(d["team_match"].matchId.nunique()),
                        "inizio": str(d["team_match"].date.min().date()), "fine": str(d["team_match"].date.max().date())}
                for league, d in {"ITA-serie-a": data[HISTORY], **foreign}.items()}
    contexts = {int(r.casa_id): r.casa for r in matches.itertuples()}
    contexts.update({int(r.trasferta_id): r.trasferta for r in matches.itertuples()})
    contexts = {key: team_context(data[SEASON]["team_match"], official, name, bridge) for key, name in contexts.items()}
    cards = []
    for ident in identities:
        fc_id, ws_id = ident["giocatore_id_fc"], ident["playerId_ws"]
        allowed = ident["stato"] in ("collegato", "collegato_solo_storico")
        if not allowed:
            ws_id = None
        periods = []
        for season, vv, bb in ((SEASON, votes, bridge), (HISTORY, historical, old_bridge)):
            player_votes = vv[vv.giocatore_id.eq(fc_id) & ~vv.allenatore]
            rated_ids = bb[bb.partita_id.isin(player_votes.loc[player_votes.voto_redazione.notna(), "partita_id"])].matchId
            d = data[season]
            pm = d["player_match"]
            selected = pm[pm.playerId.eq(ws_id)] if ws_id is not None else pm.iloc[:0]
            stats = {**aggregate_votes(player_votes), **aggregate_ws(selected, d["lineup_events"], d["shots"], d["team_match"], rated_ids)}
            stats["stagione"] = season
            stats["giornate"] = [1, 5] if season == SEASON else [1, 38]
            periods.append(stats)
        elsewhere = {}
        for league, d in foreign.items():
            selected = d["player_match"][d["player_match"].playerId.eq(ws_id)] if ws_id is not None else d["player_match"].iloc[:0]
            if len(selected):
                elsewhere[league] = aggregate_ws(selected, d["lineup_events"], d["shots"], d["team_match"])
                elsewhere[league]["copertura_campionato"] = coverage[league]
        previous = quote_old[quote_old.giocatore_id.eq(fc_id)]
        club_old = previous.squadra_id.dropna().unique().tolist()
        role_old = previous.ruolo_classic.dropna().unique().tolist()
        mantra_old = previous.ruolo_mantra.dropna().unique().tolist()
        status = ("storico_serie_a" if periods[1]["righe_fc"] or periods[1]["righe_ws"] else
                  "storico_solo_estero" if elsewhere else "storico_non_disponibile")
        memberships = [dict(lega=league["id"], squadra=team["nome"], mia_squadra=r["mia_squadra"], costo=r["costo"])
                       for league in rosters for team in league["squadre"] for r in team["rosa"] if r["giocatore_id_fc"] == fc_id]
        cards.append(dict(snapshot_id=digest, identita=ident, appartenenze=memberships,
                          corrente=periods[0], storico_serie_a=periods[1], storico_altri_campionati=elsewhere,
                          stato_storico=status, incertezza="campione_corrente_ridotto" if status != "storico_non_disponibile" else "elevata_senza_storico",
                          cambio_club=(ident["squadra_id_fc"] not in club_old) if club_old else None,
                          cambio_ruolo_classic=(ident["ruolo_classic"] not in role_old) if role_old else None,
                          cambio_ruolo_mantra=(ident["ruolo_mantra"] not in mantra_old) if mantra_old else None,
                          ruoli_mantra_storici=mantra_old,
                          criterio_cambi="Confronto listone corrente / listone 2025-26 (non cronologia trasferimenti)",
                          differenze=compare(periods[0], periods[1]),
                          contesto_squadra=contexts.get(ident["squadra_id_fc"], {"copertura": "assente"})))
    audit = dict(fase="B", snapshot_id=digest, generato_utc=datetime.now(timezone.utc).isoformat(),
                 stagione=SEASON, cutoff_statistiche="2026-09-20", data_decisione="2026-10-06",
                 partite=len(bridge), righe_voti=len(votes), righe_giocatori=int((~votes.allenatore).sum()),
                 righe_allenatori=int(votes.allenatore.sum()), riconciliazione_residui=len(residuals),
                 schede=len(cards), con_voti_correnti=sum(c["corrente"]["righe_fc"] > 0 for c in cards),
                 con_ws_corrente=sum(c["corrente"]["righe_ws"] > 0 for c in cards),
                 con_storico_estero=sum(bool(c["storico_altri_campionati"]) for c in cards),
                 stati_storico=dict(Counter(c["stato_storico"] for c in cards)), copertura_storica=coverage,
                 fonti=manifest, calendario_fonti=sources, fase_a_snapshot=audit_a["snapshot_id"])
    # Tutti i controlli sono conclusi prima di pubblicare gli elaborati.
    votes.to_parquet(out / "voti_2026_2027_g1_g5.parquet", index=False)
    votes.to_csv(out / "voti_2026_2027_g1_g5.csv", index=False)
    bridge.to_csv(out / "partite_g1_g5_verificate.csv", index=False)
    dump(out / "schede_comparative.json", cards)
    dump(out / "audit_fase_b.json", audit)
    flat = []
    for card in cards:
        row = {k: card["identita"][k] for k in ("giocatore_id_fc", "playerId_ws", "nome_fc", "club_fc", "ruolo_classic", "ruolo_mantra")}
        for period in ("corrente", "storico_serie_a"):
            row.update({f"{period}_{k}": v for k, v in card[period].items() if not isinstance(v, (dict, list))})
        row.update(stato_storico=card["stato_storico"], cambio_club=card["cambio_club"], cambio_ruolo_classic=card["cambio_ruolo_classic"])
        flat.append(row)
    flat_frame = pd.DataFrame(flat)
    for column in ("giocatore_id_fc", "playerId_ws"):
        flat_frame[column] = flat_frame[column].astype("Int64")
    flat_frame.to_csv(out / "schede_comparative.csv", index=False, encoding="utf-8-sig")
    folder = out / "schede"
    folder.mkdir(exist_ok=True)
    for card in cards:
        (folder / f"{card['identita']['giocatore_id_fc']}.md").write_text(render_card(card), encoding="utf-8")
    (out / "snapshots").mkdir(exist_ok=True)
    snapshot = out / "snapshots" / f"fase_b_{digest}.json"
    if not snapshot.exists():
        dump(snapshot, dict(audit=audit, schede=cards, voti=records(votes), partite=records(bridge)))
    lines = ["# Fantacalcio — Fase B", "", f"**{len(cards)} schede comparative**, {len(bridge)} partite G1–G5 verificate sul calendario ufficiale.",
             f"Voti: {audit['righe_giocatori']} righe giocatore e {audit['righe_allenatori']} allenatori esclusi dalle medie. "
             f"Residui nella ricostruzione FV Redazione: {len(residuals)}.",
             f"Schede con righe FC correnti: {audit['con_voti_correnti']}; con WS corrente: {audit['con_ws_corrente']}; "
             f"con storico estero per ID: {audit['con_storico_estero']}.", "",
             "Statistiche congelate al 20 settembre 2026 (G5); data della decisione: 6 ottobre 2026. "
             "Listone e rose correnti alla raccolta. Notizie su disponibilità/infortuni non acquisite.", "",
             "## Metodo e limiti", "",
             "- Join partite uno-a-uno su casa/trasferta, verifica giornata ufficiale, data effettiva e risultato FC/WS; nessun ordinamento delle prime cinque gare.",
             "- Identità della Fase A: ID FC per i voti, ID WS verificati per gli eventi e i quattro campionati esteri. Identità ambigue escluse dalle statistiche WS.",
             "- Media voto e FV fonte separati su tutte e tre le scale. Il FV delle leghe resta nullo perché i regolamenti sono incompleti.",
             "- Assenza di righe, s.v. e zero osservato restano distinti. Allenatori esclusi. I denominatori delle medie e dei tassi sono salvati nelle schede.",
             "- Tiri/SoT per voto: solo partite appaiate FC/WS con voto Redazione; i bonus per voto usano solo righe a voto, mentre i totali includono anche s.v.",
             "- Convocazioni WS osservate in distinta, non disponibilità presunta. Minuti comprensivi del recupero; assenza di riga non convertita in zero.",
             "- Risultati e gol di squadra comprendono le autoreti: verificati sul tabellino WS, non sui soli gol da tiro di team_match. Milan–Venezia G2: 2–0, un gol da tiro e un'autorete.",
             "- Storico 2025/26 intero, distinto per campionato. Copertura dei campionati e date nell'audit; assenza di storico aumenta l'incertezza, senza imputazioni.",
             "- xG interno con etichetta xg_fit conservata; fit distinti per stagione/campionato, confronto non validato e delta xG non calcolato. xA provider assente.",
             "- Calendario futuro G6–G10 verificato su fonte ufficiale il 6 ottobre; nessuna previsione sulla difficoltà. I cambi club/ruolo confrontano i listoni, non ricostruiscono i trasferimenti.", "",
             "## Fonti e riproduzione", ""]
    lines += [f"- [{f['documento']}]({f['url']})" for f in sources["fonti"]]
    lines += ["- [Voti Fantacalcio 2026/27](https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/5); URL di ogni giornata ricostruibile dal numero della pagina.",
              "- Hash, date dei file e fonti locali in `audit_fase_b.json`; provenienza riga voto nella colonna `pagina`.", "",
              "```powershell", "./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_b.py", "```", "",
              "Tabelle storiche e grezzi non vengono riscritti. Snapshot immutabile in `snapshots/fase_b_<hash>.json`.", "",
              "## Le mie rose", ""]
    for league in rosters:
        lines += [f"### {league['id']}", "", "| Giocatore | Ruolo | Minuti G1–G5 | Voti | MV | FM fonte | MV 2025/26 |", "|---|---|---:|---:|---:|---:|---:|"]
        for c in cards:
            if not any(m["lega"] == league["id"] and m["mia_squadra"] for m in c["appartenenze"]):
                continue
            i, s, h = c["identita"], c["corrente"], c["storico_serie_a"]
            lines.append(f"| [{i['nome_fc']}](schede/{i['giocatore_id_fc']}.md) | {i['ruolo_classic'].upper()} | {fmt(s['minuti'])} | {fmt(s['presenze_voto_redazione'])} | {fmt(s['media_voto_redazione'])} | {fmt(s['media_fantavoto_fonte_redazione'])} | {fmt(h['media_voto_redazione'])} |")
    lines += ["", "## Tutte le schede", ""]
    lines += [f"- [{c['identita']['nome_fc']} — {c['identita']['club_fc']}](schede/{c['identita']['giocatore_id_fc']}.md)" for c in cards]
    (out / "fase_b.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k not in ("fonti", "calendario_fonti")}, indent=2))
    print(f"Report: {out / 'fase_b.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
