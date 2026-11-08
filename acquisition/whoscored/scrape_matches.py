# -*- coding: utf-8 -*-
"""
Script per scrapare eventi di partite da WhoScored
dato un set di URL di partite.

Uso:
    1. Inserisci i tuoi URL nella lista MATCH_URLS
    2. Esegui: python scrape_matches.py
    3. Il DataFrame verrà salvato in 'events.csv'

Nota: main.py deve essere nella stessa cartella.
"""

import warnings
import time
import os
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

# Importa solo getMatchData da main.py (createEventsDF e' ridefinita qui con il fix)
# Ensure project root is importable so sibling package `env` can be found
import sys
from pathlib import Path

# Add the repository root (parent of this folder) to sys.path when running
# the script from this subfolder so `from env.main import ...` works.
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# If the project provides `golf_tracker_app` (contains db_manager/gps_tracker),
# alias those modules to `env.*` so `env.main` can import them transparently.
import importlib
try:
    mod = importlib.import_module("golf_tracker_app.db_manager")
    sys.modules.setdefault("env.db_manager", mod)
except ModuleNotFoundError:
    pass

try:
    mod = importlib.import_module("golf_tracker_app.gps_tracker")
    sys.modules.setdefault("env.gps_tracker", mod)
except ModuleNotFoundError:
    pass

# If this scraping folder contains its own `main.py` with scraping helpers,
# load it and expose it as `env.main` so existing imports work unchanged.
from importlib import util as _util
from types import ModuleType as _ModuleType
scrape_main_path = Path(__file__).resolve().parent / "main.py"
if scrape_main_path.exists():
    spec = _util.spec_from_file_location("env.main", str(scrape_main_path))
    if spec and spec.loader:
        module = _util.module_from_spec(spec)
        sys.modules.setdefault("env", _ModuleType("env"))
        sys.modules["env.main"] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            # if loading fails, remove the injected module to avoid partial state
            sys.modules.pop("env.main", None)

from env.main import getMatchData, configura_firefox_scraper


# ──────────────────────────────────────────────
#  INSERISCI QUI I TUOI URL DI PARTITE
# ──────────────────────────────────────────────
MATCH_URLS = [
    "https://it.whoscored.com/matches/1934474/live/inghilterra-women-s-super-league-2025-2026-tottenham-hotspur-women-london-city-lionesses",
    # aggiungi altri URL qui...
]

# ──────────────────────────────────────────────
#  CONFIGURAZIONE
# ──────────────────────────────────────────────
SLEEP_BETWEEN_REQUESTS = 7   # secondi tra una richiesta e l'altra (evita il ban)
OUTPUT_FILE = "events.csv"   # nome del file CSV di output
MINIMIZE_WINDOW = True        # True = finestra Firefox minimizzata
HEADLESS = False             # True = esecuzione senza finestra browser


# ──────────────────────────────────────────────
#  FIX: createEventsDF con patch per playerId
# ──────────────────────────────────────────────
def createEventsDF(data):
    events = data['events']
    for event in events:
        event.update({
            'matchId':   data['matchId'],
            'startDate': data['startDate'],
            'startTime': data['startTime'],
            'score':     data['score'],
            'ftScore':   data['ftScore'],
            'htScore':   data['htScore'],
            'etScore':   data['etScore'],
            'venueName': data['venueName'],
            'maxMinute': data['maxMinute'],
        })
    events_df = pd.DataFrame(events)

    events_df['period']      = pd.json_normalize(events_df['period'])['displayName']
    events_df['type']        = pd.json_normalize(events_df['type'])['displayName']
    events_df['outcomeType'] = pd.json_normalize(events_df['outcomeType'])['displayName']

    try:
        x = events_df['cardType'].fillna({i: {} for i in events_df.index})
        events_df['cardType'] = pd.json_normalize(x)['displayName'].fillna(False)
    except KeyError:
        events_df['cardType'] = False

    eventTypeDict = data['matchCentreEventTypeJson']
    events_df['satisfiedEventsTypes'] = events_df['satisfiedEventsTypes'].apply(
        lambda x: [list(eventTypeDict.keys())[list(eventTypeDict.values()).index(e)] for e in x]
    )

    try:
        for i in events_df.index:
            row = events_df.loc[i, 'qualifiers'].copy()
            if len(row) != 0:
                for irow in range(len(row)):
                    row[irow]['type'] = row[irow]['type']['displayName']
    except TypeError:
        pass

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        if 'isShot' in events_df.columns:
            events_df['isShot'] = events_df['isShot'].fillna(False).astype(bool)
        else:
            events_df['isShot'] = False

        if 'isGoal' in events_df.columns:
            events_df['isGoal'] = events_df['isGoal'].fillna(False).astype(bool)
        else:
            events_df['isGoal'] = False

    # ── FIX playerId ──────────────────────────────────────────────────────────
    # WhoScored ora restituisce playerId gia' come StringArray invece di float64.
    # Il codice originale faceva .astype(int) che fallisce: fix -> cast diretto a str.
    if 'playerId' in events_df.columns:
        player_ids = events_df['playerId'].astype('string')
        player_ids = player_ids.str.strip().str.replace(r'\.0$', '', regex=True)
        player_ids = player_ids.mask(player_ids.isin(['', 'nan', 'None', '<NA>']))
        events_df['playerId'] = player_ids
    # ─────────────────────────────────────────────────────────────────────────

    # normalizza anche le chiavi del dizionario a stringa
    player_id_name = {str(k): v for k, v in data['playerIdNameDictionary'].items()}
    player_name_col = events_df['playerId'].map(player_id_name)
    events_df.insert(loc=events_df.columns.get_loc("playerId") + 1,
                     column='playerName', value=player_name_col)

    # FIX: teamId ora arriva come StringArray, normalizziamo tutto a str
    team_ids = events_df['teamId'].astype('string')
    team_ids = team_ids.str.strip().str.replace(r'\.0$', '', regex=True)
    team_ids = team_ids.mask(team_ids.isin(['', 'nan', 'None', '<NA>']))
    events_df['teamId'] = team_ids
    h_a_col = events_df['teamId'].map({str(data['home']['teamId']): 'h', str(data['away']['teamId']): 'a'})
    events_df.insert(loc=events_df.columns.get_loc("teamId") + 1, column='h_a', value=h_a_col)

    events_df['shotBodyType'] = pd.Series(pd.NA, index=events_df.index, dtype='string')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot == True].index:
            for j in events_df.loc[events_df.isShot == True, 'qualifiers'].loc[i]:
                if j['type'] in ('RightFoot', 'LeftFoot', 'Head', 'OtherBodyPart'):
                    events_df.loc[i, 'shotBodyType'] = j['type']

    events_df['situation'] = pd.Series(pd.NA, index=events_df.index, dtype='string')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot == True].index:
            for j in events_df.loc[events_df.isShot == True, 'qualifiers'].loc[i]:
                if j['type'] in ('FromCorner', 'SetPiece', 'DirectFreekick'):
                    events_df.loc[i, 'situation'] = j['type']
                if j['type'] == 'RegularPlay':
                    events_df.loc[i, 'situation'] = 'OpenPlay'

    event_types = list(data['matchCentreEventTypeJson'].keys())
    event_type_cols = pd.DataFrame({
        et: pd.Series([et in row for row in events_df['satisfiedEventsTypes']])
        for et in event_types
    })
    events_df = pd.concat([events_df, event_type_cols], axis=1)

    return events_df


def build_driver():
    """
    Crea un WebDriver senza dipendere dal download automatico di Selenium Manager.

    Variabili ambiente supportate:
    - BROWSER=firefox|chrome
    - FIREFOX_BINARY / GECKODRIVER_PATH
    - CHROME_BINARY / CHROMEDRIVER_PATH
    """
    browser = os.getenv("BROWSER", "firefox").strip().lower()
    attempted = []

    def _build_firefox():
        options = FirefoxOptions()
        configura_firefox_scraper(options)
        if HEADLESS:
            options.add_argument("-headless")

        firefox_binary = os.getenv("FIREFOX_BINARY")
        if firefox_binary:
            options.binary_location = firefox_binary

        geckodriver_path = os.getenv("GECKODRIVER_PATH")
        if geckodriver_path:
            service = FirefoxService(executable_path=geckodriver_path)
            return webdriver.Firefox(service=service, options=options)

        return webdriver.Firefox(options=options)

    def _build_chrome():
        options = ChromeOptions()
        if HEADLESS:
            options.add_argument("--headless=new")

        chrome_binary = os.getenv("CHROME_BINARY")
        if chrome_binary:
            options.binary_location = chrome_binary

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if chromedriver_path:
            service = ChromeService(executable_path=chromedriver_path)
            return webdriver.Chrome(service=service, options=options)

        return webdriver.Chrome(options=options)

    builders = []
    if browser == "chrome":
        builders = [("chrome", _build_chrome), ("firefox", _build_firefox)]
    else:
        builders = [("firefox", _build_firefox), ("chrome", _build_chrome)]

    for name, builder in builders:
        try:
            return builder()
        except (NoSuchDriverException, WebDriverException) as exc:
            attempted.append(f"{name}: {exc}")

    attempted_text = "\n".join(f"- {item}" for item in attempted)
    raise RuntimeError(
        "Impossibile avviare un browser Selenium.\n"
        "Installa un browser con relativo driver locale, oppure imposta le variabili "
        "d'ambiente supportate: BROWSER, FIREFOX_BINARY, GECKODRIVER_PATH, "
        "CHROME_BINARY, CHROMEDRIVER_PATH.\n"
        f"Tentativi eseguiti:\n{attempted_text}"
    )


# ──────────────────────────────────────────────
#  FUNZIONE PRINCIPALE
# ──────────────────────────────────────────────
def scrape_matches(urls):
    """
    Dato un elenco di URL di partite WhoScored,
    restituisce un unico DataFrame con tutti gli eventi.
    """
    driver = build_driver()
    if MINIMIZE_WINDOW:
        driver.minimize_window()

    all_events = []
    failed_urls = []

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Scraping: {url}")
        try:
            if i > 1:
                time.sleep(SLEEP_BETWEEN_REQUESTS)

            match_data = getMatchData(driver, url, display=True, close_window=False)
            events_df = createEventsDF(match_data)
            all_events.append(events_df)
            print(f"  ok  {len(events_df)} eventi trovati")

        except Exception as e:
            print(f"  ERRORE su {url}: {e}")
            failed_urls.append(url)

    driver.quit()

    if not all_events:
        print("Nessun dato raccolto.")
        return pd.DataFrame()

    final_df = pd.concat(all_events, ignore_index=True)
    print(f"\nTotale eventi: {len(final_df)} da {len(all_events)} partite")

    if failed_urls:
        print(f"\nURL falliti ({len(failed_urls)}):")
        for url in failed_urls:
            print(f"  - {url}")

    return final_df


if __name__ == "__main__":
    df = scrape_matches(MATCH_URLS)

    if not df.empty:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSalvato in '{OUTPUT_FILE}'")
        print(df.head())
