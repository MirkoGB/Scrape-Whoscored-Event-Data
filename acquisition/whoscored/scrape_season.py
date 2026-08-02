# -*- coding: utf-8 -*-
"""
Scrape dei dati evento da WhoScored, per una o piu' stagioni.

Uso:
    python acquisition/whoscored/scrape_season.py --dry-run
    python acquisition/whoscored/scrape_season.py
    python acquisition/whoscored/scrape_season.py --season 2021-2022
    python acquisition/whoscored/scrape_season.py --season 2021-2022 2022-2023

**Senza argomenti scarica tutte e cinque le stagioni** di
`config.SEASONS_STORICHE` (2021-2022 .. 2025-2026), non solo quella corrente:
e' il perimetro dichiarato in `docs/regole_fantacalcio.md` §5 e §7.1.

Cosa fa, per ogni stagione:
    1. Apre la pagina della competizione, seleziona la stagione e raccoglie gli
       URL di tutte le partite giocate (in cache JSON accanto ai dati).
    2. Scarica gli eventi partita per partita, un CSV per `matchId` sotto
       `raw/whoscored/<campionato>/<stagione>/events/`.
    3. Con `--merge`, e solo con quello, ne scrive anche la concatenazione.

Tre proprieta' che vanno tenute, non sono comodita':

- **Ripartibile e idempotente** (vincolo 9): una partita gia' su disco viene
  saltata, mai riscaricata e mai sovrascritta. Interrompere e rilanciare e' il
  modo previsto di usarlo, non un incidente.
- **Il grezzo non si tocca**: si scrive solo dove il file non esiste. La
  concatenazione, che e' derivata, va sotto `processed/` e per default **non si
  scrive affatto** — su cinque stagioni sarebbero cinque copie da 1 GB di dati
  gia' presenti, cioe' esattamente cio' che la Fase 7A ha cancellato.
- **Educato con la fonte**: una richiesta alla volta, `--sleep` secondi fra una
  partita e l'altra. Abbassarlo fa scattare il blocco.

La risoluzione campionato-stagione sta in `target.py`, che non importa selenium
ed e' percio' verificabile dai test senza browser ne' rete. `--dry-run` stampa
bersagli, percorsi e stato di avanzamento senza aprire niente.

Nota: main.py, scrape_matches.py e target.py devono essere nella stessa cartella.

**I termini d'uso di WhoScored non sono mai stati verificati**
(`docs/regole_fantacalcio.md` §7.1, terza conseguenza): l'autorizzazione
ottenuta riguarda Fantacalcio.it e non si estende a questa fonte. Va accertato
prima di lanciare lo scraper sulle stagioni arretrate.
"""

import json
import sys
import time
from datetime import datetime as dt

import pandas as pd

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = None
from bs4 import BeautifulSoup as soup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# NB: da main.py si riusa solo getMatchData.
#  - getFixtureData usa prev_btn.click(), che WhoScored fa fallire con
#    ElementClickInterceptedException perche' un banner pubblicitario copre il
#    bottone  ->  vedi _get_fixture_data() piu' sotto;
#  - getSortedData fa strptime con formato inglese ('%A, %b %d %Y'), ma il sito
#    restituisce le date localizzate ('venerdi, mag 22 2026')
#    ->  vedi _parse_date() / _sort_matches() piu' sotto.
from main import getMatchData, main_url

# Campionato, stagione e percorsi non sono piu' globali del modulo: sono un
# `Target`, che li tiene insieme e li rende immutabili. Finche' erano cinque
# variabili globali, una stagione alla volta era l'unica cosa possibile.
from target import (Target, parser, report_completeness, stato,  # noqa: E402
                    targets)
import pagina  # noqa: E402


# ──────────────────────────────────────────────
#  CONFIGURAZIONE
# ──────────────────────────────────────────────
MINIMIZE_WINDOW = True
MAX_URL_PASSES = 4            # passate massime sul calendario per colmare i buchi


# ──────────────────────────────────────────────
#  Riuso di createEventsDF (con fix playerId/teamId) e build_driver.
#  Fino alla Fase 7A il file si chiamava "Scrape matches.py" e lo spazio nel
#  nome impediva l'import: andava caricato per percorso con importlib. Il
#  rinomino a scrape_matches.py elimina l'aggiramento invece di trasportarlo.
# ──────────────────────────────────────────────
import scrape_matches as _sm  # noqa: E402

createEventsDF = _sm.createEventsDF
build_driver = _sm.build_driver


# ──────────────────────────────────────────────
#  RACCOLTA URL PARTITE
# ──────────────────────────────────────────────
def _accept_cookies(driver):
    for xpath in ('//*[@class=" css-gweyaj"]', '//button[contains(., "AGREE")]'):
        try:
            driver.find_element(By.XPATH, xpath).click()
            time.sleep(1)
            return
        except (NoSuchElementException, WebDriverException):
            continue


def _select_season(driver, season):
    """Seleziona la stagione nel menu a tendina, accettando '2025/2026' o '2025/26'."""
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'seasons')))
    select = Select(driver.find_element(By.ID, 'seasons'))
    available = [opt.text.strip() for opt in select.options]

    wanted = season.replace(' ', '')
    short = wanted.replace('/20', '/')            # 2025/2026 -> 2025/26
    for label in available:
        normalized = label.replace(' ', '')
        if normalized in (wanted, short):
            select.select_by_visible_text(label)
            time.sleep(5)
            return label

    raise RuntimeError(f"Stagione '{season}' non trovata. Disponibili: {available}")


# Mesi in italiano e in inglese: WhoScored localizza le date in base al dominio
# / alla lingua del browser, quindi accettiamo entrambe le forme.
MONTHS = {
    'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
    'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12,
    'jan': 1, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
    'oct': 10, 'dec': 12,
}


def _parse_date(text):
    """'venerdi, mag 22 2026' / 'Friday, May 22 2026' -> datetime. None se illeggibile.

    Il giorno della settimana viene scartato prima del parsing: 'martedi' inizia
    per 'mar' e verrebbe letto come marzo.
    """
    body = text.rsplit(',', 1)[-1] if ',' in text else text

    month = day = year = None
    for token in body.split():
        token = token.strip('.')
        if token.isdigit():
            value = int(token)
            if value > 1900:
                year = value
            elif day is None:
                day = value
        elif month is None and len(token) <= 4:
            month = MONTHS.get(token.lower()[:3])

    if month and day and year:
        return dt(year, month, day)
    return None


def _sort_matches(matches):
    """Ordina cronologicamente.

    Le partite con data illeggibile (rinviate/riprogrammate) NON vengono scartate
    ma messe in fondo: per scaricare gli eventi serve solo l'URL, e buttarle via
    faceva sparire partite realmente giocate. Se poi la pagina non ha dati,
    getMatchData fallisce e la partita viene contata tra gli errori.
    """
    dated = [(_parse_date(m['date']), m) for m in matches]
    valid = sorted([(d, m) for d, m in dated if d is not None], key=lambda pair: pair[0])
    undated = [m for d, m in dated if d is None]

    if undated:
        print(f"  {len(undated)} partite con data non leggibile (tenute, messe in fondo)")

    return [m for _, m in valid] + undated


def _click_prev_day(driver):
    """Clicca il bottone 'giorno precedente'. Restituisce False quando non c'e' piu'.

    WhoScored piazza banner pubblicitari sopra il bottone: il click nativo di
    Selenium fallisce con ElementClickInterceptedException, quindi si ripiega
    sul click via JavaScript, che ignora gli elementi sovrapposti.
    """
    try:
        btn = driver.find_element(By.ID, 'dayChangeBtn-prev')
    except NoSuchElementException:
        return False

    if btn.get_attribute('disabled') is not None:
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        btn.click()
    except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
        try:
            driver.execute_script("arguments[0].click();", btn)
        except WebDriverException:
            return False
    return True


def _page_signature(driver):
    """Identifica la pagina di calendario corrente tramite le date mostrate."""
    try:
        headers = driver.find_elements(By.CLASS_NAME, 'Accordion-module_header__HqzWD')
        return tuple(h.text for h in headers)
    except StaleElementReferenceException:
        return ()


def _wait_page_change(driver, previous, timeout=15):
    """Attende che il calendario mostri date diverse. False se non cambia (fine)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        current = _page_signature(driver)
        if current and current != previous:
            time.sleep(0.5)   # lascia finire il rendering delle righe
            return True
    return False


def _force_render(driver, max_scrolls=15):
    """Scorre la pagina finche' il numero di righe si stabilizza.

    Le righe partita sono renderizzate in modo lazy: senza scroll, le date in
    fondo alla pagina non entrano mai nel DOM e le relative partite si perdono.
    """
    previous, stable = -1, 0
    for _ in range(max_scrolls):
        rows = len(driver.find_elements(By.CLASS_NAME, 'Match-module_row__zwBOn'))
        # servono due letture identiche di fila: con una sola si rischia di
        # fermarsi in una pausa del caricamento e perdere le ultime date
        stable = stable + 1 if rows and rows == previous else 0
        if stable >= 2:
            break
        previous = rows
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(0.3)


def _parse_visible_fixtures(driver):
    """Legge tutte le partite presenti nella pagina di calendario corrente."""
    found = []

    for dates in driver.find_elements(By.CLASS_NAME, 'Accordion-module_accordion__UuHD0'):
        try:
            date_row = dates.find_element(By.CLASS_NAME, 'Accordion-module_header__HqzWD')
            date_text = date_row.text
            rows = dates.find_elements(By.CLASS_NAME, 'Match-module_row__zwBOn')
        except (NoSuchElementException, StaleElementReferenceException):
            continue

        for row in rows:
            try:
                href = row.find_element(By.TAG_NAME, 'a').get_attribute('href') or ''
                if 'live' not in href:
                    continue
                element = soup(row.get_attribute('innerHTML'), features='lxml')
            except (NoSuchElementException, StaleElementReferenceException):
                continue

            teams_tag = element.find('div', {'class': 'Match-module_teams__sGVeq'})
            link_tag = element.find('a')
            if teams_tag is None or link_tag is None:
                continue

            found.append({
                'date':  date_text,
                'home':  teams_tag.find_all('a')[0].text,
                'away':  teams_tag.find_all('a')[1].text,
                'score': ':'.join([t.text for t in link_tag.find_all('span')]),
                'url':   link_tag['href'],
            })

    return found


def _get_fixture_data(driver, max_pages=100):
    """Naviga il calendario all'indietro raccogliendo tutte le partite.

    Rispetto a getFixtureData di main.py (che aspetta 1.5s fissi dopo il click):
    attende che le date mostrate cambino davvero prima di leggere. Con l'attesa
    fissa, se la pagina non aveva ancora renderizzato si rileggeva la stessa
    pagina e si cliccava di nuovo 'precedente', saltando una pagina intera.
    """
    matches_ls = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        _force_render(driver)
        signature = _page_signature(driver)

        for match in _parse_visible_fixtures(driver):
            if match['url'] not in seen_urls:
                seen_urls.add(match['url'])
                matches_ls.append(match)

        print(f"\r  pagina calendario {page}: {len(matches_ls)} partite trovate", end='', flush=True)

        if not _click_prev_day(driver):
            break

        if not _wait_page_change(driver, signature):
            # il click potrebbe non aver fatto effetto (overlay, pagina occupata):
            # riprova una volta prima di concludere che il calendario e' finito
            if not _click_prev_day(driver) or not _wait_page_change(driver, signature):
                break

    print()
    return matches_ls


def _scrape_current_fixtures(driver):
    driver.execute_script("window.scrollTo(0, 400)")
    matches = _get_fixture_data(driver)
    # NB: niente filtro sulle date '?': una partita rinviata e poi recuperata
    # ha comunque i suoi eventi, e scartarla qui la faceva sparire dal calendario
    return _sort_matches(matches)


def _script_di(driver):
    """Il tag <script> con i dati partita, o None se non c'e'.

    Non solleva: serve a *diagnosticare* un fallimento gia' avvenuto, e
    un'eccezione qui maschererebbe quella vera.
    """
    try:
        return driver.find_element(
            By.XPATH, '//*[@id="layout-wrapper"]/script[1]').get_attribute('innerHTML')
    except WebDriverException:
        return None


def _select_stage(driver, index):
    """Seleziona uno stage, ripiegando su JavaScript se un banner copre il menu.

    E' lo stesso problema gia' noto per il bottone 'giorno precedente'
    (`_click_prev_day`): WhoScored piazza banner pubblicitari sopra i controlli e
    il click nativo di Selenium fallisce con ElementClickInterceptedException.
    Sul menu `stages` non era gestito, e il costo non era una pagina persa ma
    **un'intera stagione**: la 2022-2023 si e' interrotta esattamente qui, con
    `<select id="stages"> is not clickable ... another element obscures it`.

    Il click via JavaScript ignora gli elementi sovrapposti, ma non fa scattare
    da solo il ricaricamento: serve l'evento 'change' esplicito, altrimenti la
    pagina resta sullo stage precedente e si rileggono le stesse partite.
    """
    el = driver.find_element(By.ID, 'stages')
    try:
        Select(el).select_by_index(index)
    except (ElementClickInterceptedException, StaleElementReferenceException,
            WebDriverException):
        driver.execute_script(
            "arguments[0].selectedIndex = arguments[1];"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el, index)


def get_match_urls(driver, target: Target):
    """Restituisce la lista di dict {date, home, away, score, url} della stagione."""
    driver.get(target.url_competizione(main_url))
    time.sleep(5)
    _accept_cookies(driver)

    label = _select_season(driver, target.stagione_sito)
    print(f"Stagione selezionata: {label}")

    all_urls = []
    try:
        stages = Select(driver.find_element(By.ID, 'stages'))
        n_stages = len(stages.options)
        for i in range(n_stages):
            # rileggo l'elemento a ogni giro: la pagina si ricarica dopo il click
            stages = Select(driver.find_element(By.ID, 'stages'))
            stage_name = stages.options[i].text
            print(f"  Stage: {stage_name}")
            _select_stage(driver, i)
            time.sleep(5)
            all_urls += _scrape_current_fixtures(driver)
    except (NoSuchElementException, TimeoutException,
            ElementClickInterceptedException):
        # Serie A: normalmente nessun menu "stages". Se c'e' ma non e'
        # utilizzabile, si legge comunque il calendario visibile invece di
        # perdere la stagione: vedi _select_stage.
        all_urls += _scrape_current_fixtures(driver)

    # dedup per URL, mantenendo l'ordine cronologico
    unique = {d['url']: d for d in all_urls}
    return _sort_matches(list(unique.values()))


def load_match_urls(driver, target: Target, refresh=False):
    cache = target.cache_url
    cached = []
    if cache.exists():
        cached = json.loads(cache.read_text(encoding='utf-8'))
        print(f"Lista partite dalla cache: {len(cached)} match ({cache})")
        if not refresh and report_completeness(cached):
            return cached
        print('\nRiscansione del calendario per recuperare le partite mancanti...')

    # la navigazione del calendario puo' perdere qualche pagina: si ripassa
    # finche' il calendario e' completo, sommando i risultati alla cache
    merged = {m['url']: m for m in cached}
    urls = _sort_matches(list(merged.values()))

    for attempt in range(1, MAX_URL_PASSES + 1):
        print(f"\n--- Passata {attempt}/{MAX_URL_PASSES} sul calendario ---")
        found = get_match_urls(driver, target)

        new = [m for m in found if m['url'] not in merged]
        merged.update({m['url']: m for m in found})
        urls = _sort_matches(list(merged.values()))

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(urls, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"Trovate {len(found)} partite in questa passata ({len(new)} nuove) "
              f"-> {len(urls)} totali in {cache.name}")

        if report_completeness(urls):
            break
        if not new:
            print('Nessuna partita nuova in questa passata: mi fermo.')
            break

    return urls


# ──────────────────────────────────────────────
#  BARRA DI AVANZAMENTO
# ──────────────────────────────────────────────
def _fmt_time(seconds):
    seconds = int(seconds)
    return f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'


class Progress:
    """Barra di avanzamento da terminale.

    Usa tqdm se installato, altrimenti ripiega su una barra ASCII equivalente
    (niente caratteri unicode, cosi' funziona anche su console Windows legacy).
    """

    BAR_WIDTH = 30

    def __init__(self, total, desc='Partite'):
        self.total = total
        self.desc = desc
        self.done = 0
        self.stats = {'ok': 0, 'skip': 0, 'nodata': 0, 'err': 0}
        self.started = time.time()
        self._last_len = 0
        self.bar = tqdm(total=total, desc=desc, unit='match', ncols=100,
                        bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]{postfix}'
                        ) if tqdm else None
        if self.bar is None:
            self._render()

    def _postfix(self):
        return ('ok {ok} | skip {skip} | senza dati {nodata} | err {err}'
                .format(**self.stats))

    def _render(self):
        filled = int(self.BAR_WIDTH * self.done / self.total) if self.total else self.BAR_WIDTH
        elapsed = time.time() - self.started
        eta = (elapsed / self.done) * (self.total - self.done) if self.done else 0
        line = (f"{self.desc} |{'#' * filled}{'-' * (self.BAR_WIDTH - filled)}| "
                f"{self.done}/{self.total} [{_fmt_time(elapsed)}<{_fmt_time(eta)}] {self._postfix()}")
        # padding invece di escape ANSI: funziona anche su console Windows legacy
        sys.stdout.write('\r' + line.ljust(self._last_len))
        sys.stdout.flush()
        self._last_len = len(line)

    def write(self, msg):
        """Stampa un messaggio senza rompere la barra."""
        if self.bar is not None:
            self.bar.write(msg)
        else:
            sys.stdout.write('\r' + msg.ljust(self._last_len) + '\n')
            self._last_len = 0
            self._render()

    def update(self, outcome):
        """outcome: 'ok' | 'skip' | 'nodata' | 'err'.

        `nodata` non e' un errore: e' una partita che la fonte non ha. Tenerlo
        separato da `err` e' l'unico modo perche' il riepilogo dica se c'e'
        qualcosa da ritentare.
        """
        self.stats[outcome] += 1
        self.done += 1
        if self.bar is not None:
            self.bar.set_postfix_str(self._postfix(), refresh=False)
            self.bar.update(1)
        else:
            self._render()

    def close(self):
        if self.bar is not None:
            self.bar.close()
        else:
            self._render()
            sys.stdout.write('\n')
            sys.stdout.flush()


# ──────────────────────────────────────────────
#  SCRAPING EVENTI
# ──────────────────────────────────────────────
def match_id_from_url(url):
    parts = [p for p in url.split('/') if p]
    for i, part in enumerate(parts):
        if part.lower() in ('matches', 'match') and i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1]


def scarica_partite(driver, target: Target, match_urls, sleep=7.0):
    """Scarica gli eventi delle partite non ancora su disco.

    Il `continue` su `out_path.exists()` e' il vincolo 9 in una riga: nessuna
    esecuzione puo' sovrascrivere grezzo gia' acquisito. Vale anche per un file
    corrotto o troncato — cancellarlo a mano e' una decisione, non un effetto
    collaterale di un rilancio.
    """
    target.dir_partite.mkdir(parents=True, exist_ok=True)

    failed = []
    senza_dati = []
    scraped = 0
    progress = Progress(len(match_urls), desc=str(target))

    try:
        for fixture in match_urls:
            match_url = main_url.rstrip('/') + fixture['url']
            match_id = match_id_from_url(fixture['url'])
            out_path = target.dir_partite / f'{match_id}.csv'
            label = f"{fixture['home']} - {fixture['away']} ({fixture['date']})"

            if out_path.exists():
                progress.update('skip')
                continue

            try:
                if scraped > 0:
                    time.sleep(sleep)

                match_data = getMatchData(driver, match_url, display=False, close_window=False)
                events_df = createEventsDF(match_data)
                events_df.to_csv(out_path, index=False)
                scraped += 1
                progress.write(f"  ok   {label}: {len(events_df)} eventi -> {out_path.name}")
                progress.update('ok')

            except Exception as exc:
                # `substring not found` puo' voler dire due cose opposte: un
                # difetto di lettura, oppure che la fonte non ha i dati. Si
                # guarda la pagina invece di indovinare — vedi pagina.py.
                verdetto = pagina.diagnosi(_script_di(driver))
                if verdetto == pagina.DATI_ASSENTI:
                    progress.write(f"  --   {label}: {pagina.spiega(verdetto)}")
                    progress.update('nodata')
                    senza_dati.append((match_url, label))
                else:
                    progress.write(f"  ERR  {label}: {exc}")
                    progress.update('err')
                    failed.append((match_url, str(exc)))
    finally:
        progress.close()

    return failed, senza_dati


def merge_matches(target: Target):
    files = sorted(target.dir_partite.glob('*.csv'))
    if not files:
        return pd.DataFrame()

    progress = Progress(len(files), desc='Unione CSV      ')
    frames = []
    try:
        for path in files:
            frames.append(pd.read_csv(path, low_memory=False))
            progress.update('ok')
    finally:
        progress.close()

    return pd.concat(frames, ignore_index=True)


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def _stampa_dry_run(bersagli):
    """Cosa verrebbe fatto, senza aprire un browser ne' toccare la rete.

    Non e' una comodita': i termini d'uso di WhoScored non sono ancora stati
    verificati, quindi serve un modo di controllare la parametrizzazione che
    non passi dalla fonte.
    """
    print(f"DRY RUN — {len(bersagli)} stagion{'e' if len(bersagli) == 1 else 'i'}, "
          "niente browser, niente rete\n")
    for t in bersagli:
        s = stato(t)
        print(f"  {t}")
        print(f"    stagione sul sito   {t.stagione_sito}")
        print(f"    url competizione    {t.url_competizione(main_url)}")
        print(f"    CSV partita         {t.dir_partite}")
        print(f"    cache calendario    {t.cache_url}")
        print(f"    gia' su disco       {s['csv_su_disco']} CSV"
              + (f" | {s['partite_in_cache']} in cache"
                 f" | {s['da_scaricare']} da scaricare" if s['partite_in_cache'] else
                 " | nessuna cache calendario: la prima passata la costruisce"))
        print()


def scarica(target: Target, args):
    """Una stagione intera. Restituisce (fallite ritentabili, senza dati)."""
    print(f"\n{'=' * 70}\n{target}\n{'=' * 70}")

    driver = build_driver()
    if MINIMIZE_WINDOW:
        driver.minimize_window()

    try:
        match_urls = load_match_urls(driver, target, refresh=args.refresh_urls)
        failed, senza_dati = scarica_partite(
            driver, target, match_urls, sleep=args.sleep)
    finally:
        driver.quit()

    if args.merge:
        df = merge_matches(target)
        if df.empty:
            print('Nessun dato da unire.')
        else:
            target.file_unito.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(target.file_unito, index=False)
            print(f"\n{len(df)} eventi da {df['matchId'].nunique()} partite "
                  f"-> {target.file_unito}")

    n = len(list(target.dir_partite.glob('*.csv')))
    print(f"\n{target}: {n} CSV su disco.")
    return failed


def main(argv=None):
    args = parser().parse_args(argv)

    # I bersagli si risolvono per primi, e un errore qui e' fatale: una stagione
    # mal formata o un campionato senza codici verificati deve fermare tutto
    # PRIMA di aprire un browser, non dopo trenta secondi su una pagina.
    try:
        bersagli = targets(args.league, args.season)
    except ValueError as exc:
        sys.exit(f"errore: {exc}")

    if args.dry_run:
        _stampa_dry_run(bersagli)
        return

    # Una stagione che fallisce non deve fermare le altre: sono acquisizioni
    # indipendenti, e la ripartibilita' vale anche fra stagioni.
    esiti = {}
    for target in bersagli:
        try:
            esiti[str(target)] = scarica(target, args)
        except Exception as exc:            # noqa: BLE001 — vale per l'intera stagione
            print(f"\n!! {target} interrotta: {exc}")
            esiti[str(target)] = ([('<intera stagione>', str(exc))], [])

    print(f"\n{'=' * 70}\nRIEPILOGO\n{'=' * 70}")
    ritentabili = 0
    for nome, (failed, senza_dati) in esiti.items():
        t = Target(args.league, nome.split()[-1])
        n = len(list(t.dir_partite.glob('*.csv'))) if t.dir_partite.is_dir() else 0
        ritentabili += len(failed)
        coda = []
        if failed:
            coda.append(f"{len(failed)} da ritentare")
        if senza_dati:
            coda.append(f"{len(senza_dati)} senza dati alla fonte")
        print(f"  {nome}: {n} CSV su disco" + (f" | {' | '.join(coda)}" if coda else ""))
        for url, err in failed:
            print(f"      ritentabile  {url}  ({err})")
        # Elencate a parte, e senza la parola "fallita": ritentarle non serve,
        # e chiamarle errori manda a cercare un difetto che non c'e'.
        for url, label in senza_dati:
            print(f"      senza dati   {label}  {url}")

    if ritentabili:
        print(f"\n{ritentabili} partite ritentabili: rilancia lo script, quelle "
              "gia' scaricate vengono saltate.")
    if any(sd for _, sd in esiti.values()):
        print("Le partite 'senza dati' NON si recuperano rilanciando: "
              "matchCentreData e' null alla fonte. Vanno dichiarate come assenti.")


if __name__ == '__main__':
    main()
