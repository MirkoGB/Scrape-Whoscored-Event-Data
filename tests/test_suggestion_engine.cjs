const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('../scripts/templates/suggestion_engine.js');
const now = new Date('2026-09-17T12:00:00Z');
const options = {now};
function row(id, p, extra = {}) {
  return {league: 'L', match_id: String(id), match_date: '2026-09-18', home: 'H' + id, away: 'A' + id,
    p, line: 8.5, target: 'shots', scope: 'team', side: 'home',
    selection_id: 'S' + id, published_at: '2026-09-16T12:00:00Z', training_through: '2026-09-15', ...extra};
}
test('finds the exact optimum even when greedy selection fails', () => {
  const rows = [row(1, .99, {home: 'A', away: 'B'}), row(2, .95, {home: 'A', away: 'C'}),
    row(3, .95, {home: 'B', away: 'D'}), row(4, .1)];
  const r = E.suggest(rows, 2, options);
  assert.deepEqual(r.legs.map(x => x.match_id), ['2', '3']);
  assert.equal(r.metrics.probability, .95 * .95);
});
test('exactly X events, all sizes 1 through 10, with no heuristic pool cap', () => {
  const rows = Array.from({length: 25}, (_, i) => row(i + 1, .99 - i * .01));
  for (let n = 1; n <= 10; n++) {
    const r = E.suggest(rows, n, options);
    assert.equal(r.legs.length, n);
    assert.ok(Math.abs(r.metrics.probability - rows.slice(0, n).reduce((p, r) => p * r.p, 1)) < 1e-14);
  }
  const crowded = rows.map((r, i) => i < 24 ? {...r, home: 'Common team'} : r);
  assert.equal(E.suggest(crowded, 2, options).legs[1].match_id, '25');
});
test('insufficient compatible events means no coupon, never silently fewer legs', () => {
  const rows = [row(1, .9, {home: 'A'}), row(2, .8, {away: 'A'}), row(3, .7, {home: 'A'})];
  const r = E.suggest(rows, 2, options);
  assert.equal(r.matches, 3);
  assert.equal(r.status, 'insufficient');
  assert.deepEqual(r.legs, []);
  assert.equal(r.metrics, null);
  assert.equal(E.suggest([], 1, options).status, 'insufficient');
});
test('keeps one market per game and excludes repeated teams across dates', () => {
  const rows = [row(1, .8), row(1, .95, {side: 'away', selection_id: 'away'}),
    row(2, .94, {home: 'h1 ', match_date: '2026-09-19'}), row(3, .7)];
  const r = E.suggest(rows, 2, options);
  assert.deepEqual(r.legs.map(x => x.selection_id), ['away', 'S3']);
});
test('latest forecast for the same market supersedes a higher old probability', () => {
  const old = row(1, .99), recent = row(1, .5, {selection_id: 'new', published_at: '2026-09-17T10:00:00Z'});
  for (const rows of [[old, recent, row(2, .8)], [recent, old, row(2, .8)]]) {
    assert.equal(E.suggest(rows, 1, options).legs[0].match_id, '2');
  }
});
test('excludes today, past, known results and forecasts not available at decision time', () => {
  const rows = [row(1, .99, {match_date: '2026-09-17'}), row(2, .98, {match_date: '2026-09-16'}),
    row(3, .97, {published_at: '2026-09-17T13:00:00Z'}), row(4, .96), row(5, .7)];
  const r = E.suggest(rows, 1, {...options, finished: [{league: 'L', match_id: 4}]});
  assert.equal(r.legs[0].match_id, '5');
  assert.equal(E.suggest(rows, 1, {now: new Date('2026-09-18T00:00:00Z')}).status, 'insufficient');
  assert.equal(E.romeDay(new Date('2026-09-17T22:30:00Z')), '2026-09-18');
});
test('rejects invalid probabilities, markets and leakage metadata', () => {
  const bad = [{p: NaN}, {p: .0}, {p: 1.01}, {p: '.9'}, {line: 8}, {line: -1.5},
    {scope: 'total', side: 'home'}, {target: 'goals'}, {training_through: '2026-09-18'},
    {published_at: '2026-09-16T12:00:00'}, {match_date: '2026-09-31'}, {home: ''}];
  const rows = bad.map((extra, i) => row(i + 1, .99, extra));
  assert.equal(E.prepare(rows, options).rows.length, 0);
  for (const size of [0, 11, 1.5, NaN]) assert.throws(() => E.suggest([], size, options), RangeError);
});
test('applies market, league and date filters before optimization', () => {
  const rows = [row(1, .99), row(2, .95, {league: 'OTHER'}),
    row(3, .9, {target: 'sot', scope: 'total', side: 'total', match_date: '2026-09-19'})];
  assert.equal(E.suggest(rows, 1, {...options, market: 'sot:total'}).legs[0].match_id, '3');
  assert.equal(E.suggest(rows, 1, {...options, league: 'OTHER'}).legs[0].match_id, '2');
  assert.equal(E.suggest(rows, 1, {...options, day: '2026-09-19'}).legs[0].match_id, '3');
  assert.equal(E.suggest(rows, 2, {...options, league: 'OTHER'}).status, 'insufficient');
});
test('probability, loss, fair price and sensitivity have distinct correct meanings', () => {
  const m = E.metrics([row(1, .8), row(2, .7)]);
  for (const [key, expected] of Object.entries({probability: .56, loss: .44, fairOdds: 1/.56, lower: .5, upper: .7, stress5: .75*.65})) {
    assert.ok(Math.abs(m[key] - expected) < 1e-14, key);
  }
});
test('matches exhaustive enumeration on 80 seeded conflict graphs', () => {
  let seed = 127;
  const random = () => {seed = (Math.imul(1664525, seed) + 1013904223) >>> 0; return seed / 2**32;};
  for (let trial = 0; trial < 80; trial++) {
    const rows = Array.from({length: 10}, (_, i) => {
      const h = Math.floor(random() * 8), a = (h + 1 + Math.floor(random() * 7)) % 8;
      return row(i + 1, .1 + .89 * random(), {home: 'T' + h, away: 'T' + a});
    });
    const n = 1 + trial % 4;
    let best = 0;
    for (let mask = 0; mask < 2**rows.length; mask++) {
      const legs = rows.filter((_, i) => mask & (1 << i));
      if (legs.length !== n || new Set(legs.flatMap(r => [r.home, r.away])).size !== 2*n) continue;
      best = Math.max(best, legs.reduce((p, r) => p * r.p, 1));
    }
    const r = E.suggest(rows, n, options);
    assert.ok(Math.abs((r.metrics?.probability || 0) - best) < 1e-14, `trial ${trial}`);
    const reversed = E.suggest([...rows].reverse(), n, options);
    assert.deepEqual(reversed.legs, r.legs);
  }
});

function quote(r, extra = {}) {
  return {...r, run_id: 'run', status: 'matched', bookmaker: 'Sisal', over_odds: 1.8,
    observed_at: '2026-09-17T11:45:00Z', recorded_at: '2026-09-17T11:46:00Z', kickoff: '2026-09-18T18:00:00Z',
    settlement_rule: 'sisal_official_opta_fallback_90min_halfline', ...extra};
}
test('Sisal filter acts before selecting the most likely market of a match', () => {
  const high = row(1, .99), available = row(1, .8, {line: 9.5, selection_id: 'available'});
  const rows = E.withSisalQuotes([high, available], [quote(available)], {now, runId: 'run', onlyQuoted: true});
  assert.equal(E.suggest(rows, 1, options).legs[0].selection_id, 'available');
});
test('Sisal rejects old runs, expired quotes, wrong lines and future timestamps', () => {
  const r = row(1, .8);
  for (const extra of [{run_id: 'old'}, {line: 9.5}, {recorded_at: '2026-09-17T13:00:00Z'},
    {observed_at: '2026-09-17T10:00:00Z'}, {kickoff: '2026-09-17T11:00:00Z'}, {over_odds: null},
    {scope: 'total'}, {bookmaker: 'Other'}, {settlement_rule: 'unknown'}]) {
    assert.equal(E.withSisalQuotes([r], [quote(r, extra)], {now, runId: 'run', onlyQuoted: true}).length, 0);
  }
  assert.equal(E.withSisalQuotes([r], [], {now, runId: 'run', onlyQuoted: true}).length, 0);
});
test('today can be suggested only with a fresh matched quote and a future kickoff', () => {
  const r = row(1, .8, {match_date: '2026-09-17'});
  assert.equal(E.suggest([r], 1, options).status, 'insufficient');
  const rows = E.withSisalQuotes([r], [quote(r, {kickoff: '2026-09-17T18:00:00Z'})], {now, runId: 'run'});
  assert.equal(E.suggest(rows, 1, options).status, 'suggested');
});

function priced(id,p,odds,extra={}) {
  const r=row(id,p,extra);return {...r,quote:quote(r,{over_odds:odds})};
}
test('baseline requires a real fresh price strictly greater than 1.05',()=>{
  const rows=[priced(1,.99,1.04),priced(2,.98,1.05),priced(3,.8,1.06),row(4,.999)];
  const result=E.suggest(rows,1,{...options,minOdds:1.05});
  assert.equal(result.legs[0].match_id,'3');
  assert.equal(result.excludedOdds,3);
  for(const extra of [{observed_at:'2026-09-17T10:00:00Z'}, {kickoff:'2026-09-17T11:00:00Z'},
    {line:9.5},{bookmaker:'Other'}]) {
    const r=priced(5,.9,1.5);r.quote={...r.quote,...extra};
    assert.equal(E.suggest([r],1,{...options,minOdds:1.05}).status,'insufficient');
  }
});
test('value filtering happens before picking the most likely line per game',()=>{
  const high=priced(1,.99,1.06),value=priced(1,.8,1.4,{line:9.5,selection_id:'value'});
  assert.equal(E.suggest([high,value],1,{...options,minOdds:1.05}).legs[0].selection_id,high.selection_id);
  const r=E.suggest([high,value],1,{...options,minOdds:1.05,playWell:true,minEdge:.10});
  assert.equal(r.legs[0].selection_id,'value');
  assert.equal(r.excludedValue,1);
});
test('user-chosen EV threshold is inclusive and not a probability-point gap',()=>{
  const r=priced(1,.7,1.5); // 5% EV, 3.333... probability points.
  assert.equal(E.suggest([r],1,{...options,minOdds:1.05,playWell:true,minEdge:.05}).status,'suggested');
  assert.equal(E.suggest([r],1,{...options,minOdds:1.05,playWell:true,minEdge:.051}).status,'insufficient');
  const v=E.value(r);
  assert.ok(Math.abs(v.expectedReturn-.05)<1e-12);
  assert.ok(Math.abs(v.probabilityGap-(.7-1/1.5))<1e-12);
  assert.ok(v.stressReturn<0);
});
test('a latest forecast failing the value threshold never revives an older one',()=>{
  const old=priced(1,.9,1.4),recent=priced(1,.7,1.4,{published_at:'2026-09-17T11:00:00Z',selection_id:'latest'});
  assert.equal(E.suggest([old,recent],1,{...options,minOdds:1.05,playWell:true,minEdge:.05}).status,'insufficient');
});
test('all favorable alternatives are shown but only one is selected per match',()=>{
  const a=priced(1,.8,1.4),b=priced(1,.7,1.6,{line:9.5,selection_id:'alternative'});
  const opts={...options,minOdds:1.05,playWell:true,minEdge:.05};
  assert.equal(E.eligibleMarkets([a,b],opts).rows.length,2);
  assert.equal(E.suggest([a,b],2,opts).status,'insufficient');
});
test('invalid margin inputs are not silently converted to permissive filters',()=>{
  for(const minEdge of [NaN,Infinity,-.1,1.1,'5']) {
    assert.throws(()=>E.suggest([],1,{...options,minOdds:1.05,playWell:true,minEdge}),RangeError);
  }
});
