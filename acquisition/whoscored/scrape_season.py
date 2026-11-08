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

**Autorizzazione**: dichiarata dall'utente per WhoScored il 2026-07-31
(`docs/regole_fantacalcio.md` §7.1, terza conseguenza) ed **estesa il 2026-08-14
a Premier League, Liga, Bundesliga e Ligue 1** (§7.2, decisione 1). Il
repository registra la dichiarazione, non conserva il documento.

Fino al 2026-08-14 questa docstring diceva che i termini d'uso non erano mai
stati verificati: era vero quando fu scritta e ha smesso di esserlo con §7.1,
restando indietro per due fasi. **Una nota di cautela che invecchia senza
accorgersene e' peggio della sua assenza**, perche' sembra ancora una misura.
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
from target import (Target, avanzamento, parser, report_completeness,  # noqa: E402
                    stato, targets)
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
    for i, label in enumerate(available):
        normalized = label.replace(' ', '')
        if normalized in (wanted, short):
            # Per INDICE e non per testo: il ripiego JavaScript puo' agire solo
            # su `selectedIndex`, e avere due strade che scelgono l'opzione con
            # criteri diversi e' il modo di scoprire tardi che divergono.
            _seleziona_con_ripiego(driver, driver.find_element(By.ID, 'seasons'), i)
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


#: I due bottoni di navigazione fra i giorni del calendario.
#:
#: `-next` **e' stato accertato il 2026-09-03** da
#: `verifica_calendario.py`: esiste, non e' disabilitato e muove la pagina. Fino
#: ad allora non compariva in nessun punto del repository, e che ci fosse era
#: un'ipotesi — per questo la verifica e' venuta prima di questo codice.
#: Ritorno a capo per le stampe di avanzamento sulla stessa riga.
CR = chr(13)

BTN_PREV = 'dayChangeBtn-prev'
BTN_NEXT = 'dayChangeBtn-next'


def _click_day(driver, id_bottone):
    """Clicca un bottone di navigazione. False quando non si puo' andare oltre.

    **Sta in un posto solo per i due versi**, ed e' la lezione di
    `_seleziona_con_ripiego`: il ripiego JS sul banner pubblicitario e' gia'
    costato due stagioni intere quando era stato applicato al punto d'uso invece
    che alla classe di difetto. Averne una copia per `prev` e una per `next`
    vorrebbe dire poterle far divergere in silenzio.
    """
    try:
        btn = driver.find_element(By.ID, id_bottone)
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


def _click_prev_day(driver):
    """Il giorno precedente. E' la navigazione dell'acquisizione degli eventi."""
    return _click_day(driver, BTN_PREV)


def _click_next_day(driver):
    """Il giorno successivo. E' la navigazione del CALENDARIO delle partite future."""
    return _click_day(driver, BTN_NEXT)


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


#: Il discriminante fra una partita GIOCATA e una da giocare, **accertato** il
#: 2026-09-03 da `verifica_calendario.py` e non assunto: su 30 righe di una
#: stagione conclusa il criterio le da' tutte giocate e tutte presenti in
#: `matches.json`; su 30 righe future le da' tutte da giocare e nessuna presente.
#: Una partita futura ha `/show/` nell'href (non `/preview/`, che era la
#: congettura) e mostra `-:-` al posto del punteggio.
SEGMENTO_GIOCATA = '/live/'


def _e_giocata(href):
    """Una definizione in un posto solo: la usano il parser e i test."""
    return SEGMENTO_GIOCATA in (href or '')


def _parse_visible_fixtures(driver, includi_future=False):
    """Legge le partite della pagina di calendario corrente.

    `includi_future=False` e' il comportamento storico e **non cambia di un
    bit**: si tengono le sole righe giocate, che e' cio' di cui l'acquisizione
    degli eventi ha bisogno. Un test lo blocca.

    Con `includi_future=True` si tengono anche le righe da giocare, e allora
    valgono due regole che non sono cosmetiche:

    - **`score` NON viene scritto per una partita da giocare.** Il campo esiste
      per contenere un risultato; su una riga futura il sito mostra `-:-`, e su
      altre localizzazioni potrebbe mostrare l'orario. `20:45` ha esattamente la
      forma di un punteggio, quindi metterlo li' produrrebbe un dato ambiguo
      **per costruzione**, che nessun controllo a valle saprebbe piu' separare.
    - **la riga porta `giocata`**, cioe' il fatto, invece di lasciarlo dedurre
      dalla forma di un altro campo.
    """
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
                giocata = _e_giocata(href)
                if not giocata and not includi_future:
                    continue
                element = soup(row.get_attribute('innerHTML'), features='lxml')
            except (NoSuchElementException, StaleElementReferenceException):
                continue

            teams_tag = element.find('div', {'class': 'Match-module_teams__sGVeq'})
            link_tag = element.find('a')
            if teams_tag is None or link_tag is None:
                continue

            riga = {
                'date':  date_text,
                'home':  teams_tag.find_all('a')[0].text,
                'away':  teams_tag.find_all('a')[1].text,
                'score': ':'.join([t.text for t in link_tag.find_all('span')]),
                'url':   link_tag['href'],
            }
            if includi_future:
                riga['giocata'] = giocata
                if not giocata:
                    # mai un orario dentro `score`: sarebbe ambiguo per forma
                    riga['score'] = None
            found.append(riga)

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


def _get_calendario_futuro(driver, max_pages=40):
    """Naviga il calendario IN AVANTI e raccoglie le partite da giocare.

    E' il gemello di `_get_fixture_data`, con tre differenze dichiarate:

    1. va in **avanti** (`BTN_NEXT`), che e' cio' che
       `verifica_calendario.py` ha accertato esistere;
    2. legge anche le righe non giocate (`includi_future=True`);
    3. **si ferma quando smette di trovare partite da giocare**, non quando la
       pagina non si muove: oltre l'ultima giornata il calendario continua a
       esistere e a scorrere, vuoto, per sempre.

    `max_pages` e' un tetto, non il criterio di arresto: senza, un bottone che
    resta abilitato all'infinito farebbe girare lo scraper per sempre.
    """
    trovate = {}
    vuote_di_seguito = 0

    for page in range(1, max_pages + 1):
        _force_render(driver)
        signature = _page_signature(driver)

        nuove = 0
        for match in _parse_visible_fixtures(driver, includi_future=True):
            if match.get('giocata'):
                continue                      # le giocate stanno in matches.json
            if match['url'] not in trovate:
                trovate[match['url']] = match
                nuove += 1

        vuote_di_seguito = 0 if nuove else vuote_di_seguito + 1
        print(f"{CR}  calendario, pagina {page}: "
              f"{len(trovate)} partite da giocare",
              end='', flush=True)

        # Tre pagine consecutive senza niente di nuovo: la stagione e' finita.
        # Il numero e' un margine per i turni infrasettimanali vuoti, non una
        # soglia stimata.
        if vuote_di_seguito >= 3:
            break
        if not _click_next_day(driver):
            break
        if not _wait_page_change(driver, signature):
            if not _click_next_day(driver) or not _wait_page_change(driver, signature):
                break

    print()
    return _sort_matches(list(trovate.values()))


def verifica_calendario_futuro(righe):
    """Controlli di struttura che valgono su un calendario PARZIALE.

    Non si puo' pretendere 38 giornate: la Bundesliga ne ha 34, la Ligue 1 pure
    dalla 2023-24, e un calendario della stagione in corso e' incompleto per
    definizione (i denominatori si **contano**, mai si assumono — §7.2). Cio' che
    vale comunque e' piu' debole ma falsificabile:

    - nessuna squadra gioca contro se stessa;
    - nessuna squadra compare due volte nella stessa data;
    - nessun accoppiamento ordinato (casa, trasferta) compare piu' di una volta;
    - nessuna riga ha un punteggio.

    Ritorna un dizionario di violazioni: **vuoto** significa che i controlli
    passano. Non solleva: il chiamante decide se un calendario storto va
    scartato o riportato, e questa funzione non deve poterlo nascondere.
    """
    problemi = {}

    stesse = [r for r in righe if r['home'] == r['away']]
    if stesse:
        problemi['squadra_contro_se_stessa'] = [r['url'] for r in stesse]

    per_data = {}
    for r in righe:
        for squadra in (r['home'], r['away']):
            per_data.setdefault((r['date'], squadra), []).append(r['url'])
    doppie = {f"{d} / {sq}": u for (d, sq), u in per_data.items() if len(u) > 1}
    if doppie:
        problemi['squadra_due_volte_nello_stesso_giorno'] = doppie

    coppie = {}
    for r in righe:
        coppie.setdefault((r['home'], r['away']), []).append(r['url'])
    ripetute = {f"{a} - {b}": u for (a, b), u in coppie.items() if len(u) > 1}
    if ripetute:
        problemi['accoppiamento_ripetuto'] = ripetute

    con_punteggio = [r['url'] for r in righe if r.get('score')]
    if con_punteggio:
        problemi['partita_futura_con_punteggio'] = con_punteggio

    return problemi


def raccogli_calendario(driver, target: Target, max_pages=40):
    """Il calendario delle partite da giocare, in un file SEPARATO.

    Non tocca `matches.json`, e la ragione sta in `config.calendario_json`: quel
    file e' il criterio di arresto dello scraper e il denominatore di
    `avanzamento`, e mescolarci le partite future romperebbe entrambi in
    silenzio.
    """
    _apri_calendario(driver, target)
    righe = _get_calendario_futuro(driver, max_pages=max_pages)
    problemi = verifica_calendario_futuro(righe)

    out = target.cache_calendario
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'campionato': target.league,
        'stagione': target.season,
        'raccolto': dt.now().isoformat(timespec='seconds'),
        'fonte': target.url_competizione(main_url),
        'criterio_giocata': f"una partita e' giocata se l'href contiene "
                            f"{SEGMENTO_GIOCATA!r} (accertato da "
                            f"verifica_calendario.py il 2026-09-03)",
        'partite': len(righe),
        'verifica_struttura': problemi or 'nessuna violazione',
        'righe': righe,
    }, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"  calendario: {len(righe)} partite da giocare -> {out}")
    if problemi:
        print(f"  ATTENZIONE, la struttura non torna: {sorted(problemi)}")
    return righe, problemi


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


def _seleziona_con_ripiego(driver, el, index):
    """Sceglie l'opzione `index` di un `<select>`, aggirando i banner sovrapposti.

    **Sta in un posto solo perche' e' gia' costato due stagioni intere.**
    WhoScored piazza banner pubblicitari sopra i controlli e il click nativo di
    Selenium fallisce con `ElementClickInterceptedException`:

      - la prima volta sul menu `stages`, e costo' la 2022-2023 della Serie A
        (documentato in CLAUDE.md, acquisizione WhoScored 2021-2026);
      - la seconda sul menu `seasons`, e costo' la 2023-2024 della Premier
        League: `<select id="seasons"> is not clickable at point (539,173)
        because another element <div class="a__sc-np32r2-0 ..."> obscures it`.

    La prima volta il rimedio fu applicato **al solo `stages`**, cioe' al punto
    in cui si era manifestato invece che alla classe di difetto. Ecco perche' e'
    tornato su un altro menu: un rimedio locale a un problema generale aspetta
    solo il prossimo punto d'uso.

    Il click via JavaScript ignora gli elementi sovrapposti, ma **non fa
    scattare da solo il ricaricamento**: serve l'evento `change` esplicito,
    altrimenti la pagina resta sull'opzione precedente e si rileggono gli stessi
    dati credendo di averne cambiati.
    """
    try:
        Select(el).select_by_index(index)
    except (ElementClickInterceptedException, StaleElementReferenceException,
            WebDriverException):
        driver.execute_script(
            "arguments[0].selectedIndex = arguments[1];"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el, index)


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
    _seleziona_con_ripiego(driver, driver.find_element(By.ID, 'stages'), index)


def _apri_calendario(driver, target: Target):
    """Apre la pagina della competizione e seleziona la stagione chiesta.

    **Sta in un posto solo perche' i chiamanti sono due**: l'acquisizione degli
    eventi (`get_match_urls`) e la raccolta del calendario futuro
    (`raccogli_calendario`). Averne due copie e' esattamente il difetto che ha
    prodotto un calendario vuoto la prima volta che `--solo-calendario` e' stato
    eseguito: quel ramo salta `load_match_urls`, quindi nessuno apriva la
    pagina, e lo scraper leggeva `about:blank` senza accorgersene.
    """
    driver.get(target.url_competizione(main_url))
    time.sleep(5)
    _accept_cookies(driver)
    label = _select_season(driver, target.stagione_sito)
    print(f"Stagione selezionata: {label}")
    return label


def get_match_urls(driver, target: Target):
    """Restituisce la lista di dict {date, home, away, score, url} della stagione."""
    _apri_calendario(driver, target)

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


def load_match_urls(driver, target: Target, refresh=False, in_corso=False):
    """Il calendario della stagione, dalla cache o dalla rete.

    `in_corso` cambia **due** cose, e nessuna delle due e' cosmetica.

    1. **Una passata sola invece di quattro.** Il criterio di arresto normale e'
       `report_completeness`, cioe' «tutte le squadre hanno il loro numero di
       partite». Una stagione che si sta giocando non lo soddisfa mai, quindi
       ogni esecuzione pagherebbe `MAX_URL_PASSES` navigazioni complete del
       calendario per cercare partite che non esistono ancora — settimana dopo
       settimana, verso una fonte di cui si e' ospiti.
    2. **La cache si rinfresca sempre.** E' l'esatto contrario del caso normale:
       li' una cache completa e' la risposta definitiva, qui e' vecchia di sette
       giorni per costruzione. Saltarla nasconderebbe proprio le partite nuove,
       che sono l'unica ragione per cui si sta rilanciando.

    Cio' che **non** cambia e' che le partite gia' in cache non si perdono mai:
    `merged` parte da loro e la passata nuova ci si somma. Una navigazione che
    non arrivasse fino a settembre non cancellerebbe settembre.
    """
    cache = target.cache_url
    cached = []
    if cache.exists():
        cached = json.loads(cache.read_text(encoding='utf-8'))
        print(f"Lista partite dalla cache: {len(cached)} match ({cache})")
        if not in_corso and not refresh and report_completeness(cached):
            return cached
        if not in_corso:
            print('Riscansione del calendario per le partite mancanti...')

    # la navigazione del calendario puo' perdere qualche pagina: si ripassa
    # finche' il calendario e' completo, sommando i risultati alla cache
    merged = {m['url']: m for m in cached}
    urls = _sort_matches(list(merged.values()))

    passate = 1 if in_corso else MAX_URL_PASSES
    for attempt in range(1, passate + 1):
        print(f"--- Passata {attempt}/{passate} sul calendario ---")
        found = get_match_urls(driver, target)

        new = [m for m in found if m['url'] not in merged]
        merged.update({m['url']: m for m in found})
        urls = _sort_matches(list(merged.values()))

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(urls, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"Trovate {len(found)} partite in questa passata ({len(new)} nuove) "
              f"-> {len(urls)} totali in {cache.name}")

        if in_corso:
            avanzamento(urls)
            break
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


# Firme di un browser MORTO, non di una partita che non si scarica. Selenium le
# riporta come normali eccezioni per-partita, e senza distinguerle lo scraper
# cicla sul resto della stagione fallendo tutto in pochi secondi: e' successo
# alla Ligue 1 2025-2026, dove lo spegnimento del PC ha ucciso geckodriver a
# quota 70 e le **236 partite rimanenti** sono state marcate ritentabili una per
# una. Nessun dato perso — erano tutte ritentabili davvero — ma il log diventa
# illeggibile e il riepilogo dice "236 da ritentare" dove la causa e' UNA.
FIRME_DRIVER_MORTO = (
    'without establishing a connection',
    'invalid session id',
    'session deleted',
    'browser has closed',
    'connection refused',
    'unable to connect',
)


def _driver_morto(exc: Exception) -> bool:
    testo = str(exc).lower()
    return any(f in testo for f in FIRME_DRIVER_MORTO)


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
                # Un browser morto non e' un problema DI QUESTA partita: e' la
                # fine della passata. Si ferma qui e si lascia il resto alla
                # ripresa, invece di marcare ritentabili centinaia di partite
                # mai davvero tentate.
                if _driver_morto(exc):
                    progress.write(
                        f"  STOP {label}: browser non piu' raggiungibile "
                        f"({str(exc).splitlines()[0][:80]}). "
                        f"Interrompo la stagione: le rimanenti restano da fare.")
                    failed.append((match_url, f"browser caduto: {exc}"))
                    break

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
def _stampa_dry_run(bersagli, in_corso=False):
    """Cosa verrebbe fatto, senza aprire un browser ne' toccare la rete.

    Non e' una comodita': i termini d'uso di WhoScored non sono ancora stati
    verificati, quindi serve un modo di controllare la parametrizzazione che
    non passi dalla fonte.
    """
    print(f"DRY RUN — {len(bersagli)} stagion{'e' if len(bersagli) == 1 else 'i'}, "
          "niente browser, niente rete")
    if in_corso:
        print("modo --in-corso: una passata sola sul calendario, cache "
              "sempre rinfrescata, incompletezza attesa e non un difetto")
    print("")
    for t in bersagli:
        s = stato(t)
        print(f"  {t}")
        print(f"    stagione sul sito   {t.stagione_sito}")
        print(f"    url competizione    {t.url_competizione(main_url)}")
        print(f"    CSV partita         {t.dir_partite}")
        print(f"    cache partite       {t.cache_url}")
        print(f"    calendario futuro   {t.cache_calendario}")
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

    solo_cal = getattr(args, 'solo_calendario', False)
    vuole_cal = solo_cal or getattr(args, 'calendario', False)

    try:
        if solo_cal:
            failed, senza_dati = [], []
        else:
            match_urls = load_match_urls(
                driver, target, refresh=args.refresh_urls,
                in_corso=getattr(args, 'in_corso', False))
            failed, senza_dati = scarica_partite(
                driver, target, match_urls, sleep=args.sleep)
        if vuole_cal:
            # **Dopo** gli eventi e nella STESSA sessione di browser: aprirne una
            # seconda raddoppierebbe le richieste alla fonte per niente.
            raccogli_calendario(driver, target)
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
    # **Si restituiscono ENTRAMBE le liste**, come la docstring dichiara e come
    # `main` spacchetta. Fino al 2026-08-14 qui c'era `return failed`, e la
    # contraddizione con la propria docstring e' rimasta invisibile per due
    # ragioni che vale la pena scrivere:
    #
    #   - con una lista di ESATTAMENTE due fallimenti lo spacchettamento in
    #     `main` riusciva, assegnando due URL alle variabili sbagliate: nessun
    #     errore, un riepilogo falso;
    #   - con zero fallimenti — cioe' **solo quando la stagione riesce del
    #     tutto** — sollevava `not enough values to unpack`.
    #
    # Ne segue che il difetto si manifestava all'ESITO MIGLIORE e taceva su
    # quelli mediocri. E' comparso alla prima stagione a copertura piena, la
    # Premier League 2025-2026 (380/380), non sulla Serie A che ne perdeva 12.
    return failed, senza_dati


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
        _stampa_dry_run(bersagli, in_corso=args.in_corso)
        return

    # Una stagione che fallisce non deve fermare le altre: sono acquisizioni
    # indipendenti, e la ripartibilita' vale anche fra stagioni.
    # La chiave e' il `Target` stesso (dataclass frozen, quindi hashabile) e non
    # la sua forma stampata: il riepilogo ricostruiva un Target da
    # `nome.split()[-1]`, cioe' rileggeva una stringa che aveva appena
    # formattato. Funzionava finche' `__str__` restava "campionato stagione", e
    # sarebbe diventato silenziosamente sbagliato al primo campionato con uno
    # spazio nel nome.
    esiti = {}
    for target in bersagli:
        try:
            esiti[target] = scarica(target, args)
        except Exception as exc:            # noqa: BLE001 — vale per l'intera stagione
            print(f"\n!! {target} interrotta: {exc}")
            esiti[target] = ([('<intera stagione>', str(exc))], [])

    print(f"\n{'=' * 70}\nRIEPILOGO\n{'=' * 70}")
    ritentabili = 0
    for t, (failed, senza_dati) in esiti.items():
        nome = str(t)
        n = len(list(t.dir_partite.glob('*.csv'))) if t.dir_partite.is_dir() else 0
        ritentabili += len(failed)
        coda = []
        if failed:
            coda.append(f"{len(failed)} da ritentare")
        if senza_dati:
            coda.append(f"{len(senza_dati)} senza dati alla fonte")
        # In una stagione in corso il divario fra calendario e CSV non e' un
        # difetto: sono le partite che non si sono ancora giocate. Senza questa
        # riga la copertura sembrerebbe sempre rotta, e la volta in cui lo fosse
        # davvero non si distinguerebbe da tutte le altre.
        if getattr(args, 'in_corso', False):
            resto = stato(t)['partite_in_cache'] - n - len(failed) - len(senza_dati)
            if resto > 0:
                coda.append(f"{resto} non ancora giocate")
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
