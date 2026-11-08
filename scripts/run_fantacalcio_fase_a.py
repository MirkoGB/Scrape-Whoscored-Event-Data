"""Fase A: importazione verificata, identità, configurazioni. Nessuna rete."""
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

from acquisition.fantacalcio import pagina as P
from acquisition.fantacalcio.target import TargetQuote
from sot.rose import (RoseError, check_ownership, file_info, import_roster,
                      resolve_identities, rules_status)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, records):
    frame = pd.DataFrame(records)
    for col in frame.columns:
        if frame[col].map(lambda v: isinstance(v, (list, dict))).any():
            frame[col] = frame[col].map(lambda v: json.dumps(v, ensure_ascii=False)
                                       if isinstance(v, (list, dict)) else v)
        if col in ("giocatore_id_fc", "playerId_ws", "squadra_id_fc"):
            frame[col] = frame[col].astype("Int64")
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "fantacalcio_rose/leghe.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/fantacalcio_scambi")
    args = parser.parse_args(argv)
    settings = json.loads(args.config.read_text(encoding="utf-8"))
    if settings.get("versione_schema") != 1:
        raise RoseError("Versione configurazione non supportata")
    season = settings["stagione"]
    configs = settings["leghe"]
    if len({c['id'] for c in configs}) != len(configs):
        raise RoseError("Configurazioni lega duplicate")
    records, leagues = [], []
    inputs = [args.config, Path(__file__), ROOT / "sot/rose.py", ROOT / "sot/aggancio.py",
              ROOT / "acquisition/fantacalcio/pagina.py"]
    selected = set()
    for config in configs:
        paths = list(args.config.parent.glob(config["id"] + "-rosters-*.xlsx"))
        if len(paths) != 1:
            raise RoseError(f"{config['id']}: trovati {len(paths)} export; conservarne uno attivo per lega")
        path = paths[0]
        selected.add(path.name)
        entries, audit = import_roster(path, config["id"], config["mia_squadra"], config.get("foglio", "ROSE"))
        audit["configurazione"] = config
        audit["stato_regole"] = rules_status(config)
        records.extend(entries)
        leagues.append(audit)
        inputs.append(path)
    unexpected = {p.name for p in args.config.parent.glob("*.xlsx")} - selected
    if unexpected:
        raise RoseError(f"Export non configurati: {sorted(unexpected)}")

    raw = TargetQuote(season=season).percorso
    if not raw.exists():
        raise RoseError(f"Listone mancante. Acquisire con: python -m acquisition.fantacalcio.scrape_quote --season {season}")
    quotes = pd.DataFrame(P.analizza_quote(P.leggi(raw), season))
    base = ROOT / "data/processed/ITA-serie-a"
    historical_path = ROOT / "data/mapping/aggancio_giocatori.csv"
    teams_path = ROOT / "data/mapping/aggancio_squadre.csv"
    current_path = base / season / "player_match.parquet"
    aliases_path = args.config.parent / "alias_giocatori.json"
    aliases_doc = json.loads(aliases_path.read_text(encoding="utf-8"))
    if aliases_doc.get("versione_schema") != 1:
        raise RoseError("Versione alias non supportata")
    identities = resolve_identities(
        [r["giocatore"] for r in records], quotes, pd.read_csv(historical_path),
        pd.read_parquet(current_path), pd.read_csv(teams_path), season, aliases_doc["alias"])
    by_name = {r["nome_export"]: r for r in identities}
    for record in records:
        identity = by_name[record["giocatore"]]
        record.update({k: identity[k] for k in ("giocatore_id_fc", "nome_fc", "club_fc", "ruolo_classic",
                                               "ruolo_mantra", "playerId_ws", "copertura_ws_corrente")})
        record["stato_identita"] = identity["stato"]
        record["stagione_ruoli"] = season
    check_ownership(records)
    issues = [r for r in identities if r["stato"] not in ("collegato", "collegato_solo_storico")]
    inputs.extend([raw, historical_path, teams_path, current_path, aliases_path])
    manifest = [{**file_info(p), "percorso": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)}
                for p in inputs]
    manifest.append({"url": TargetQuote(season=season).url, "file": str(raw.relative_to(ROOT)),
                     "nota": "Listone corrente: ruoli/club alla data della raccolta, non snapshot pre-stagione."})
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    summary = {"fase": "A", "stagione": season, "snapshot_id": digest,
               "generato_utc": datetime.now(timezone.utc).isoformat(),
               "totale_squadre": sum(len(l["squadre"]) for l in leagues),
               "totale_tesseramenti": len(records), "nomi_distinti": len(identities),
               "identita_fc_risolte": sum(r["giocatore_id_fc"] is not None for r in identities),
               "stati_identita": dict(Counter(r["stato"] for r in identities)),
               "metodi_ws": dict(Counter(r["metodo_ws"] or "non_collegato" for r in identities)),
               "leghe": leagues, "fonti": manifest}
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "rose_normalizzate.csv", records)
    write_csv(out / "identita_giocatori.csv", identities)
    # Con colonne anche quando non esistono casi aperti.
    if issues:
        write_csv(out / "identita_da_verificare.csv", issues)
    else:
        pd.DataFrame(columns=list(identities[0])).to_csv(out / "identita_da_verificare.csv", index=False, encoding="utf-8-sig")
    write_json(out / "identita_giocatori.json", identities)
    write_json(out / "audit.json", summary)
    write_json(out / "rose_per_lega.json", [dict(id=l["lega"], squadre=[
        dict(**team, rosa=[r for r in records if r["lega"] == l["lega"] and r["squadra"] == team["nome"]])
        for team in l["squadre"]]) for l in leagues])
    snapshots = out / "snapshots"
    snapshots.mkdir(exist_ok=True)
    snapshot_path = snapshots / (digest + ".json")
    if not snapshot_path.exists():
        write_json(snapshot_path, {"audit": summary, "identita": identities, "rose": records})
    # Listone isolato: non riscrive le tabelle storiche usate dalle altre fasi.
    write_csv(out / f"listone_{season.replace('-', '_')}.csv", quotes.to_dict("records"))
    lines = ["# Fantacalcio — Fase A", "", f"Stagione di lavoro: {season}. Stato dei regolamenti riportato sotto.", "",
             f"Importate **{len(records)} assegnazioni**, **{summary['totale_squadre']} squadre**, "
             f"**{len(identities)} nomi**. Identità Fantacalcio risolte: **{summary['identita_fc_risolte']}**.", "",
             "| Lega | Mia squadra | Partecipanti | Rosa | Identità WS correnti |", "|---|---|---:|---:|---:|"]
    for l in leagues:
        mine = [r for r in records if r["lega"] == l["lega"] and r["mia_squadra"]]
        count = sum(r["stato_identita"] == "collegato" for r in mine)
        lines.append(f"| {l['lega']} | {l['configurazione']['mia_squadra']} | {len(l['squadre'])} | {len(mine)} | {count}/{len(mine)} |")
    lines += ["", "## Collegamenti WhoScored", ""]
    lines += [f"- {status}: {count}" for status, count in summary["stati_identita"].items()]
    lines += ["", "Le assenze dal dataset delle cinque giornate non sono presenze o minuti pari a zero.",
              "I collegamenti solo storici conservano l'ID, senza attribuire una squadra o un ruolo attuale dallo storico.",
              "I casi ambigui/conflittuali sono esclusi dall'uso automatico tramite stato_identita.",
              "", "## Casi da verificare", ""]
    lines += ([f"- {r['nome_export']} ({r['club_fc']}): {r['stato']}; candidati WS {r['candidati_ws']}" for r in issues]
              or ["Nessun conflitto o identità irrisolta."])
    lines += ["", "## Regole ancora mancanti", ""]
    for l in leagues:
        lines.append(f"- **{l['lega']}**: " + ", ".join(l["stato_regole"]["campi_da_confermare"]))
    lines += ["", "## Indicazioni già ricevute dall'utente", ""]
    for l in leagues:
        facts = l["configurazione"].get("dichiarazioni_utente", {})
        if facts:
            lines.append(f"- **{l['lega']}**: bonus difesa " + str(facts['difesa']['bonus_in_ordine']) +
                         ("; capitano attivo." if facts.get('capitano_attivo') else "; capitano non specificato."))
            lines.append("  Scatti di 0,25; fasce registrate: " + json.dumps(l['configurazione']['regole']['modificatori']['difesa'].get('fasce_complete'), ensure_ascii=False))
    lines += ["", "Le soglie sono registrate dalle indicazioni dell'utente; criterio della media e formula del capitano",
              "non sono stati dedotti. I regolamenti incompleti impediscono la valutazione numerica.", "",
              "Nota sull'audit iniziale: gli accenti degli XLSX sono integri. I caratteri apparentemente",
              "corrotti erano prodotti dalla visualizzazione del terminale. Viene normalizzato anche lo spazio finale di `Fini `."]
    lines += ["", "## Riproduzione", "", "```powershell", "./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_a.py", "```", "",
              "Le rose complete sono in `fantacalcio_scambi/rose_normalizzate.csv` e `rose_per_lega.json`.",
              "Identità, sorgenti e snapshot sono nella stessa cartella. Configurazioni modificabili in",
              "`fantacalcio_rose/leghe.json`; nessun regolamento è copiato da `sot/lega.py`.", "",
              "Il costo di acquisto resta un dato dell'export, non un valore di mercato o il budget iniziale.",
              "Nessuna valutazione di rendimento, proposta di scambio o dashboard è inclusa nella Fase A."]
    (out / "fase_a.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("leghe", "fonti")}, ensure_ascii=True, indent=2))
    print(f"Report: {out / 'fase_a.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
