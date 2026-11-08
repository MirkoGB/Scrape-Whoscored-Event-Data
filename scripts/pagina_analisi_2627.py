"""Genera il report HTML autonomo dai CSV dell'analisi, senza ristimare il modello."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sot import config, over_paper as OP


def scrivi() -> Path:
    names = {
        "metrics": "metriche", "matches": "partite", "coverage": "copertura",
        "totals": "totali", "brier": "brier",
    }
    data = {}
    for key, suffix in names.items():
        frame = pd.read_csv(config.REPORTS / f"analisi_2627_{suffix}.csv")
        data[key] = json.loads(frame.to_json(orient="records", force_ascii=False))
    data["report"] = (config.REPORTS / "analisi_2627_prestazioni.md").read_text(encoding="utf-8")
    over_path = config.REPORTS / "over_2627_stato.json"
    data["over"] = json.loads(over_path.read_text(encoding="utf-8")) if over_path.exists() else None
    if data["over"]:
        sisal_root = config.ROOT / 'data/external/paper_over/sisal'
        runs = OP.load_records(sisal_root / 'runs')
        data["over"]["sisal"] = {
            "last_run": max(runs, key=lambda r: r['finished_at']) if runs else None,
            "observations": OP.load_records(sisal_root / 'observations'),
        }
    # JSON incorporato: null per i valori mancanti e nessuna chiusura di script
    # possibile attraverso nomi di squadre o contenuto del report.
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    template = Path(__file__).with_name("templates") / "analisi_2627.html"
    output = config.REPORTS / "analisi_2627_prestazioni.html"
    html = template.read_text(encoding="utf-8").replace("__REPORT_DATA__", payload)
    panel = (template.parent / "over_panel.html").read_text(encoding="utf-8") if data["over"] else ""
    script = (template.parent / "over_panel.js").read_text(encoding="utf-8") if data["over"] else ""
    if data["over"]:
        panel = (template.parent / "suggestion_panel.html").read_text(encoding="utf-8") + panel
        script = "\n".join([
            (template.parent / "suggestion_engine.js").read_text(encoding="utf-8"),
            script,
            (template.parent / "suggestion_panel.js").read_text(encoding="utf-8"),
        ])
    html = html.replace('__OVER_PANEL__', panel).replace('__OVER_SCRIPT__', script)
    output.write_text(html, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(scrivi())
