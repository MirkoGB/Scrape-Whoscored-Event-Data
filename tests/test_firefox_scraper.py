"""Regressione: ogni ingresso dello scraper deve impedire l'avvio al login.

Intercetta il costruttore Selenium: nessun browser o richiesta di rete nei test.
"""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'acquisition' / 'whoscored'))
import main as scraper_main
import scrape_matches
import scrape_season


@pytest.mark.parametrize('entry', ['legacy', 'matches', 'season', 'explicit_driver', 'fallback'])
def test_firefox_cannot_register_windows_autostart(monkeypatch, entry):
    monkeypatch.setenv('BROWSER', 'chrome' if entry == 'fallback' else 'firefox')
    monkeypatch.setenv('WHOSCORED_BROWSER', 'firefox')
    monkeypatch.delenv('FIREFOX_BINARY', raising=False)
    monkeypatch.delenv('GECKODRIVER_PATH', raising=False)
    if entry == 'explicit_driver':
        monkeypatch.setenv('GECKODRIVER_PATH', 'geckodriver-test.exe')
        monkeypatch.setenv('FIREFOX_BINARY', 'firefox-test.exe')

    firefox = Mock()
    chrome = Mock(side_effect=WebDriverException('Chrome non disponibile'))
    monkeypatch.setattr(scrape_matches.webdriver, 'Firefox', firefox)
    monkeypatch.setattr(scrape_matches.webdriver, 'Chrome', chrome)
    if entry == 'legacy':
        result = scraper_main.nuovo_driver()
    elif entry == 'season':
        result = scrape_season.build_driver()
    else:
        result = scrape_matches.build_driver()

    assert result is firefox.return_value
    firefox.assert_called_once()
    prefs = firefox.call_args.kwargs['options'].preferences
    assert prefs['browser.startup.windowsLaunchOnLogin.enabled'] is False
    assert prefs['app.update.background.scheduling.enabled'] is False
    if entry == 'fallback':
        chrome.assert_called_once()
