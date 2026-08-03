# -*- coding: utf-8 -*-
"""Il listone: una pagina per stagione.

    ./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_quote --dry-run
    ./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_quote

Stesse regole dei voti, e per lo stesso motivo: stesso `User-Agent`
identificabile, stesso ritmo dichiarato, stessa idempotenza — il disco si guarda
**prima** della rete — e stessa quarantena per una pagina che non rispetti il
contratto del markup. Le regole non cambiano perche' cambia la risorsa.

Sono cinque richieste in tutto, non centonovanta: le quotazioni sono un oggetto
stagionale.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acquisition.fantacalcio import pagina as P  # noqa: E402
from acquisition.fantacalcio import target as T  # noqa: E402
from acquisition.fantacalcio.scrape_voti import (  # noqa: E402
    FonteHaRifiutato, RITENTABILI, TENTATIVI, USER_AGENT, sessione)
from sot import config  # noqa: E402


def scarica_listone(sess, target: T.TargetQuote, verbose: bool = True) -> str:
    fuori = target.percorso
    if fuori.is_file():
        return "saltato"

    ultimo = None
    for tentativo in range(1, TENTATIVI + 1):
        try:
            r = sess.get(target.url, timeout=60)
        except Exception as e:                      # noqa: BLE001
            ultimo = e
            time.sleep(2.0 * tentativo)
            continue
        if r.status_code == 200:
            break
        if r.status_code in RITENTABILI:
            ultimo = f"HTTP {r.status_code}"
            time.sleep(5.0 * tentativo)
            continue
        raise FonteHaRifiutato(
            f"{target.url} -> HTTP {r.status_code}. Un rifiuto non si ritenta "
            "e non si aggira (Termini, art. 3.3(e))")
    else:
        raise RuntimeError(f"{target.url}: {TENTATIVI} tentativi falliti, ultimo: {ultimo}")

    try:
        righe = P.analizza_quote(r.content, target.season)
    except P.ListoneNonPubblicato as e:
        # Non e' un errore: il listone della stagione entrante esce a fine
        # agosto. Non si scrive niente e non si ritenta in ciclo.
        if verbose:
            print(f"  {e}")
        return "non pubblicato"
    except P.MarkupInatteso as e:
        q = config.processed_dir(target.league, target.season) / "quote_quarantena"
        q.mkdir(parents=True, exist_ok=True)
        P.scrivi(q / "quotazioni.html.gz", r.content)
        raise P.MarkupInatteso(
            f"{target}: {e}\n  la pagina NON e' entrata in raw/. Copia: {q}") from e

    P.scrivi(fuori, r.content)
    if verbose:
        print(f"  {len(righe)} quotati, {len(r.content) // 1024} KB -> {fuori}")
    return "scaricato"


def main(argv=None) -> int:
    p = T.parser()
    p.description = "Scarica il listone (quotazioni) per una o piu' stagioni."
    args = p.parse_args(argv)
    seasons = args.season or config.SEASONS_STORICHE
    bersagli = [T.TargetQuote(args.league, s) for s in sorted(seasons)]

    print(f"fonte: {T.BASE_URL} | User-Agent: {USER_AGENT}")
    print(f"{len(bersagli)} listoni, pausa {args.sleep}s\n")

    if args.dry_run:
        for t in bersagli:
            stato = "gia' su disco" if t.percorso.is_file() else "da scaricare"
            print(f"{t}\n  url         : {t.url}\n  destinazione: {t.percorso}\n"
                  f"  stato       : {stato}")
        print("\n--dry-run: nessuna richiesta di rete effettuata.")
        return 0

    sess = sessione()
    falliti = []
    for i, t in enumerate(bersagli):
        print(f"\n=== {t} ===")
        try:
            esito = scarica_listone(sess, t)
            if esito == "saltato":
                print("  gia' su disco, saltato")
            elif esito == "non pubblicato":
                pass
            elif i < len(bersagli) - 1:
                time.sleep(args.sleep)
        except (P.MarkupInatteso, FonteHaRifiutato, RuntimeError) as e:
            print(f"  INTERROTTO: {e}")
            falliti.append(str(t))
    if falliti:
        print(f"\n{len(falliti)} listoni non acquisiti: {falliti}")
    return 1 if falliti else 0


if __name__ == "__main__":
    raise SystemExit(main())
