"""Opt-in Chrome checks of the observed Sisal structure, using synthetic prices.

Set SISAL_TEST_CHROME and SISAL_TEST_DRIVER to local executable paths.
No network or bookmaker page is used by these tests.
"""
import os

import pytest

from acquisition.sisal import DOM_SCRIPT, prices


@pytest.fixture(scope='module')
def browser():
    executable = os.environ.get('SISAL_TEST_CHROME')
    driver = os.environ.get('SISAL_TEST_DRIVER')
    if not executable or not driver:
        pytest.skip('Local Chrome and driver paths required')
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    options = webdriver.ChromeOptions()
    options.binary_location = executable
    options.add_argument('--headless=new')
    options.add_argument('--no-first-run')
    b = webdriver.Chrome(service=Service(driver), options=options)
    yield b
    b.quit()


def page(browser, tmp_path, start='2026-09-20T12:30:00.000', shown='20/09 12:30', away='Napoli'):
    # Relevant class prefixes and nesting observed on Sisal; names/prices are fixtures.
    file = tmp_path / 'fixture.html'
    file.write_text('''<!doctype html><meta charset="utf-8">
    <p class="PrematchSubheader_firstCompetitor__test PrematchSubheader_competitorName__test">Fiorentina</p>
    <p class="PrematchSubheader_competitorName__test">Napoli</p>
    <div class="PrematchSubheader_dateContainer__test">''' + shown + '''</div>
    <div class="template_mg-market-attribute__test"><div>U/O 10.5 TIRI IN PORTA</div>
      <div><button data-qa="esito_fixture_under" disabled><div>UNDER</div></button>
      <button data-qa="esito_fixture_over"><div>OVER</div><span>2.80</span></button></div></div>
    <div class="template_mg-market-attribute__test"><div>SQUADRA 1: U/O 2.5 TIRI IN PORTA</div>
      <button data-qa="esito_fixture_home"><div>OVER</div><span>1.18</span></button></div>
    <div class="template_mg-market-attribute__test"><div>SQUADRA 2: U/O 9.5 TIRI TOTALI</div>
      <button data-qa="esito_fixture_away"><div>OVER</div><span>1.40</span></button></div>
    <div class="template_mg-market-attribute__test"><div>SQUADRA 1: U/O 2.5 TIRI IN PORTA 1 TEMPO</div>
      <button data-qa="esito_fixture_half"><div>OVER</div><span>3.40</span></button></div>
    ''', encoding='utf-8')
    browser.get(file.as_uri())
    browser.execute_script('''const x=arguments[0];x.url=location.origin+location.pathname;
      const s=document.createElement('script');s.type='application/ld+json';
      s.textContent=JSON.stringify(x);document.head.append(s);''', {
        'type': 'SportsEvent', 'name': 'Fiorentina - ' + away, 'startDate': start,
        'competitor': [{'name': 'Fiorentina'}, {'name': away}]})
    return browser.execute_script(DOM_SCRIPT)


def test_observed_cards_and_metadata(browser, tmp_path):
    capture = page(browser, tmp_path)
    assert capture['events'] == [{'home': 'Fiorentina', 'away': 'Napoli', 'kickoff': '2026-09-20T10:30:00.000Z'}]
    assert len(capture['blocks']) == 3
    rows = [q for b in capture['blocks'] for q in prices(b)]
    assert [(q['side'], q['line'], q['over_odds']) for q in rows] == [
        ('total', 10.5, 2.8), ('home', 2.5, 1.18), ('away', 9.5, 1.4)]
    assert rows[0]['under_odds'] is None


@pytest.mark.parametrize('start,shown,expected', [
    ('2027-01-20T12:30:00.000', '20/01 12:30', '2027-01-20T11:30:00.000Z'),
    ('2026-10-25T02:30:00.000', '25/10 02:30', None),  # Ambiguous DST hour.
    ('2027-03-28T02:30:00.000', '28/03 02:30', None),  # Nonexistent DST hour.
    ('2026-09-20T12:30:00.000', '21/09 12:30', None),  # Stale/mismatched metadata.
])
def test_local_time_and_visible_date(browser, tmp_path, start, shown, expected):
    capture = page(browser, tmp_path, start, shown)
    assert [e['kickoff'] for e in capture['events']] == ([expected] if expected else [])


def test_metadata_for_another_match_is_rejected(browser, tmp_path):
    assert page(browser, tmp_path, away='Atalanta')['events'] == []


def test_desktop_labels_with_bet_limits_keep_all_team_markets(browser, tmp_path):
    page(browser, tmp_path)
    browser.execute_script('''for(const card of document.querySelectorAll('[class*="template_mg-market-attribute__"]')){
      const label=card.firstElementChild, desc=document.createElement('div');
      desc.className='mg-market-attribute-desc';label.replaceWith(desc);desc.append(label);
      const limits=document.createElement('div');limits.textContent='Min - max: 1 - 30';desc.append(limits);
    }''')
    capture = browser.execute_script(DOM_SCRIPT)
    rows = [q for b in capture['blocks'] for q in prices(b)]
    assert len(capture['blocks']) == 3  # Excludes the first-half card.
    assert [(q['side'], q['line'], q['over_odds']) for q in rows] == [
        ('total', 10.5, 2.8), ('home', 2.5, 1.18), ('away', 9.5, 1.4)]
    assert capture['blocks'][0]['outcomes'][0]['disabled'] is True


def test_metadata_trailing_whitespace_is_harmless(browser, tmp_path):
    page(browser, tmp_path)
    browser.execute_script('''const s=document.querySelector('script[type="application/ld+json"]');
      const x=JSON.parse(s.textContent);x.name+=' ';x.competitor[1].name+=' ';
      s.textContent=JSON.stringify(x);''')
    assert browser.execute_script(DOM_SCRIPT)['events'][0]['away'] == 'Napoli'


def test_display_title_is_not_used_as_ordered_team_identity(browser, tmp_path):
    page(browser, tmp_path)
    browser.execute_script('''const s=document.querySelector('script[type="application/ld+json"]');
      const x=JSON.parse(s.textContent);x.name='Alternate display title';
      s.textContent=JSON.stringify(x);''')
    assert browser.execute_script(DOM_SCRIPT)['events'][0]['home'] == 'Fiorentina'
    browser.execute_script('''const s=document.querySelector('script[type="application/ld+json"]');
      const x=JSON.parse(s.textContent);x.competitor.reverse();s.textContent=JSON.stringify(x);''')
    assert browser.execute_script(DOM_SCRIPT)['events'] == []
