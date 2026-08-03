# -*- coding: utf-8 -*-
"""L'unico modulo di questo pacchetto che apre una connessione.

Si esegue:

    ./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_voti --dry-run
    ./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_voti
    ./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_voti --season 2021-2022

I requisiti di `docs/regole_fantacalcio.md` §4.2, uno per uno e dove sono:

| requisito | dove |
| --- | --- |
| frequenza limitata e dichiarata | `--sleep`, default 3 s, ~10 min per cinque stagioni |
| `User-Agent` identificabile | `USER_AGENT`, sotto |
| cache locale, nessuna pagina scaricata due volte | `scarica_giornata`, il `is_file()` **prima** del `get` |
| manifest con URL, data e hash | `acquisition/manifest.registra_fantacalcio` |
| grezzo separato dagli elaborati, mai trasformato | `raw/fantacalcio/...`, gzip senza perdita |
| cambiamenti di struttura segnalati, non assorbiti | `pagina.MarkupInatteso`, e la quarantena qui sotto |
| ogni voto conserva stagione, giornata e provider | colonne di `pagina.analizza` |

**Una pagina il cui markup non rispetta il contratto non entra in `raw/`.**
Finisce sotto `processed/.../quarantena/`, che e' cancellabile, e la stagione si
ferma li'. E' piu' severo del necessario di proposito: raccogliere centonovanta
pagine e scoprire dopo che il parser leggeva la colonna sbagliata e' il modo in
cui questi errori costano davvero, e la Fase 7 ne ha gia' visto uno
(`StandingSave`, la stessa etichetta su due dizionari diversi).

**Nessun aggiramento.** Se la fonte rispondesse 401, 403 o servisse una pagina
di verifica, lo scraper si ferma e lo dichiara: non cambia `User-Agent`, non
forgia cookie, non cerca endpoint alternativi. L'art. 3.3(e) dei Termini vieta
di aggirare gli strumenti anti-bot, e l'autorizzazione dichiarata dall'utente
copre la raccolta, non l'elusione di un rifiuto.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acquisition.fantacalcio import pagina as P  # noqa: E402
from acquisition.fantacalcio import target as T  # noqa: E402
from sot import config  # noqa: E402

# Dichiarato in `target.py`, che non importa `requests`: chi vuole sapere come
# ci presentiamo alla fonte non deve caricare lo strato di rete per leggerlo.
USER_AGENT = T.USER_AGENT

# Un 5xx e' un inciampo del server e si ritenta; un 401/403 e' un rifiuto e non
# si ritenta. Distinguerli e' la differenza fra insistere e forzare.
RITENTABILI = {429, 500, 502, 503, 504}
TENTATIVI = 3


class FonteHaRifiutato(RuntimeError):
    """La fonte ha risposto con un rifiuto. Non si ritenta e non si aggira."""


def sessione() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "it-IT,it;q=0.9",
    })
    return s


def quarantena(target: T.TargetVoti) -> Path:
    """Dove finisce una pagina che non rispetta il contratto del markup.

    Sotto `processed/` e non sotto `raw/`: e' materiale da guardare a mano, non
    un dato acquisito, e `processed/` e' l'albero cancellabile senza perdita.
    """
    return config.processed_dir(target.league, target.season) / "voti_quarantena"


def scarica_giornata(sess, target: T.TargetVoti, giornata: int,
                     verbose: bool = True) -> str:
    """Scarica una giornata. Restituisce `saltata` | `scaricata`.

    L'ordine delle prime due righe e' il vincolo 9 in forma eseguibile: si
    guarda il disco **prima** di toccare la rete. Una pagina gia' presente non
    si riscarica e non si sovrascrive mai.
    """
    fuori = target.percorso(giornata)
    if fuori.is_file():
        return "saltata"

    url = target.url(giornata)
    ultimo = None
    for tentativo in range(1, TENTATIVI + 1):
        try:
            r = sess.get(url, timeout=60)
        except requests.RequestException as e:
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
            f"{url} -> HTTP {r.status_code}. Lo scraper si ferma qui: un "
            "rifiuto non si ritenta e non si aggira (Termini, art. 3.3(e))"
        )
    else:
        raise RuntimeError(f"{url}: {TENTATIVI} tentativi falliti, ultimo: {ultimo}")

    # Il contratto si verifica **prima** di scrivere in raw/: cosi' `raw/` non
    # contiene mai una pagina che non sappiamo leggere.
    try:
        P.analizza(r.content, target.season, giornata)
    except P.MarkupInatteso as e:
        q = quarantena(target)
        q.mkdir(parents=True, exist_ok=True)
        P.scrivi(q / f"{giornata:02d}.html.gz", r.content)
        raise P.MarkupInatteso(
            f"{target} giornata {giornata}: {e}\n"
            f"  la pagina NON e' entrata in raw/. Copia da guardare: {q}"
        ) from e

    P.scrivi(fuori, r.content)
    if verbose:
        print(f"  g{giornata:02d}  {len(r.content) // 1024} KB  -> {fuori.name}")
    return "scaricata"


def scarica_stagione(sess, target: T.TargetVoti, giornate=None,
                     pausa: float = 3.0, verbose: bool = True) -> dict:
    giornate = list(giornate) if giornate else list(range(1, T.N_GIORNATE + 1))
    conti = {"scaricate": 0, "saltate": 0}
    for i, g in enumerate(giornate):
        esito = scarica_giornata(sess, target, g, verbose=verbose)
        conti["scaricate" if esito == "scaricata" else "saltate"] += 1
        # La pausa serve solo dopo una richiesta vera: saltare 38 file gia' su
        # disco deve costare zero, altrimenti la ripartibilita' del vincolo 9
        # esiste sulla carta e non nell'uso.
        if esito == "scaricata" and i < len(giornate) - 1:
            time.sleep(pausa)
    return conti


def main(argv=None) -> int:
    args = T.parser().parse_args(argv)
    bersagli = T.targets(args.league, args.season)
    giornate = sorted(args.giornata) if args.giornata else list(range(1, T.N_GIORNATE + 1))
    for g in giornate:
        T._check_giornata(g)

    print(f"fonte: {T.BASE_URL} | User-Agent: {USER_AGENT}")
    print(f"{len(bersagli)} stagioni x {len(giornate)} giornate = "
          f"{len(bersagli) * len(giornate)} pagine, pausa {args.sleep}s\n")

    if args.dry_run:
        for t in bersagli:
            s = T.stato(t)
            print(f"{t}")
            print(f"  url esempio : {t.url(giornate[0])}")
            print(f"  destinazione: {s['dir_grezzo']}")
            print(f"  su disco    : {s['presenti']}/{s['attese']}"
                  + (f" — mancano {len(s['mancanti'])}" if s["mancanti"] else " — completa"))
        print("\n--dry-run: nessuna richiesta di rete effettuata.")
        return 0

    sess = sessione()
    falliti = []
    for t in bersagli:
        print(f"\n=== {t} ===")
        try:
            c = scarica_stagione(sess, t, giornate, pausa=args.sleep)
            print(f"  {c['scaricate']} scaricate, {c['saltate']} gia' presenti")
        except (P.MarkupInatteso, FonteHaRifiutato, RuntimeError) as e:
            # Una stagione che fallisce non ferma le altre: e' la stessa scelta
            # dell'acquisizione WhoScored, ed e' quella che ha retto quando la
            # 2022-2023 e' saltata per un banner.
            print(f"  INTERROTTA: {e}")
            falliti.append((str(t), str(e)))

    if falliti:
        print(f"\n{len(falliti)} stagioni interrotte:")
        for nome, err in falliti:
            print(f"  {nome}: {err.splitlines()[0]}")
    return 1 if falliti else 0


if __name__ == "__main__":
    raise SystemExit(main())
