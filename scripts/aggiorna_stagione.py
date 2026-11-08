# -*- coding: utf-8 -*-
"""Fase 14 / A1 — l'aggiornamento settimanale della stagione IN CORSO.

Un comando che porta i cinque campionati dal sito ai Parquet e, da li', alla
pagina delle previsioni. E' pensato per essere rilanciato ogni martedi' e per
non fare danni se lo si rilancia due volte di fila.

LE QUATTRO COSE CHE QUESTO SCRIPT SA E CHE UN CICLO INGENUO SBAGLIEREBBE
------------------------------------------------------------------------
1. **Una stagione in corso e' incompleta per definizione**, quindi lo scraper va
   invocato con `--in-corso`: una passata sola sul calendario invece di quattro,
   e la cache degli URL sempre rinfrescata. Senza, ogni martedi' si pagherebbero
   tre navigazioni complete del calendario per cercare partite non ancora
   giocate, verso una fonte di cui si e' ospiti.

2. **`io_events.build_cache` e' idempotente per ESISTENZA del file**, non per
   contenuto: con CSV nuovi su disco e `force=False` restituirebbe il Parquet
   della settimana prima, e tutto il resto della catena lavorerebbe su dati
   vecchi senza un solo messaggio. Qui si forza **se e solo se** almeno un CSV e'
   piu' recente del Parquet — non «sempre» (rileggere centinaia di CSV ogni
   settimana e' lavoro buttato) e non «mai».

3. **L'xG interno e' cross-fitted a `xg.N_FOLDS` fold raggruppati per partita**,
   quindi sotto quel numero di partite non e' calcolabile affatto. La soglia e'
   dichiarata (`MIN_PARTITE_DERIVATI`) e la stagione viene **saltata**, non
   costruita a meta': meglio nessun derivato che un derivato con dentro una
   colonna che nessuno ha validato. Ne' i tiri ne' i tiri in porta usano l'xG,
   quindi la soglia non e' un limite della previsione: e' un limite della
   tabella.

4. **Una stagione che fallisce non ferma le altre.** E' la stessa regola dello
   scraper, un piano piu' su: cinque campionati sono cinque acquisizioni
   indipendenti, e un browser che muore sulla Ligue 1 non deve costare la
   Bundesliga. Lo scraper gira in un **sottoprocesso** proprio per questo — un
   crash di Selenium li' dentro e' un codice di uscita, non un'eccezione che
   attraversa tutto.

Non decide niente e non stima niente: e' orchestrazione. I numeri li fanno
`aggregate`, `previsione` e i moduli che loro chiamano.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sot import config, xg as xg_mod  # noqa: E402

#: I cinque campionati, presi da `config` e non riscritti: il campionato ha un
#: nome in un posto solo.
CAMPIONATI = tuple(sorted(config.LEAGUE_CODES))

#: Sotto questa soglia i derivati non si costruiscono. E' `xg.N_FOLDS` perche'
#: e' esattamente il numero sotto il quale `GroupKFold` non ha abbastanza gruppi:
#: la soglia non e' scelta guardando i dati, e' imposta dalla procedura.
MIN_PARTITE_DERIVATI = xg_mod.N_FOLDS

RADICE = Path(__file__).resolve().parents[1]
SCRAPER = RADICE / "acquisition" / "whoscored" / "scrape_season.py"


# --------------------------------------------------------------------------
# Stato su disco — non tocca la rete
# --------------------------------------------------------------------------
def stato(league: str, season: str) -> dict:
    """Quanti CSV, quante partite in calendario, e se i Parquet sono vecchi."""
    csv_dir = config.match_dir(league, season)
    csv = sorted(csv_dir.glob("*.csv")) if csv_dir.is_dir() else []

    cal = config.matches_json(league, season)
    in_calendario = None
    if cal.is_file():
        in_calendario = len(json.loads(cal.read_text(encoding="utf-8")))

    slim = config.events_slim(league, season)
    tm = config.team_match(league, season)
    piu_recente = max((c.stat().st_mtime for c in csv), default=0.0)
    # `stale` e' vero anche quando il Parquet non c'e' affatto: e' il caso della
    # prima esecuzione, e trattarlo come "aggiornato" salterebbe la costruzione.
    stale = (not slim.is_file() or not tm.is_file()
             or slim.stat().st_mtime < piu_recente
             or tm.stat().st_mtime < piu_recente)

    return {"campionato": league, "stagione": season,
            "csv": len(csv), "in_calendario": in_calendario,
            "derivati_da_rifare": bool(csv) and stale,
            "abbastanza": len(csv) >= MIN_PARTITE_DERIVATI}


# --------------------------------------------------------------------------
# I tre passi
# --------------------------------------------------------------------------
def scarica(league: str, season: str, sleep: float, dry_run: bool) -> int:
    """Lo scraper, in un sottoprocesso. Ritorna il codice di uscita.

    **`--calendario` raccoglie anche le partite da giocare**, nella stessa
    sessione di browser: aprirne una seconda raddoppierebbe le richieste alla
    fonte per niente. Finiscono in `calendario.json`, che e' un file diverso da
    `matches.json` — mescolarli manderebbe la quota di `avanzamento` a 1,00 dal
    giorno zero e farebbe ritentare ogni settimana lo scarico di partite che non
    si sono ancora giocate.
    """
    cmd = [sys.executable, str(SCRAPER), "--league", league,
           "--season", season, "--in-corso", "--calendario",
           "--sleep", str(sleep)]
    if dry_run:
        cmd.append("--dry-run")
    print("  $ " + " ".join(cmd[1:]))
    return subprocess.call(cmd)


def derivati(league: str, season: str, force: bool) -> dict:
    """Da CSV a `events_slim` / `shots` / `team_match` / `player_match`."""
    from sot import aggregate, io_events

    io_events.build_cache(force=force, league=league, season=season)
    out = aggregate.run(force=force, league=league, season=season)
    return {k: len(v) for k, v in out.items()}


def registra(league: str, season: str) -> dict:
    """La provenienza (vincolo 8). Non scarica e non tocca `raw/`."""
    from acquisition import manifest
    return manifest.registra_whoscored(league=league, seasons=[season],
                                       verbose=False)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Aggiorna i dati evento della stagione in corso e rigenera "
                    "le previsioni.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""esempi:
  aggiorna_stagione.py                       tutti e cinque i campionati
  aggiorna_stagione.py --dry-run             cosa farebbe, senza browser ne' rete
  aggiorna_stagione.py --league ITA-serie-a  uno solo
  aggiorna_stagione.py --solo-derivati       salta lo scaricamento, rifa' il resto
""")
    p.add_argument("--league", nargs="+", choices=sorted(config.LEAGUE_CODES),
                   default=list(CAMPIONATI),
                   help="campionati da aggiornare (default: tutti e cinque)")
    p.add_argument("--season", default=config.SEASON_CORRENTE, metavar="AAAA-AAAA",
                   help="stagione in corso (default: %(default)s)")
    p.add_argument("--dry-run", action="store_true",
                   help="stampa cosa verrebbe fatto e si ferma. Non apre il "
                        "browser, non tocca la rete, non scrive niente")
    p.add_argument("--solo-derivati", action="store_true",
                   help="non scarica: rigenera i Parquet dai CSV gia' su disco")
    p.add_argument("--senza-previsioni", action="store_true",
                   help="non rigenera la pagina delle previsioni")
    p.add_argument("--sleep", type=float, default=7.0, metavar="SEC",
                   help="pausa fra una partita e l'altra (default: %(default)s)")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    config._check_season(args.season)
    t0 = time.time()

    print("=" * 74)
    print(f"AGGIORNAMENTO — stagione {args.season} — "
          f"{len(args.league)} campionat{'o' if len(args.league) == 1 else 'i'}")
    print("=" * 74)

    esiti = []
    for league in args.league:
        print("")
        print(f"--- {league} ---")
        prima = stato(league, args.season)
        print(f"  prima: {prima['csv']} CSV su disco"
              + (f", {prima['in_calendario']} partite in calendario"
                 if prima["in_calendario"] is not None else
                 ", nessuna cache calendario"))

        errore = None
        if not args.solo_derivati:
            try:
                rc = scarica(league, args.season, args.sleep, args.dry_run)
                if rc != 0:
                    errore = f"scraper uscito con codice {rc}"
            except Exception as exc:            # noqa: BLE001
                errore = f"scraper: {exc}"
            if errore:
                print(f"  !! {errore} — gli altri campionati proseguono")

        dopo = stato(league, args.season)
        if args.dry_run:
            print("  (dry-run: nessun derivato, nessun manifest)")
        elif not dopo["abbastanza"]:
            print(f"  {dopo['csv']} partite: sotto le {MIN_PARTITE_DERIVATI} che "
                  "l'xG cross-fitted richiede. Derivati saltati.")
        elif not dopo["derivati_da_rifare"]:
            print("  derivati gia' aggiornati (nessun CSV piu' recente dei Parquet)")
        else:
            # **I due passi hanno due `try` separati**, e non e' pedanteria.
            # Fino al 2026-09-03 stavano insieme, e la riga che stampa il
            # riepilogo del manifest chiamava `len()` su `nuovi`, che e' un
            # CONTATORE INTERO e non una lista: l'eccezione veniva attribuita a
            # `derivati`, che era gia' riuscito. Ogni esecuzione settimanale ha
            # riportato per cinque campionati un errore inesistente sul passo
            # sbagliato, e un guasto VERO dei derivati sarebbe stato
            # indistinguibile da quello.
            try:
                righe = derivati(league, args.season, force=True)
                print("  derivati: "
                      + ", ".join(f"{k} {v}" for k, v in righe.items()))
            except Exception as exc:            # noqa: BLE001
                errore = errore or f"derivati: {exc}"
                print(f"  !! {errore}")
            else:
                try:
                    r = registra(league, args.season)
                    print(f"  manifest: {r.get('nuovi', 0)} nuovi, "
                          f"{len(r.get('modificati', []))} modificati")
                except Exception as exc:        # noqa: BLE001
                    errore = errore or f"manifest: {exc}"
                    print(f"  !! {errore}")

        esiti.append({**dopo, "scaricate": dopo["csv"] - prima["csv"],
                      "errore": errore})

    # ----- riepilogo -----
    print("")
    print("=" * 74)
    print("RIEPILOGO")
    print("=" * 74)
    print(f"  {'campionato':<22} {'CSV':>5} {'cal.':>5} {'nuove':>6}  nota")
    for e in esiti:
        cal = e["in_calendario"] if e["in_calendario"] is not None else "-"
        nota = e["errore"] or ("" if e["abbastanza"]
                               else "sotto la soglia dei derivati")
        print(f"  {e['campionato']:<22} {e['csv']:>5} {str(cal):>5} "
              f"{e['scaricate']:>6}  {nota}")

    # ----- la seconda fonte del calendario -----
    # Va rinfrescata ogni settimana come la prima, o la **giornata** invecchia:
    # Wikipedia scrive il girone di ritorno mano a mano che si avvicina. E' una
    # richiesta per campionato, cinque in tutto, quindi costa quasi niente.
    if not args.dry_run:
        print("")
        print("Aggiorno il calendario da Wikipedia (la giornata)...")
        try:
            from acquisition.wikipedia import scrape_calendario as WK

            WK.main(["--season", args.season])
        except Exception as exc:                # noqa: BLE001
            # **Non ferma il giro.** La giornata e' un di piu': senza, la pagina
            # dichiara `fonte_giornata = assente` e continua a funzionare.
            print(f"  !! calendario Wikipedia: {exc}")

    if not args.dry_run and not args.senza_previsioni:
        print("")
        print("Rigenero le previsioni...")
        # **Non si passa `--league`**, nemmeno quando questa esecuzione ne ha
        # aggiornato uno solo. La pagina e' uno **stato completo**, non un
        # artefatto incrementale: filtrarla sui campionati aggiornati stavolta
        # farebbe sparire gli altri quattro dalla pagina, in silenzio e senza
        # che nulla vada in errore. Ricalcolarli tutti costa un minuto.
        try:
            import run_previsioni
            run_previsioni.main(["--season", args.season])
        except ImportError:
            print("  (run_previsioni.py non c'e' ancora: blocco A4)")
        except Exception as exc:                # noqa: BLE001
            print(f"  !! previsioni non rigenerate: {exc}")

    print("")
    print(f"Fatto in {time.time() - t0:.0f} s.")
    return 1 if any(e["errore"] for e in esiti) else 0


if __name__ == "__main__":
    sys.exit(main())
