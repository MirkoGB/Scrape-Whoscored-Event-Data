# -*- coding: utf-8 -*-
"""
Scrape di TUTTI i dati evento della Serie A 2025/2026 da WhoScored.

Uso:
    python scrape_serie_a_2025_2026.py

Cosa fa:
    1. Apre la pagina della Serie A, seleziona la stagione 2025/2026 e raccoglie
       gli URL di tutte le partite giocate (salvati in cache JSON).
    2. Scarica gli eventi partita per partita, salvando un CSV per ogni match
       nella cartella `data/serie_a_2025_2026/`.
    3. Unisce tutto in un unico CSV finale.

Lo script e' riavviabile: le partite gia' salvate vengono saltate, quindi se
viene interrotto (o WhoScored blocca temporaneamente) basta rilanciarlo.

Nota: main.py e "Scrape matches.py" devono essere nella stessa cartella.
"""

import json
import sys
import time
from datetime import datetime as dt
from importlib import util as _util
from pathlib import Path

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


# ──────────────────────────────────────────────
#  CONFIGURAZIONE
# ──────────────────────────────────────────────
SEASON = '2025/2026'
COMPETITION_URL = main_url.rstrip('/') + '/regions/108/tournaments/5/italy-serie-a'

BASE_DIR = Path(__file__).resolve().parent
MATCHES_DIR = BASE_DIR / 'data' / 'serie_a_2025_2026'   # un CSV per partita
URLS_CACHE = BASE_DIR / 'data' / 'serie_a_2025_2026_matches.json'
OUTPUT_FILE = BASE_DIR / 'serie_a_2025_2026_events.csv'

SLEEP_BETWEEN_REQUESTS = 7    # secondi tra una partita e l'altra (evita il ban)
MINIMIZE_WINDOW = True
# La lista partite viene comunque ri-raccolta finche' la cache non e' completa
# (38 partite a squadra): metti True per forzare un giro anche se e' gia' completa.
REFRESH_URLS = False
MAX_URL_PASSES = 4            # passate massime sul calendario per colmare i buchi


# ──────────────────────────────────────────────
#  Riuso di createEventsDF (con fix playerId/teamId) e build_driver
#  definiti in "Scrape matches.py" (il nome col
#  spazio impedisce un import normale).
# ──────────────────────────────────────────────
def _load_scrape_matches_module():
    path = BASE_DIR / 'Scrape matches.py'
    if not path.exists():
        raise FileNotFoundError(
            f"Non trovo '{path.name}': serve per createEventsDF (fix playerId) e build_driver."
        )
    spec = _util.spec_from_file_location('scrape_matches', str(path))
    module = _util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sm = _load_scrape_matches_module()
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


def get_match_urls(driver, season=SEASON):
    """Restituisce la lista di dict {date, home, away, score, url} della stagione."""
    driver.get(COMPETITION_URL)
    time.sleep(5)
    _accept_cookies(driver)

    label = _select_season(driver, season)
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
            stages.select_by_index(i)
            time.sleep(5)
            all_urls += _scrape_current_fixtures(driver)
    except (NoSuchElementException, TimeoutException):
        # Serie A: normalmente nessun menu "stages"
        all_urls += _scrape_current_fixtures(driver)

    # dedup per URL, mantenendo l'ordine cronologico
    unique = {d['url']: d for d in all_urls}
    return _sort_matches(list(unique.values()))


def report_completeness(matches):
    """Stampa quante partite ha ogni squadra: in Serie A devono essere 38."""
    per_team = {}
    for match in matches:
        for team in (match['home'], match['away']):
            per_team[team] = per_team.get(team, 0) + 1

    expected = (len(per_team) - 1) * 2 if per_team else 0
    incomplete = {t: n for t, n in per_team.items() if n != expected}

    print(f"\nSquadre: {len(per_team)} | partite totali: {len(matches)} "
          f"(attese: {len(per_team) * expected // 2 if per_team else 0})")

    if not incomplete:
        print('Calendario completo.')
        return True

    print(f"Calendario INCOMPLETO - squadre con meno di {expected} partite:")
    for team, n in sorted(incomplete.items(), key=lambda p: p[1]):
        print(f"  {n:3d}/{expected}  {team}")
    print("Rilancia con REFRESH_URLS = True: i risultati si sommano alla cache.")
    return False


def load_match_urls(driver):
    cached = []
    if URLS_CACHE.exists():
        cached = json.loads(URLS_CACHE.read_text(encoding='utf-8'))
        print(f"Lista partite dalla cache: {len(cached)} match ({URLS_CACHE.name})")
        if not REFRESH_URLS and report_completeness(cached):
            return cached
        print('\nRiscansione del calendario per recuperare le partite mancanti...')

    # la navigazione del calendario puo' perdere qualche pagina: si ripassa
    # finche' il calendario e' completo, sommando i risultati alla cache
    merged = {m['url']: m for m in cached}
    urls = _sort_matches(list(merged.values()))

    for attempt in range(1, MAX_URL_PASSES + 1):
        print(f"\n--- Passata {attempt}/{MAX_URL_PASSES} sul calendario ---")
        found = get_match_urls(driver)

        new = [m for m in found if m['url'] not in merged]
        merged.update({m['url']: m for m in found})
        urls = _sort_matches(list(merged.values()))

        URLS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        URLS_CACHE.write_text(json.dumps(urls, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"Trovate {len(found)} partite in questa passata ({len(new)} nuove) "
              f"-> {len(urls)} totali in {URLS_CACHE.name}")

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
        self.stats = {'ok': 0, 'skip': 0, 'err': 0}
        self.started = time.time()
        self._last_len = 0
        self.bar = tqdm(total=total, desc=desc, unit='match', ncols=100,
                        bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]{postfix}'
                        ) if tqdm else None
        if self.bar is None:
            self._render()

    def _postfix(self):
        return 'ok {ok} | skip {skip} | err {err}'.format(**self.stats)

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
        """outcome: 'ok' | 'skip' | 'err'."""
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


def scrape_season(driver, match_urls):
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)

    failed = []
    scraped = 0
    progress = Progress(len(match_urls), desc='Serie A 2025/2026')

    try:
        for fixture in match_urls:
            match_url = main_url.rstrip('/') + fixture['url']
            match_id = match_id_from_url(fixture['url'])
            out_path = MATCHES_DIR / f'{match_id}.csv'
            label = f"{fixture['home']} - {fixture['away']} ({fixture['date']})"

            if out_path.exists():
                progress.update('skip')
                continue

            try:
                if scraped > 0:
                    time.sleep(SLEEP_BETWEEN_REQUESTS)

                match_data = getMatchData(driver, match_url, display=False, close_window=False)
                events_df = createEventsDF(match_data)
                events_df.to_csv(out_path, index=False)
                scraped += 1
                progress.write(f"  ok   {label}: {len(events_df)} eventi -> {out_path.name}")
                progress.update('ok')

            except Exception as exc:
                progress.write(f"  ERR  {label}: {exc}")
                progress.update('err')
                failed.append((match_url, str(exc)))
    finally:
        progress.close()

    return failed


def merge_matches():
    files = sorted(MATCHES_DIR.glob('*.csv'))
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
def main():
    driver = build_driver()
    if MINIMIZE_WINDOW:
        driver.minimize_window()

    try:
        match_urls = load_match_urls(driver)
        failed = scrape_season(driver, match_urls)
    finally:
        driver.quit()

    df = merge_matches()
    if df.empty:
        print('Nessun dato raccolto.')
        return

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nTotale: {len(df)} eventi da {df['matchId'].nunique()} partite")
    print(f"Salvato in '{OUTPUT_FILE.name}'")

    if failed:
        print(f"\nPartite fallite ({len(failed)}) - rilancia lo script per riprovarle:")
        for url, err in failed:
            print(f"  - {url}  ({err})")


if __name__ == '__main__':
    main()
