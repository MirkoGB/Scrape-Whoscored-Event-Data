# -*- coding: utf-8 -*-
"""Accerta le terne `(regione, torneo, slug)` di WhoScored, invece di indovinarle.

`config.LEAGUE_CODES` porta `whoscored: None` per quattro campionati su cinque, e
`target.Target.__post_init__` **solleva** invece di comporre un URL: e' voluto,
perche' un URL inventato porta a un'altra competizione **senza dirlo**. Questo
modulo e' il modo dichiarato di togliere quel `None`.

**Il disegno e' una falsificazione, non una ricerca.** Non si naviga il menu a
tendina di `main.getLeagueUrls` (che e' una sequenza di click su classi CSS
generate, cioe' la parte piu' fragile del fork). Si fa il contrario:

1. si dichiara una terna **candidata**, che e' un'ipotesi e non un dato;
2. si carica la pagina e si chiede **alla fonte** come si chiama;
3. la candidata passa **solo se** il nome della competizione e il paese
   corrispondono a cio' che ci si aspettava.

Ne segue che una terna sbagliata non entra in `LEAGUE_CODES`: viene rifiutata.
E' lo stesso disegno di `soglie_2627.verifica_calendario`, che ha **rifiutato
tre fonti su quattro** invece di adattarsi alla prima.

**I due controlli sono cio' che rende leggibile un esito positivo** (lezione di
E1: una guardia che dice sempre di si' non e' una guardia):

- `ITA-serie-a` e' **gia' accertata** nel repository (108 / 5 / italy-serie-a) e
  deve **passare**;
- una terna deliberatamente sbagliata deve **fallire**.

Se il controllo negativo passasse, la verifica non starebbe guardando niente.

Nota sul browser: `main.py` istanzia `webdriver.Firefox()`, che su questa
macchina non esiste. Qui si usa Chrome via Selenium Manager (selenium >= 4.6
scarica il driver da solo). **Non e' una correzione di `main.py`**: e' un modulo
separato che non tocca l'acquisizione, e il fatto che `main.py` non parta resta
un difetto dichiarato e non aggirato di nascosto.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sot import config  # noqa: E402

# Il mirror `1xbet.whoscored.com` di `main.py:60` risponde 301 verso questo
# dominio (rilevato il 2026-08-14). Si registra il fatto e si usa la
# destinazione, invece di seguire un redirect a ogni richiesta.
BASE_URL = "https://www.whoscored.com"

# Attesa dopo il caricamento: la pagina e' dietro un controllo anti-bot che
# rimanda una interstiziale prima del contenuto vero.
ATTESA_S = 8.0


@dataclass(frozen=True)
class Candidata:
    """Un'IPOTESI su una terna, con cio' che la fonte deve confermare.

    I tre attesi sono il criterio di accettazione e vanno scritti **prima** di
    guardare la pagina: e' la stessa disciplina con cui E1 dichiara le soglie e
    V0 le linee.

    **Ogni atteso si cerca nel campo in cui significa qualcosa, mai in un blob
    concatenato**, e questa non e' pignoleria: la prima stesura cercava il paese
    in tutti i campi uniti e ha **confermato la Ligue 1 per via di "Coupe de
    France"**, che e' un'altra competizione elencata nel breadcrumb. Un criterio
    su un testo unito produce falsi positivi e falsi negativi insieme.

    - `atteso_nome` -> in `title` **o** `h1`. Sono nomi propri e la fonte non li
      traduce ("Serie A", "Premier League", "LaLiga", "Bundesliga", "Ligue 1").
    - `atteso_slug_fonte` -> nel **`canonical`**, che e' il modo in cui la
      pagina dichiara la propria identita'. E' localizzato (`italia-serie-a`,
      non `italy-serie-a`), quindi si dichiara **come la fonte lo scrive**, non
      come lo scriviamo noi.
    - la coppia numerica -> nel `canonical`, ed e' il controllo piu' forte:
      la fonte **rimanda indietro gli stessi id** che le abbiamo chiesto.
    """

    league: str
    regione: int
    torneo: int
    slug: str
    atteso_nome: str
    atteso_slug_fonte: str


# Le cinque candidate. La prima e' il CONTROLLO POSITIVO: e' gia' in
# `config.LEAGUE_CODES` ed e' l'unica terna del repository che sia gia' stata
# usata per scaricare dati veri (1.889 partite).
#
# Gli slug della fonte sono quelli **osservati** nel canonical il 2026-08-14,
# con il sito che serve la localizzazione italiana (`it.whoscored.com`).
CANDIDATE = (
    Candidata("ITA-serie-a", 108, 5, "italy-serie-a", "serie a", "italia-serie-a"),
    Candidata("ENG-premier-league", 252, 2, "england-premier-league",
              "premier league", "inghilterra-premier-league"),
    Candidata("ESP-la-liga", 206, 4, "spain-laliga", "laliga", "spagna-laliga"),
    Candidata("GER-bundesliga", 81, 3, "germany-bundesliga",
              "bundesliga", "germania-bundesliga"),
    Candidata("FRA-ligue-1", 74, 22, "france-ligue-1",
              "ligue 1", "francia-ligue-1"),
)

# DUE controlli negativi, che provano due cose diverse.
#
# 1. il criterio si accorge di un NOME sbagliato;
# 2. la fonte non ripiega in silenzio su un default quando gli id non esistono.
#    Senza il secondo, "il canonical contiene i miei id" sarebbe una tautologia
#    se il sito rispondesse comunque qualcosa.
CONTROLLI_NEGATIVI = (
    Candidata("[neg] nome sbagliato", 252, 2, "england-premier-league",
              "primeira liga", "portogallo-primeira-liga"),
    Candidata("[neg] id inesistenti", 9999, 9999, "campionato-inventato",
              "premier league", "inghilterra-premier-league"),
)


def percorso(c: Candidata) -> str:
    return f"/regions/{c.regione}/tournaments/{c.torneo}/{c.slug}"


def _apri_browser(headless: bool = True):
    from selenium import webdriver

    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    # Un UA da browser reale: l'UA di default di headless e' rifiutato con 403.
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=opts)


def _testo_identificativo(driver) -> dict:
    """Cio' che la PAGINA dice di se stessa. Non si interpreta: si riporta."""
    out = {"title": driver.title or ""}
    for nome, script in (
        ("canonical",
         "var e=document.querySelector('link[rel=canonical]');"
         "return e? e.href : '';"),
        ("og_title",
         "var e=document.querySelector('meta[property=\"og:title\"]');"
         "return e? e.content : '';"),
        ("h1", "var e=document.querySelector('h1');return e? e.innerText : '';"),
        ("breadcrumb",
         "var e=document.querySelector('.breadcrumb, #breadcrumb-nav');"
         "return e? e.innerText : '';"),
    ):
        try:
            out[nome] = driver.execute_script(script) or ""
        except Exception:
            out[nome] = ""
    return out


def verifica_una(driver, c: Candidata) -> dict:
    """Carica la pagina della candidata e applica il criterio dichiarato."""
    url = BASE_URL + percorso(c)
    esito = {"league": c.league, "url": url, **asdict(c)}

    try:
        driver.get(url)
        time.sleep(ATTESA_S)
    except Exception as e:  # pragma: no cover - dipende dalla rete
        esito.update(stato="errore_rete", dettaglio=str(e)[:200], passa=False)
        return esito

    ident = _testo_identificativo(driver)
    esito.update(ident)

    blob = re.sub(r"\s+", " ", " ".join(ident.values()).lower())

    # La pagina anti-bot non contiene il nome della competizione: si distingue
    # da un "nome sbagliato" invece di confonderla con esso.
    if not blob.strip() or "just a moment" in blob or "attention required" in blob:
        esito.update(stato="bloccata_anti_bot", passa=False)
        return esito

    canonical = (ident.get("canonical") or "").lower()
    titolo = ((ident.get("title") or "") + " " + (ident.get("h1") or "")).lower()

    # --- i tre controlli, ognuno nel campo in cui significa qualcosa ---
    trova_nome = c.atteso_nome.lower() in titolo
    trova_slug = c.atteso_slug_fonte.lower() in canonical
    trova_ids = f"/regions/{c.regione}/tournaments/{c.torneo}/" in canonical

    if not canonical:
        esito.update(stato="canonical_assente", passa=False)
        return esito

    passa = trova_nome and trova_slug and trova_ids
    esito.update(
        trova_nome=trova_nome,
        trova_slug=trova_slug,
        trova_ids=trova_ids,
        stato="confermata" if passa else "rifiutata",
        passa=bool(passa),
    )
    return esito


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="stampa gli URL candidati senza aprire il browser "
                         "e senza toccare la rete")
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=Path("reports/fase13_terne_whoscored.json"))
    a = ap.parse_args(argv)

    print(f"Base URL: {BASE_URL}")
    print(f"(il mirror {'1xbet.whoscored.com'} risponde 301 verso questo dominio)\n")

    prove = list(CANDIDATE) + list(CONTROLLI_NEGATIVI)

    if a.dry_run:
        print("DRY-RUN — nessuna richiesta di rete\n")
        for c in prove:
            marca = ""
            if c in CONTROLLI_NEGATIVI:
                marca = " [CONTROLLO NEGATIVO: deve fallire]"
            elif c.league == "ITA-serie-a":
                marca = " [CONTROLLO POSITIVO: deve passare]"
            print(f"  {c.league:22s} {BASE_URL + percorso(c)}{marca}")
            print(f"  {'':22s} attende nome={c.atteso_nome!r} "
                  f"slug_fonte={c.atteso_slug_fonte!r} ids=/{c.regione}/{c.torneo}/")
        return 0

    driver = _apri_browser(headless=not a.no_headless)
    esiti = []
    try:
        for c in prove:
            e = verifica_una(driver, c)
            esiti.append(e)
            print(f"{c.league:22s} r={c.regione:<4d} t={c.torneo:<3d} "
                  f"{e['stato']:18s} title={e.get('title','')[:60]!r}")
    finally:
        driver.quit()

    # --- i controlli, che rendono leggibile l'esito ---
    pos = next(e for e in esiti if e["league"] == "ITA-serie-a")
    negs = esiti[-len(CONTROLLI_NEGATIVI):]
    print("\n--- controlli ---")
    print(f"positivo  ITA-serie-a (gia' accertata)  "
          f"{'PASSA (giusto)' if pos['passa'] else 'FALLISCE'}")
    for c, e in zip(CONTROLLI_NEGATIVI, negs):
        stato = "FALLISCE (giusto)" if not e["passa"] else "PASSA (la guardia non guarda niente)"
        print(f"negativo  {c.league:24s}      {stato}")

    guardia_valida = pos["passa"] and not any(e["passa"] for e in negs)
    print(f"\nla verifica e' leggibile: {guardia_valida}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"base_url": BASE_URL, "guardia_valida": guardia_valida, "esiti": esiti},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"scritto {a.out}")

    if not guardia_valida:
        print("\nNESSUNA terna viene dichiarata: senza i due controlli un "
              "'confermata' non significa niente.")
        return 1

    print("\nterne confermate, da dichiarare in config.LEAGUE_CODES:")
    for e in esiti[:len(CANDIDATE)]:
        if e["passa"] and e["league"] != "ITA-serie-a":
            print(f'    "{e["league"]}": {{"regione": {e["regione"]}, '
                  f'"torneo": {e["torneo"]}, "slug": "{e["slug"]}"}},')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
