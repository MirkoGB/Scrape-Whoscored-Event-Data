# -*- coding: utf-8 -*-
"""Fase 15 / C1 — accerta se le partite FUTURE si possono leggere, invece di assumerlo.

Lo scraper di questo repository sa raccogliere solo partite **gia' giocate**, e
lo fa per due ragioni indipendenti che vanno accertate una per una:

1. **naviga solo all'indietro.** `scrape_season._click_prev_day` usa il bottone
   `dayChangeBtn-prev`; **un `dayChangeBtn-next` non esiste in nessun punto del
   repository** e non e' mai stato osservato. Che ci sia e' un'IPOTESI.
2. **scarta le righe non-`/live/` prima di leggerle**
   (`scrape_season.py:281`). Quale sia davvero il discriminante fra «giocata» e
   «da giocare» non e' mai stato misurato: si sa solo che le 8.909 righe dei 25
   `matches.json` su disco hanno **tutte** `/live/` e uno `score` della forma
   `\\d+:\\d+`, che e' un campione in cui la risposta e' costante.

**Il disegno e' una falsificazione, non una ricerca**, ed e' quello di
`verifica_terne.py`: si dichiara il criterio PRIMA, poi lo si mette alla prova
su un caso in cui la risposta e' nota nei due versi.

- **CONTROLLO POSITIVO** — una stagione **conclusa e gia' su disco**
  (`2025-2026`): ogni riga del calendario deve risultare **giocata**, e il suo
  URL deve stare nel `matches.json` che abbiamo. Se il criterio ne classificasse
  una come «da giocare», sarebbe sbagliato.
- **CONTROLLO NEGATIVO** — la stagione **in corso**, navigata in **avanti**:
  quelle righe devono risultare **da giocare**, e i loro URL non devono stare in
  nessun `matches.json`. Se passassero come «giocate», il criterio non starebbe
  guardando niente.
- **CONTROLLO SULLA NAVIGAZIONE** — il bottone «giorno successivo» deve
  **muovere la pagina**. Senza, «nessuna partita futura trovata» e «il bottone
  non funziona» darebbero lo stesso identico esito.

**Due derivazioni indipendenti dello stesso fatto** (vincolo 7 applicato dentro
una fonte sola): il criterio primario guarda l'**href**, quello di controllo
guarda la **forma del punteggio**. Devono concordare; dove divergono, la
divergenza e' il risultato e va riportata, non risolta scegliendo la piu' comoda.

**`--dry-run` non tocca la rete.** Usa Chrome via Selenium Manager, come
`verifica_terne.py`, e **non tocca `main.py` ne' `scrape_season.py`**: questo
modulo accerta, non acquisisce.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sot import config  # noqa: E402

BASE_URL = "https://www.whoscored.com"

#: **Il sito serve la localizzazione italiana e redirige a `it.whoscored.com`**
#: (rilevato il 2026-09-03 da questa verifica). Ne segue che l'`href` di una riga
#: ha l'host `it.` mentre `matches.json` conserva un percorso RELATIVO: i due si
#: confrontano sul **percorso**, mai sottraendo una stringa di host.
HOST_SERVITO = "it.whoscored.com"

#: Attesa dopo un caricamento di pagina: c'e' un controllo anti-bot davanti.
ATTESA_S = 8.0

#: Attesa dopo un click di navigazione fra i giorni.
ATTESA_CLICK_S = 2.5

#: Quante pagine di calendario percorrere per lato. Piccolo di proposito: qui si
#: accerta una proprieta', non si acquisisce un calendario.
PAGINE = 3

#: I selettori del calendario. **Sono classi CSS generate da React**, cioe' la
#: parte piu' fragile di tutta l'acquisizione: si importano da un posto solo per
#: non averne due copie che divergono in silenzio.
SEL_ACCORDION = "Accordion-module_accordion__UuHD0"
SEL_HEADER = "Accordion-module_header__HqzWD"
SEL_ROW = "Match-module_row__zwBOn"
SEL_TEAMS = "Match-module_teams__sGVeq"

#: I due bottoni. Il primo e' quello che lo scraper gia' usa; **il secondo e'
#: l'ipotesi che questo modulo esiste per accertare**.
BTN_PREV = "dayChangeBtn-prev"
BTN_NEXT = "dayChangeBtn-next"

#: **Il criterio primario, dichiarato prima di guardare la pagina.**
#: Una partita e' GIOCATA se e solo se il suo href contiene `/live/`. E' cio' che
#: lo scraper gia' assume implicitamente scartando tutto il resto; qui diventa
#: un'affermazione falsificabile invece di un filtro non detto.
CRITERIO_PRIMARIO = "giocata <=> '/live/' compare nell'href della riga"

#: **Il criterio di controllo, indipendente dal primo.** Guarda la forma del
#: testo negli `span` del link, che e' cio' che `scrape_season` scrive dentro
#: `score`. Un punteggio ha due numeri piccoli; un orario ha le ore a sinistra.
#: La soglia 10 e' dichiarata qui e non scelta guardando i dati: in nessuno dei
#: cinque campionati esiste una squadra che abbia segnato 10 gol in una partita
#: nelle cinque stagioni acquisite.
CRITERIO_CONTROLLO = ("giocata <=> il testo degli span e' 'a:b' con a<10 e b<10 "
                      "(un orario ha le ore a sinistra: '20:45')")
MAX_GOL_PLAUSIBILE = 10

_RE_COPPIA = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{1,2})\s*$")


def giocata_da_href(href: str) -> bool:
    """Il criterio primario. Una riga sola, perche' e' una definizione."""
    return "/live/" in (href or "")


def giocata_da_punteggio(testo: str) -> bool | None:
    """Il criterio di controllo. `None` = non si pronuncia, che non e' `False`.

    La distinzione conta: una riga il cui testo non ha affatto la forma `a:b`
    non e' «da giocare», e' **illeggibile con questo criterio**, e contarla come
    negativa gonfierebbe l'accordo fra i due criteri senza motivo.
    """
    m = _RE_COPPIA.match(testo or "")
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return a < MAX_GOL_PLAUSIBILE and b < MAX_GOL_PLAUSIBILE


def url_gia_scaricati() -> set[str]:
    """Gli URL di tutte le partite che il repository ha gia' su disco.

    E' il metro del controllo positivo, e viene dai `matches.json`, cioe' da un
    file che **non passa da questo modulo**: se lo producesse lui, il confronto
    sarebbe circolare.
    """
    noti = set()
    for league in sorted(config.LEAGUE_CODES):
        for season in config.SEASONS_STORICHE:
            f = config.matches_json(league, season)
            if f.is_file():
                for r in json.loads(f.read_text(encoding="utf-8")):
                    noti.add(urlsplit(r.get("url") or "").path)
    return noti


def _apri_browser(headless: bool = True):
    from selenium import webdriver

    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=opts)


def _firma(driver) -> str:
    """Le date mostrate: se non cambiano, il click non ha avuto effetto."""
    from selenium.webdriver.common.by import By

    try:
        return "|".join(e.text for e in
                        driver.find_elements(By.CLASS_NAME, SEL_HEADER))
    except Exception:
        return ""


def _clicca(driver, id_bottone: str) -> dict:
    """Clicca un bottone di navigazione e RIPORTA che cosa e' successo.

    Ritorna un dizionario invece di un booleano: «il bottone non c'e'», «c'e' ma
    e' disabilitato» e «c'e', l'ho cliccato e la pagina non si e' mossa» sono
    tre fatti diversi, e collassarli in `False` e' esattamente cio' che
    renderebbe illeggibile l'esito.
    """
    from selenium.webdriver.common.by import By

    try:
        btn = driver.find_element(By.ID, id_bottone)
    except Exception:
        return {"esiste": False, "disabilitato": None, "muove": False}

    disabilitato = btn.get_attribute("disabled") is not None
    if disabilitato:
        return {"esiste": True, "disabilitato": True, "muove": False}

    prima = _firma(driver)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)
    except Exception as e:
        return {"esiste": True, "disabilitato": False, "muove": False,
                "errore": str(e)[:120]}

    time.sleep(ATTESA_CLICK_S)
    return {"esiste": True, "disabilitato": False,
            "muove": _firma(driver) != prima}


def _righe_visibili(driver) -> list[dict]:
    """Tutte le righe partita della pagina corrente, **senza filtrarle**.

    E' la differenza con `scrape_season._parse_visible_fixtures`, che scarta le
    righe non-`/live/` prima di leggerle: qui si legge tutto e si classifica
    dopo, perche' il filtro e' proprio cio' che si vuole mettere alla prova.
    """
    from selenium.webdriver.common.by import By

    fuori = []
    for acc in driver.find_elements(By.CLASS_NAME, SEL_ACCORDION):
        try:
            data = acc.find_element(By.CLASS_NAME, SEL_HEADER).text
            righe = acc.find_elements(By.CLASS_NAME, SEL_ROW)
        except Exception:
            continue
        for row in righe:
            try:
                a = row.find_element(By.TAG_NAME, "a")
                href = a.get_attribute("href") or ""
                spans = [s.text for s in a.find_elements(By.TAG_NAME, "span")]
                squadre = row.find_element(By.CLASS_NAME, SEL_TEAMS).text
            except Exception:
                continue
            fuori.append({"data": data, "href": href,
                          "testo_span": ":".join(spans),
                          "squadre": squadre.replace("\n", " - ")})
    return fuori


def _scraper():
    """Le funzioni fragili si RIUSANO da `scrape_season`, non si riscrivono.

    `_select_season` e `_seleziona_con_ripiego` sono gia' costate due stagioni
    intere (il banner sopra i menu, documentato in CLAUDE.md): averne una seconda
    copia qui vorrebbe dire poterle far divergere in silenzio, ed e' esattamente
    il difetto che `_seleziona_con_ripiego` esiste per non ripetere.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import scrape_season

    return scrape_season


def _url_stagione(league: str, season: str) -> str:
    """L'URL della pagina calendario, con la terna gia' ACCERTATA da Fase 13."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from target import Target

    return Target(league=league, season=season).url_competizione(BASE_URL)


def raccogli(driver, league: str, season: str, verso: str,
             pagine: int = PAGINE) -> dict:
    """Percorre `pagine` pagine di calendario in un verso e raccoglie tutto.

    `verso` e' una stringa e non un booleano, per la ragione per cui `campo` lo
    e' in `previsione.py`: uno `0/1` si scambierebbe senza rumore, e qui
    scambiare i due versi darebbe l'esito opposto senza che nulla se ne accorga.
    """
    if verso not in ("avanti", "indietro"):
        raise ValueError(f"verso {verso!r} non ammesso: 'avanti' o 'indietro'")
    bottone = BTN_NEXT if verso == "avanti" else BTN_PREV

    S = _scraper()
    url = _url_stagione(league, season)
    driver.get(url)
    time.sleep(ATTESA_S)

    titolo = driver.title or ""
    if "just a moment" in titolo.lower() or "attention required" in titolo.lower():
        return {"league": league, "season": season, "verso": verso, "url": url,
                "stato": "bloccata_anti_bot", "righe": [], "navigazione": []}

    # La stagione si SELEZIONA: l'URL della competizione porta quella corrente, e
    # il controllo positivo ha bisogno di una stagione conclusa. Se il menu non
    # ha quella chiesta, si dichiara invece di raccogliere l'anno sbagliato.
    from target import stagione_whoscored
    try:
        S._select_season(driver, stagione_whoscored(season))
        time.sleep(ATTESA_CLICK_S)
    except Exception as e:
        return {"league": league, "season": season, "verso": verso, "url": url,
                "stato": "stagione_non_selezionabile", "dettaglio": str(e)[:200],
                "righe": [], "navigazione": []}

    righe, navigazione = [], []
    viste = set()
    for _ in range(pagine):
        S._force_render(driver)          # il calendario e' caricato pigramente
        for r in _righe_visibili(driver):
            chiave = (r["data"], r["href"])
            if chiave not in viste:
                viste.add(chiave)
                righe.append(r)
        esito = _clicca(driver, bottone)
        navigazione.append(esito)
        if not esito.get("muove"):
            break

    return {"league": league, "season": season, "verso": verso, "url": url,
            "stato": "ok", "titolo": titolo, "righe": righe,
            "navigazione": navigazione}


def classifica(raccolta: dict, noti: set[str]) -> dict:
    """Applica i due criteri e conta. **Non sceglie: riporta.**"""
    righe = raccolta["righe"]
    n = len(righe)
    concordi = discordi = illeggibili = 0
    giocate_href = 0
    in_matches_json = 0

    for r in righe:
        g1 = giocata_da_href(r["href"])
        g2 = giocata_da_punteggio(r["testo_span"])
        r["giocata_href"] = g1
        r["giocata_punteggio"] = g2
        giocate_href += int(g1)
        # **Si confronta il PERCORSO, non una sottostringa dell'URL.** La prima
        # stesura sottraeva `BASE_URL` dall'href e trovava zero corrispondenze
        # su trenta partite che erano tutte gia' su disco: il sito serve la
        # localizzazione italiana, quindi l'host e' `it.whoscored.com` e non
        # `www`. E' la sesta volta che in questo repository un criterio scritto
        # su una FORMA invece che su una PROPRIETA' da' un falso negativo.
        r["percorso"] = urlsplit(r["href"]).path
        r["in_matches_json"] = r["percorso"] in noti
        in_matches_json += int(r["in_matches_json"])
        if g2 is None:
            illeggibili += 1
        elif g1 == g2:
            concordi += 1
        else:
            discordi += 1

    return {**{k: v for k, v in raccolta.items() if k != "righe"},
            "righe_lette": n,
            "giocate_secondo_href": giocate_href,
            "da_giocare_secondo_href": n - giocate_href,
            "in_matches_json": in_matches_json,
            "criteri_concordi": concordi,
            "criteri_discordi": discordi,
            "punteggio_illeggibile": illeggibili,
            "campione_righe": righe[:8]}


#: Le tre prove. **Il controllo positivo e quello negativo stanno sullo stesso
#: campionato**, cosi' che una differenza fra i due non possa venire dal
#: campionato invece che dalla stagione.
PROVE = (
    {"nome": "positivo", "league": config.LEAGUE, "season": "2025-2026",
     "verso": "indietro",
     "attende": "tutte GIOCATE e tutte presenti in matches.json"},
    {"nome": "negativo", "league": config.LEAGUE,
     "season": config.SEASON_CORRENTE, "verso": "avanti",
     "attende": "tutte DA GIOCARE e nessuna presente in matches.json"},
)


def verdetto(classificate: list[dict]) -> dict:
    """Applica i tre controlli **meccanicamente**, e non li interpreta."""
    pos = next(c for c in classificate if c["nome"] == "positivo")
    neg = next(c for c in classificate if c["nome"] == "negativo")

    # (1) la navigazione in avanti esiste e muove la pagina
    nav_avanti = [n for n in neg.get("navigazione", [])]
    bottone_esiste = bool(nav_avanti) and nav_avanti[0].get("esiste") is True
    bottone_muove = any(n.get("muove") for n in nav_avanti)

    # (2) il controllo positivo: tutte giocate, tutte note
    pos_ok = (pos.get("righe_lette", 0) > 0
              and pos.get("da_giocare_secondo_href", 1) == 0
              and pos.get("in_matches_json", 0) == pos.get("righe_lette", 0))

    # (3) il controllo negativo: nessuna giocata, nessuna nota
    neg_ok = (neg.get("righe_lette", 0) > 0
              and neg.get("giocate_secondo_href", 1) == 0
              and neg.get("in_matches_json", 1) == 0)

    # (4) i due criteri indipendenti non devono discordare
    discordi = sum(c.get("criteri_discordi", 0) for c in classificate)

    valida = bool(bottone_esiste and bottone_muove and pos_ok and neg_ok
                  and discordi == 0)
    return {
        "bottone_next_esiste": bottone_esiste,
        "bottone_next_muove": bottone_muove,
        "controllo_positivo": pos_ok,
        "controllo_negativo": neg_ok,
        "criteri_discordi": discordi,
        "verifica_leggibile": valida,
        "criterio_primario": CRITERIO_PRIMARIO,
        "criterio_controllo": CRITERIO_CONTROLLO,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="stampa le prove senza aprire il browser e senza rete")
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--pagine", type=int, default=PAGINE)
    ap.add_argument("--out", type=Path,
                    default=Path("reports/fase15_calendario_verifica.json"))
    a = ap.parse_args(argv)

    print(f"Base URL: {BASE_URL}")
    print(f"criterio primario : {CRITERIO_PRIMARIO}")
    print(f"criterio controllo: {CRITERIO_CONTROLLO}\n")

    if a.dry_run:
        print("DRY-RUN - nessuna richiesta di rete\n")
        for p in PROVE:
            print(f"  [{p['nome']:8s}] {p['league']} {p['season']} "
                  f"verso={p['verso']}")
            print(f"  {'':11s} {_url_stagione(p['league'], p['season'])}")
            print(f"  {'':11s} attende: {p['attende']}")
        print(f"\n  bottoni: prev={BTN_PREV!r}  next={BTN_NEXT!r} "
              f"(il secondo e' l'IPOTESI da accertare)")
        noti = url_gia_scaricati()
        print(f"  URL gia' su disco, metro del controllo positivo: {len(noti)}")
        return 0

    noti = url_gia_scaricati()
    print(f"URL gia' su disco: {len(noti)}\n")

    driver = _apri_browser(headless=not a.no_headless)
    classificate = []
    try:
        for p in PROVE:
            racc = raccogli(driver, p["league"], p["season"], p["verso"],
                            pagine=a.pagine)
            c = {"nome": p["nome"], "attende": p["attende"],
                 **classifica(racc, noti)}
            classificate.append(c)
            print(f"[{p['nome']:8s}] {p['league']} {p['season']} "
                  f"verso={p['verso']} stato={c['stato']}")
            print(f"           righe={c.get('righe_lette', 0)} "
                  f"giocate={c.get('giocate_secondo_href', 0)} "
                  f"note={c.get('in_matches_json', 0)} "
                  f"discordi={c.get('criteri_discordi', 0)} "
                  f"illeggibili={c.get('punteggio_illeggibile', 0)}")
            for n in c.get("navigazione", []):
                print(f"           navigazione: {n}")
            for r in c.get("campione_righe", [])[:3]:
                print(f"           es: {r['data'][:28]!r} {r['squadre'][:34]!r} "
                      f"span={r['testo_span']!r} live={r['giocata_href']}")
    finally:
        driver.quit()

    v = verdetto(classificate)
    print("\n--- controlli ---")
    print(f"il bottone '{BTN_NEXT}' esiste : {v['bottone_next_esiste']}")
    print(f"il bottone muove la pagina     : {v['bottone_next_muove']}")
    print(f"controllo positivo (deve passare): {v['controllo_positivo']}")
    print(f"controllo negativo (deve passare): {v['controllo_negativo']}")
    print(f"criteri discordi (devono essere 0): {v['criteri_discordi']}")
    print(f"\nla verifica e' leggibile: {v['verifica_leggibile']}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"base_url": BASE_URL, "verdetto": v, "prove": classificate},
        indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"scritto {a.out}")

    if not v["verifica_leggibile"]:
        print("\nIL CALENDARIO FUTURO NON E' DICHIARATO ACCERTATO: senza i "
              "controlli, 'ho trovato delle partite' non significa niente.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
