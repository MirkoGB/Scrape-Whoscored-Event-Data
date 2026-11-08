"""Acquisizione esplicita G1-G5 e documenti Lega; cache mai sovrascritte."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from acquisition import manifest
from acquisition.fantacalcio.scrape_voti import sessione, scarica_stagione
from acquisition.fantacalcio.target import TargetVoti


def main():
    sources = json.loads((ROOT / "fantacalcio_rose/calendario_fonti.json").read_text(encoding="utf-8"))
    with sessione() as session:
        scarica_stagione(session, TargetVoti(season=sources["stagione"]), range(1, 6))
        for source in sources["fonti"]:
            path = ROOT / source["cache"]
            if path.exists():
                continue
            time.sleep(3)
            response = session.get(source["url"], timeout=60)
            response.raise_for_status()
            content = response.content
            if path.suffix == ".pdf" and not content.startswith(b"%PDF"):
                raise ValueError(f"Documento non PDF: {source['url']}")
            if path.suffix == ".html" and (b"<html" not in content.lower() or b"2026" not in content):
                raise ValueError(f"Documento HTML inatteso: {source['url']}")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
            print(path)
    print(manifest.registra_fantacalcio(seasons=[sources["stagione"]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
