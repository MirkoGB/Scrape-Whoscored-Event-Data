"""Fixture sintetiche esplicite: non attestano il DOM live o quote reali Sisal."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from acquisition import sisal as S
from scripts.raccogli_quote_sisal import collect
from scripts.raccogli_quote_sisal import import_extension
from sot import over_paper as OP


def sample():
    now = datetime.now(timezone.utc)
    kickoff = now + timedelta(days=2)
    p = dict(league='ITA-serie-a', match_id='42', match_date=str(kickoff.astimezone(S.ROME).date()),
             home='Juventus', away='Atalanta', selection_id='fixture|42|shots|home|8.5',
             target='shots', scope='team', side='home', line=8.5, p=.8,
             published_at=(now - timedelta(days=1)).isoformat(), training_through=str((now - timedelta(days=2)).date()))
    c = dict(source_url=S.BASE_URL + '/fixture-test', observed_at=now.isoformat(), blocked=False,
             events=[dict(home='Juventus', away='Atalanta', kickoff=kickoff.isoformat())],
             blocks=[dict(label='U/O Tiri Totali Casa', outcomes=[
                 dict(text='Under 8,5 2,10', disabled=False), dict(text='Over 8,5 1,80', disabled=False)])])
    return p, c


@pytest.mark.parametrize('label,target,side', [
    ('U/O TIRI TOTALI CASA', 'shots', 'home'), ('U/O 8,5 TIRI TOTALI OSPITE', 'shots', 'away'),
    ('U/O TIRI IN PORTA SQUADRA CASA', 'sot', 'home'), ('Under/Over Tiri In Porta', 'sot', 'total'),
    ('U/O TIRI TOTALI', 'shots', 'total'), ('U/O TIRI IN PORTA SQUADRA 2', 'sot', 'away'),
    ('SQUADRA 1: U/O 2.5 TIRI IN PORTA', 'sot', 'home'),
    ('SQUADRA 2: U/O 12.5 TIRI TOTALI', 'shots', 'away')])
def test_exact_known_markets(label, target, side):
    m = S.market(label)
    assert m['target'] == target and m['side'] == side


@pytest.mark.parametrize('label', ['U/O TIRI TOTALI CASA INCL. TS', 'U/O TIRI TOTALI CASA 1 TEMPO',
    'U/O TIRI IN PORTA GIOCATORE X', 'U/O CORNER', 'U/O GOAL', 'TIRI TOTALI', 'U/O TIRI TOTALI DA FUORI AREA',
    'SQUADRA 1: U/O 2.5 TIRI IN PORTA 1 TEMPO', 'SQUADRA 2: U/O 12.5 TIRI TOTALI INCL. TS'])
def test_unsupported_periods_players_and_other_stats_are_not_guessed(label):
    assert S.market(label) is None


def test_explicit_line_and_decimal_price_only():
    p, c = sample()
    rows, excluded = S.match_capture(c, [p], OP.utc_now())
    assert not excluded
    assert rows[0]['over_odds'] == 1.8 and rows[0]['under_odds'] == 2.1
    assert rows[0]['economic_eligible'] is False
    assert rows[0]['settlement_rule'] != 'opta_90min_halfline'
    block = dict(label='U/O 8,5 TIRI TOTALI CASA', outcomes=[dict(text='Over 1,80', disabled=False)])
    assert S.prices(block)[0]['line'] == 8.5
    block['label'] = 'U/O TIRI TOTALI CASA'
    assert S.prices(block) == []
    for text in ['Over 8.5 180', 'Over 8.5 1.8 2.1', 'Over 8 1.80', 'Over 8.5 1.0']:
        block['outcomes'] = [dict(text=text, disabled=False)]
        assert S.prices(block) == []


def test_suspended_or_conflicting_prices_are_excluded():
    _, c = sample()
    b = c['blocks'][0]
    b['outcomes'][1]['disabled'] = True
    assert S.prices(b) == []
    b['outcomes'][1]['disabled'] = False
    b['outcomes'].append(dict(text='Over 8,5 1,90', disabled=False))
    assert S.prices(b) == []


def test_sisal_stats_match_card_with_closed_under():
    b = dict(label='SQUADRA 1: U/O 2.5 TIRI IN PORTA', outcomes=[
        dict(text='UNDER', disabled=True), dict(text='OVER 1.18', disabled=False)])
    rows = S.prices(b)
    assert len(rows) == 1
    assert rows[0]['side'] == 'home' and rows[0]['line'] == 2.5
    assert rows[0]['over_odds'] == 1.18 and rows[0]['under_odds'] is None


def test_price_on_different_line_has_no_probability_attached():
    p, c = sample()
    c['blocks'][0]['outcomes'][1]['text'] = 'Over 9,5 1,80'
    rows, excluded = S.match_capture(c, [p], OP.utc_now())
    assert not rows and excluded[0]['line'] == 9.5


def test_identity_date_home_away_and_unambiguous_kickoff():
    p, c = sample()
    wrong = deepcopy(c)
    wrong['events'][0].update(home='Atalanta', away='Juventus')
    with pytest.raises(ValueError, match='univoco'):
        S.match_capture(wrong, [p], OP.utc_now())
    wrong = deepcopy(c)
    wrong['events'][0]['kickoff'] = (S.timestamp(c['events'][0]['kickoff']) + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match='univoco'):
        S.match_capture(wrong, [p], OP.utc_now())
    c['events'].append({**c['events'][0], 'kickoff': (S.timestamp(c['events'][0]['kickoff']) + timedelta(minutes=1)).isoformat()})
    with pytest.raises(ValueError, match='univoco'):
        S.match_capture(c, [p], OP.utc_now())


@pytest.mark.parametrize('league,source,canonical', [
    (league, alias, name) for league, aliases in S.TEAM_ALIASES.items()
    for alias, name in aliases.items()])
def test_explicit_sisal_team_aliases(league, source, canonical):
    assert S.team_key(league, source) == S.team_key(league, canonical)
    assert S.team_key('OTHER', source) == S.normal(source)


def test_aliases_preserve_identity_date_and_home_away_checks():
    p, c = sample()
    p.update(league='GER-bundesliga', home='Hamburger SV', away='FC Koln')
    c['events'][0].update(home='Amburgo', away='Colonia')
    assert S.match_capture(c, [p], OP.utc_now())[0]
    c['events'][0].update(home='Colonia', away='Amburgo')
    with pytest.raises(ValueError, match='univoco'):
        S.match_capture(c, [p], OP.utc_now())
    c['events'][0].update(home='Amburgo II', away='Colonia')
    with pytest.raises(ValueError, match='univoco'):
        S.match_capture(c, [p], OP.utc_now())


def test_no_future_forecasts_stale_odds_or_started_matches():
    p, c = sample()
    p['published_at'] = c['events'][0]['kickoff']
    assert S.match_capture(c, [p], OP.utc_now())[0] == []
    p, c = sample()
    later = (S.timestamp(c['observed_at']) + timedelta(minutes=61)).isoformat()
    with pytest.raises(ValueError, match='60 minuti'):
        S.match_capture(c, [p], later)
    with pytest.raises(ValueError, match='futura'):
        S.match_capture(c, [p], p['published_at'])
    c['observed_at'] = c['events'][0]['kickoff']
    with pytest.raises(ValueError, match='iniziata'):
        S.match_capture(c, [p], c['observed_at'])


def test_url_filter_and_link_discovery_are_restricted():
    p, _ = sample()
    assert S.public_url('https://www.sisal.it/scommesse-matchpoint')
    assert not S.public_url('https://www.sisal.it/scommesse-matchpoint-fake')
    for url in ['https://evil.test/scommesse-matchpoint', 'https://www.sisal.it.evil.test/scommesse-matchpoint',
                'https://areaprivata.sisal.it/login', 'https://www.sisal.it/scommesse-matchpoint/blog/test',
                'file:///x', 'javascript:alert(1)', 'https://user:password@www.sisal.it/scommesse-matchpoint']:
        assert not S.public_url(url)
    page = {'links': [{'url': S.BASE_URL + '/partita', 'text': 'Juventus - Atalanta'},
                      {'url': S.BASE_URL + '/lega', 'text': 'Serie A'},
                      {'url': 'https://evil.test', 'text': 'Juventus - Atalanta'}]}
    assert S.discovered_links(page, [p]) == [S.BASE_URL + '/partita']
    assert S.discovered_links(page, [p], league_pages=True) == [S.BASE_URL + '/lega']


def test_collect_auto_discovers_saves_evidence_and_keeps_economic_registry_separate(tmp_path):
    p, capture = sample()
    event_url = capture['source_url']
    class Browser:
        closed = False
        def read(self, url, evidence):
            if url == S.BASE_URL:
                return {'source_url': url, 'observed_at': OP.utc_now(), 'links': [{'url': event_url, 'text': 'Juventus - Atalanta'}]}
            return deepcopy(capture)
        def close(self): self.closed = True
    b = Browser()
    result = collect(tmp_path, [p], lambda: b, delay=0)
    assert b.closed
    assert result['status'] == 'collected' and len(result['observations']) == 1
    record = OP.load_records(tmp_path / 'sisal/observations')[0]
    assert (tmp_path / record['evidence_file']).exists()
    assert len(OP.load_records(tmp_path / 'sisal/runs')) == 1
    assert OP.load_records(tmp_path / 'quotes') == []
    assert OP.load_records(tmp_path / 'decisions') == []
    assert record['recorded_at'] >= record['observed_at']


def test_failed_access_is_not_reported_as_no_odds_and_is_journaled(tmp_path):
    p, _ = sample()
    class Browser:
        def read(self, *args): raise TimeoutError('synthetic timeout')
        def close(self): pass
    run = collect(tmp_path, [p], Browser, delay=0)
    assert run['status'] == 'access_failed'
    assert run['observations'] == []
    assert 'TimeoutError' in run['pages'][0]['reason']
    assert len(OP.load_records(tmp_path / 'sisal/runs')) == 1


def test_no_future_catalogue_does_not_open_browser(tmp_path):
    def forbidden(): raise AssertionError('Browser must not start')
    assert collect(tmp_path, [], forbidden)['status'] == 'no_future_predictions'


def test_extension_import_keeps_original_capture_time_and_uses_same_match_checks(tmp_path):
    import json
    p, c = sample()
    c.update(transport='chrome_extension', cookies='must not be retained')
    bundle = dict(schema='sisal-chrome-captures', version=1, exported_at=OP.utc_now(), captures=[c])
    path = tmp_path / 'export.json'
    path.write_text(json.dumps(bundle), encoding='utf-8')
    root = tmp_path / 'registry'
    run = import_extension(root, [p], path)
    assert run['status'] == 'collected' and run['transport'] == 'chrome_extension'
    row = OP.load_records(root / 'sisal/observations')[0]
    assert row['observed_at'] == S.timestamp(c['observed_at']).isoformat()
    assert row['recorded_at'] >= row['observed_at']
    proof = json.loads((root / row['evidence_file']).read_text(encoding='utf-8'))
    assert 'cookies' not in proof
    assert OP.load_records(root / 'quotes') == []


def test_extension_import_never_refreshes_stale_odds(tmp_path):
    import json
    p, c = sample()
    c.update(transport='chrome_extension', observed_at=(datetime.now(timezone.utc) - timedelta(minutes=61)).isoformat())
    file = tmp_path / 'export.json'
    bundle = dict(schema='sisal-chrome-captures', version=1, exported_at=OP.utc_now(), captures=[c])
    file.write_text(json.dumps(bundle), encoding='utf-8')
    run = import_extension(tmp_path / 'registry', [p], file)
    assert not run['observations']
    assert '60 minuti' in run['pages'][0]['reason']


def test_extension_import_rejects_foreign_sources_and_wrong_schema(tmp_path):
    import json
    p, c = sample()
    c.update(transport='chrome_extension', source_url='https://evil.test/page')
    file = tmp_path / 'export.json'
    bundle = dict(schema='sisal-chrome-captures', version=1, exported_at=OP.utc_now(), captures=[c])
    file.write_text(json.dumps(bundle), encoding='utf-8')
    with pytest.raises(ValueError, match='Pagina'):
        import_extension(tmp_path / 'registry', [p], file)
    bundle['schema'] = 'other'
    file.write_text(json.dumps(bundle), encoding='utf-8')
    with pytest.raises(ValueError, match='Formato'):
        import_extension(tmp_path / 'registry', [p], file)
