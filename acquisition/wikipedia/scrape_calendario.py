# -*- coding: utf-8 -*-
"""Il calendario di stagione da Wikipedia: la SECONDA fonte, con la giornata.

    ./.venv/Scripts/python.exe -m acquisition.wikipedia.scrape_calendario --dry-run
    ./.venv/Scripts/python.exe -m acquisition.wikipedia.scrape_calendario

Cinque richieste per campionato (una per sezione), non una pagina intera per
volta: si usa l'API, che e' l'interfaccia dichiarata stabile dalla fonte.

**Perche' una seconda fonte**: quella di WhoScored porta gli URL e i `matchId`
ma NON la giornata, che quella pagina non espone affatto. Questa la porta. Le
due non sono ridondanti, e messe una contro l'altra sono il vincolo 7 a costo
quasi zero — vedi `sot/calendario.py`, che le riconcilia e **dichiara** le
divergenze invece di sceglierne una.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime as dt

import requests

from sot import config

from . import pagina as P
from . import target as T

#: Pausa fra una richiesta e l'altra. Wikipedia non chiede un minimo, ma la
#: cortesia verso una fonte gratuita e' la stessa disciplina applicata altrove.
PAUSA_S = 1.0


def _api(sessione, titolo: str, tentativi: int = 4, **extra) -> dict:
    """Una chiamata all'API, con attesa crescente sul 429.

    Wikipedia risponde **429 Too Many Requests** se la si interroga troppo in
    fretta, e ci e' successo alla prima esecuzione. Non e' un difetto della
    fonte: e' la sua condizione d'uso, e si rispetta aspettando invece di
    ritentare subito.
    """
    attesa = PAUSA_S
    for tentativo in range(1, tentativi + 1):
        r = sessione.get(T.API, params={"action": "parse", "format": "json",
                                        "page": titolo, **extra}, timeout=40)
        if r.status_code == 429:
            if tentativo == tentativi:
                r.raise_for_status()
            print(f"    429 dalla fonte: aspetto {attesa:.0f}s "
                  f"(tentativo {tentativo}/{tentativi})")
            time.sleep(attesa)
            attesa *= 3
            continue
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise RuntimeError(f"{titolo}: {d['error'].get('info', d['error'])}")
        return d["parse"]
    raise RuntimeError(f"{titolo}: la fonte continua a rispondere 429")


def scarica_uno(sessione, league: str, season: str) -> dict:
    """Il calendario di un campionato. Non scrive: ritorna.

    **Una sola richiesta per campionato**, per l'intera pagina. La prima stesura
    ne faceva tre, chiedendo le sezioni per indice, e ha scoperto per errore due
    cose: che la struttura delle sezioni NON e' la stessa nei cinque campionati
    (la divisione in gironi e' una convenzione della sola pagina italiana della
    Serie A) e che chiedere piu' spesso fa scattare il 429. Leggere la pagina
    intera una volta risolve entrambe.
    """
    titolo = T.titolo(league, season)
    html = _api(sessione, titolo, prop="text")["text"]["*"]

    note = P.squadre(html)
    righe = P.giornate(html, note)
    if not righe:
        raise RuntimeError(
            f"{titolo}: nessuna riga-partita riconosciuta. La pagina esiste ma "
            "non ha un calendario nella forma attesa: si dichiara invece di "
            "scrivere un file vuoto che sembrerebbe un calendario."
        )

    return {
        "campionato": league,
        "stagione": season,
        "fonte": f"it.wikipedia.org / {titolo}",
        "raccolto": dt.now().isoformat(timespec="seconds"),
        "criterio_giocata": P.CRITERIO_GIOCATA,
        "squadre": note,
        "partite": len(righe),
        "giocate": sum(1 for r in righe if r["giocata"] is True),
        "da_giocare": sum(1 for r in righe if r["giocata"] is False),
        "completezza": P.completezza(righe, len(note)),
        "verifica_struttura": P.verifica(righe, len(note)) or "nessuna violazione",
        "righe": righe,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--league", nargs="+", choices=sorted(T.TITOLI))
    ap.add_argument("--season", default=config.SEASON_CORRENTE)
    ap.add_argument("--dry-run", action="store_true",
                    help="stampa i bersagli senza toccare la rete")
    a = ap.parse_args(argv)

    bersagli = T.bersagli(a.league, a.season)

    if a.dry_run:
        print("DRY-RUN - nessuna richiesta di rete\n")
        for b in bersagli:
            print(f"  {b['league']:22s} {b['titolo']}")
            print(f"  {'':22s} -> {b['percorso']}")
        return 0

    sessione = requests.Session()
    sessione.headers.update({"User-Agent": T.USER_AGENT})

    usciti = 0
    for b in bersagli:
        try:
            d = scarica_uno(sessione, b["league"], b["season"])
        except Exception as exc:            # noqa: BLE001
            print(f"  !! {b['league']}: {exc}")
            usciti = 1
            continue
        b["percorso"].parent.mkdir(parents=True, exist_ok=True)
        b["percorso"].write_text(
            json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        c = d["completezza"]
        stato = ("ok" if d["verifica_struttura"] == "nessuna violazione"
                 else f"STRUTTURA: {sorted(d['verifica_struttura'])}")
        print(f"  {b['league']:22s} {len(d['squadre']):2d} squadre | "
              f"{d['partite']:3d}/{c['partite_attese']:3d} partite | "
              f"g{c['prima_giornata']}-{c['ultima_giornata']} su "
              f"{c['giornate_attese']} | {d['giocate']:3d} giocate | "
              f"{'completo' if c['completo'] else 'PARZIALE'} | {stato}")
        if d["verifica_struttura"] != "nessuna violazione":
            usciti = 1
    return usciti


if __name__ == "__main__":
    raise SystemExit(main())
