"""Acquisisce automaticamente le quote pubbliche riconoscibili e aggiorna l'HTML.

Senza --event-url cerca le partite del catalogo attraverso i link pubblici del
calcio e dei cinque campionati. Non usa API indovinate o endpoint di gioco.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acquisition import sisal as S
from sot import config, over_paper as OP

ROOT = config.ROOT / 'data/external/paper_over'


def current_predictions(root):
    records = OP.load_records(root / 'predictions')
    return max(records, key=lambda r: r['published_at'])['selections'] if records else []


def collect(root, candidates, browser_factory, *, event_urls=(), max_events=50, delay=1.0, transport='selenium', input_sha256=None):
    """Append-only run journal, including failures and unavailable markets."""
    started = OP.utc_now()
    today = str(S.timestamp(started).astimezone(S.ROME).date())
    candidates = [r for r in candidates if r['match_date'] >= today and S.timestamp(r['published_at']) <= S.timestamp(started)]
    ident = 'sisal_' + uuid.uuid4().hex[:16]
    run = {'id': ident, 'started_at': started, 'bookmaker': 'Sisal', 'status': 'running',
           'transport': transport, 'input_sha256': input_sha256,
           'catalogue_matches': len({(r['league'], r['match_id']) for r in candidates}),
           'pages': [], 'observations': [], 'excluded': [], 'discovered_events': 0,
           'live_parser_verified': True,
           'parser_verification': {'date': '2026-09-19', 'format': 'STATS MATCH',
               'url': 'https://www.sisal.it/scommesse-matchpoint/evento/calcio/serie-a/fiorentina-napoli'},
           'note': 'Formato STATS MATCH verificato su Fiorentina–Napoli; copertura degli altri formati non attestata.'}
    browser = None

    def read(url):
        evidence = root / 'sisal/evidence' / ident / f'page_{len(run["pages"]):03d}'
        try:
            capture = browser.read(url, evidence)
            S.enrich_events(capture, candidates)
            evidence.mkdir(parents=True, exist_ok=True)
            file = evidence / 'page.json'
            OP.write_once(file, capture)
            proof = {'evidence_file': str(file.relative_to(root)),
                     'evidence_sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
            screenshot = evidence / 'page.png'
            if screenshot.is_file():
                proof.update(screenshot_file=str(screenshot.relative_to(root)),
                             screenshot_sha256=hashlib.sha256(screenshot.read_bytes()).hexdigest())
            run['pages'].append({'url': url, 'status': 'blocked' if capture.get('blocked') else 'read', **proof})
            if capture.get('blocked'):
                run['pages'][-1]['reason'] = capture.get('blocked_reason', 'Pagina non accessibile; vedi prova archiviata')
                return None
            return capture, proof
        except Exception as exc:
            run['pages'].append({'url': url, 'status': 'error', 'reason': type(exc).__name__ + ': ' + str(exc).split('\n')[0][:240]})
            return None

    try:
        if not candidates:
            run['status'] = 'no_future_predictions'
        else:
            if any(not S.public_url(u) for u in event_urls):
                raise ValueError('Gli URL devono essere pagine pubbliche Sisal del palinsesto')
            browser = browser_factory()
            urls = set(event_urls)
            if not urls:
                home = read(S.BASE_URL)
                if home:
                    urls.update(S.discovered_links(home[0], candidates))
                    for url in S.discovered_links(home[0], candidates, league_pages=True)[:5]:
                        time.sleep(delay)
                        page = read(url)
                        if page:
                            urls.update(S.discovered_links(page[0], candidates))
            run['discovered_events'] = len(urls)
            for url in sorted(urls)[:max_events]:
                time.sleep(delay)
                page = read(url)
                if not page:
                    continue
                capture, proof = page
                try:
                    matched, excluded = S.match_capture(capture, candidates, OP.utc_now())
                except ValueError as exc:
                    run['pages'][-1].update(status='unmatched', reason=str(exc))
                    continue
                run['excluded'].extend({'url': url, **r} for r in excluded)
                if not matched:
                    run['pages'][-1].update(status='no_matching_markets', reason='Nessuna quota Over leggibile e abbinabile alle linee previste')
                for row in matched:
                    recorded = OP.utc_now()
                    if S.timestamp(recorded) >= S.timestamp(row['kickoff']):
                        run['excluded'].append({'url': url, 'selection_id': row['selection_id'], 'reason': 'kickoff raggiunto durante la registrazione'})
                        continue
                    record = {**row, **proof, 'id': 'sisal_quote_' + uuid.uuid4().hex[:16],
                              'run_id': ident, 'recorded_at': recorded}
                    OP.save_record(root / 'sisal/observations', record)
                    run['observations'].append(record['id'])
            run['status'] = ('collected' if run['observations'] else
                             'access_failed' if run['pages'] and all(p['status'] in ('blocked', 'error') for p in run['pages']) else
                             'no_matching_markets' if urls else 'no_event_links')
    except Exception as exc:
        run.update(status='failed', error=type(exc).__name__ + ': ' + str(exc).split('\n')[0][:240])
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
    run['finished_at'] = OP.utc_now()
    return OP.save_record(root / 'sisal/runs', run)


def import_extension(root, candidates, file):
    """Importa letture del browser, senza rilevarle di nuovo o retrodatare il registro."""
    file = Path(file)
    if file.stat().st_size > 5_000_000:
        raise ValueError('Esportazione troppo grande (massimo 5 MB)')
    raw = file.read_bytes()
    bundle = json.loads(raw.decode('utf-8-sig'))
    if bundle.get('schema') != 'sisal-chrome-captures' or bundle.get('version') != 1:
        raise ValueError('Formato di esportazione Chrome non riconosciuto')
    exported = S.timestamp(bundle['exported_at'])
    if exported > S.timestamp(OP.utc_now()):
        raise ValueError('Esportazione con data futura')
    captures = bundle.get('captures')
    if not isinstance(captures, list) or not 1 <= len(captures) <= 50:
        raise ValueError('Richieste da 1 a 50 pagine esportate')
    pages = {}
    for capture in captures:
        url = capture.get('source_url')
        if not S.public_url(url) or capture.get('transport') != 'chrome_extension':
            raise ValueError('Pagina non proveniente dalla raccolta Sisal prevista')
        if S.timestamp(capture['observed_at']) > exported:
            raise ValueError('Rilevazione successiva all’esportazione')
        if url not in pages or S.timestamp(capture['observed_at']) > S.timestamp(pages[url]['observed_at']):
            # Only public market metadata is retained as evidence, never arbitrary extra fields.
            pages[url] = {k: capture[k] for k in ('source_url', 'observed_at', 'transport', 'events', 'headings', 'times', 'blocks', 'frame_hosts') if k in capture}

    class ExportedPages:
        def read(self, url, _evidence_dir):
            return pages[url]
        def close(self):
            pass

    return collect(root, candidates, ExportedPages, event_urls=list(pages), delay=0,
                   transport='chrome_extension', input_sha256=hashlib.sha256(raw).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--event-url', action='append', default=[], help='URL partita, ripetibile; altrimenti scoperta automatica')
    p.add_argument('--import-extension', type=Path, help='JSON esportato dall’estensione Chrome; nessun accesso alla rete')
    p.add_argument('--max-events', type=int, default=50)
    p.add_argument('--driver', help='Percorso chromedriver; altrimenti Selenium Manager')
    p.add_argument('--headed', action='store_true', help='Mostra Chrome durante la raccolta')
    p.add_argument('--timeout', type=int, default=25)
    args = p.parse_args()
    if not 1 <= args.max_events <= 100 or not 5 <= args.timeout <= 60:
        p.error('max-events: 1–100; timeout: 5–60 secondi')
    if args.import_extension and args.event_url:
        p.error('Usa import-extension oppure event-url')
    print('Raccolta Sisal: pagine pubbliche, nessun account o giocata.', flush=True)
    if args.import_extension:
        try:
            run = import_extension(ROOT, current_predictions(ROOT), args.import_extension)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            print('Importazione non riuscita:', str(exc))
            return 2
    else:
        run = collect(ROOT, current_predictions(ROOT),
                      lambda: S.PublicBrowser(args.driver, args.timeout, args.headed),
                      event_urls=args.event_url, max_events=args.max_events)
    from scripts.pagina_analisi_2627 import scrivi
    report = scrivi()
    print('Stato:', run['status'], '| pagine:', len(run['pages']), '| quote abbinate:', len(run['observations']))
    for page in run['pages']:
        if page.get('reason'):
            print(page['status'], page['url'], page['reason'])
    if run.get('error'):
        print(run['error'])
    print('Report:', report)
    return 0 if run['status'] == 'collected' else 2


if __name__ == '__main__':
    raise SystemExit(main())
