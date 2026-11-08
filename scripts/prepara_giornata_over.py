"""Prepara un'analisi giornaliera dai forecast già pubblicati, senza nuove quote."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acquisition import sisal as S
from scripts.raccogli_quote_sisal import ROOT, current_predictions
from sot import config, over_paper as OP


def build(day):
    clock = OP.utc_now()
    rows = [r for r in current_predictions(ROOT) if r['match_date'] == day
            and S.timestamp(r['published_at']) <= S.timestamp(clock)
            and r['training_through'] < day and 0 < r['p'] < 1]
    if not rows:
        raise ValueError('Nessuna previsione anteriore disponibile per questa data')
    sources = []
    # Public links actually observed during the previous browser test.
    for file in sorted((config.ROOT / 'reports').glob('sisal_test_1909_*/status.json')):
        for discovery in json.loads(file.read_text(encoding='utf-8')).get('discovery', []):
            for link in discovery.get('links', []):
                if S.public_url(link.get('url')):
                    sources.append({**link, 'league': discovery['league'],
                                    'evidence': str(file.relative_to(config.ROOT))})
    matches = []
    for league, match_id in dict.fromkeys((r['league'], r['match_id']) for r in rows):
        selections = [r for r in rows if (r['league'], r['match_id']) == (league, match_id)]
        first = selections[0]
        urls = {}
        for link in sources:
            if link['league'] != league:
                continue
            parts = [S.team_key(league, p.strip()) for p in link['text'].splitlines() if p.strip()]
            if (len(parts) == 2 and parts == [S.team_key(league, first['home']), S.team_key(league, first['away'])]):
                urls[link['url']] = link['evidence']
        source_url = next(iter(urls)) if len(urls) == 1 else None
        matches.append({**{k: first[k] for k in ('league', 'match_id', 'home', 'away', 'match_date')},
                        'source_url': source_url, 'source_evidence': urls.get(source_url),
                        'kickoff': None, 'quote_status': 'da_aggiornare',
                        'regime': first['regime'], 'selections': selections})
    plan = {'schema': 'over-day-plan', 'version': 1, 'day': day, 'generated_at': clock,
            'names': S.LEAGUES, 'matches': matches, 'candidates': rows,
            'published_at': sorted({r['published_at'] for r in rows}),
            'training_through': sorted({r['training_through'] for r in rows}),
            'offered_odds': None, 'economic_decision': 'nessuna_giocata',
            'note': 'Probabilità del modello già pubblicate; nessuna nuova quota acquisita.'}
    runs = OP.load_records(ROOT / 'sisal/runs')
    plan['sisal'] = {'last_run': max(runs, key=lambda r: r['finished_at']) if runs else None,
                     'observations': OP.load_records(ROOT / 'sisal/observations')}
    stem = config.ROOT / 'reports' / ('preparazione_over_' + day)
    stem.with_suffix('.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    with stem.with_suffix('.csv').open('w', newline='', encoding='utf-8-sig') as file:
        fields = ['match_date', 'league', 'home', 'away', 'target', 'scope', 'side', 'line', 'p',
                  'fair_odds', 'published_at', 'training_through', 'selection_id', 'source_url']
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        urls = {(m['league'], m['match_id']): m['source_url'] for m in matches}
        for r in rows:
            writer.writerow({**r, 'fair_odds': 1 / r['p'], 'source_url': urls[(r['league'], r['match_id'])]})
    template = (config.ROOT / 'scripts/templates/day_plan.html').read_text(encoding='utf-8')
    engine = (config.ROOT / 'scripts/templates/suggestion_engine.js').read_text(encoding='utf-8')
    html = template.replace('__PLAN_DATA__', json.dumps(plan, ensure_ascii=False).replace('<', '\\u003c'))
    html = html.replace('__SUGGESTION_ENGINE__', engine)
    stem.with_suffix('.html').write_text(html, encoding='utf-8')
    return stem.with_suffix('.html'), plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True, help='YYYY-MM-DD')
    args = parser.parse_args()
    from datetime import date
    date.fromisoformat(args.date)
    output, plan = build(args.date)
    print(output)
    print(len(plan['matches']), 'partite,', len(plan['candidates']), 'linee,',
          sum(bool(m['source_url']) for m in plan['matches']), 'link Sisal verificati nel palinsesto')
