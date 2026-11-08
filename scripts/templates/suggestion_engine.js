/* Pure optimizer shared by the standalone report and Node tests. */
'use strict';
const OverSuggestion = (() => {
  const matchKey = r => JSON.stringify([r.league, String(r.match_id)]);
  const teamKeys = r => [r.home, r.away].map(t => JSON.stringify([r.league, t.trim().toLowerCase()]));
  const marketKey = r => JSON.stringify([matchKey(r), r.target, r.scope, r.side, r.line]);
  const compare = (a, b) => b.p - a.p || marketKey(a).localeCompare(marketKey(b));
  function romeDay(now) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Rome', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(now);
    return ['year', 'month', 'day'].map(k => parts.find(p => p.type === k).value).join('-');
  }
  function validDay(s) {
    return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) &&
      Number.isFinite(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s;
  }
  function withSisalQuotes(rows, observations, {now = new Date(), runId = null, onlyQuoted = false} = {}) {
    const end = now.getTime(), latest = new Map();
    for (const q of observations || []) {
      const observed = Date.parse(q.observed_at), recorded = Date.parse(q.recorded_at), kickoff = Date.parse(q.kickoff);
      if (!runId || q.run_id !== runId || q.status !== 'matched' || q.bookmaker !== 'Sisal' ||
          !Number.isFinite(q.over_odds) || q.over_odds <= 1 ||
          ![observed, recorded, kickoff].every(Number.isFinite) ||
          observed > recorded || recorded > end || end - observed > 3600000 || kickoff <= end ||
          q.settlement_rule !== 'sisal_official_opta_fallback_90min_halfline') continue;
      const prev = latest.get(q.selection_id);
      if (!prev || observed > Date.parse(prev.observed_at) ||
          (observed === Date.parse(prev.observed_at) && recorded > Date.parse(prev.recorded_at))) latest.set(q.selection_id, q);
    }
    return rows.map(r => {
      const q = latest.get(r.selection_id);
      const fields = ['league', 'target', 'scope', 'side', 'line', 'match_date', 'home', 'away'];
      const compatible = q && String(q.match_id) === String(r.match_id) && fields.every(k => q[k] === r[k]) &&
        Date.parse(r.published_at) <= Date.parse(q.observed_at) && romeDay(new Date(q.kickoff)) === r.match_date;
      return {...r, quote: compatible ? q : null};
    }).filter(r => !onlyQuoted || r.quote);
  }
  function value(r) {
    const odds = r.quote?.over_odds;
    if (!Number.isFinite(odds) || odds <= 1 || !Number.isFinite(r.p) || r.p <= 0 || r.p >= 1) return null;
    return {odds, fairOdds:1/r.p, breakEvenProbability:1/odds,
      probabilityGap:r.p-1/odds, expectedReturn:r.p*odds-1,
      stressReturn:Math.max(0,r.p-.05)*odds-1};
  }
  function eligibleMarkets(rows, {now = new Date(), finished = [], league = 'TUTTI', market = 'all', day = 'all', minOdds = null, playWell = false, minEdge = .05} = {}) {
    if (minOdds !== null && (!Number.isFinite(minOdds) || minOdds < 1)) throw new RangeError('Quota minima non valida.');
    if (!Number.isFinite(minEdge) || minEdge < 0 || minEdge > 1) throw new RangeError('Il margine deve essere fra 0 e 100%.');
    const today = romeDay(now), end = now.getTime(), latest = new Map();
    const done = new Set(finished.map(matchKey));
    let excludedTime = 0;
    for (const r of rows) {
      if (typeof r.p !== 'number' || !Number.isFinite(r.p) || r.p <= 0 || r.p >= 1 ||
          !Number.isFinite(r.line) || r.line < 0 || r.line % 1 !== .5 ||
          !r.league || !r.match_id || !r.selection_id ||
          typeof r.home !== 'string' || !r.home.trim() || typeof r.away !== 'string' || !r.away.trim() ||
          !['shots', 'sot'].includes(r.target) || !['team', 'total'].includes(r.scope) ||
          !(r.scope === 'total' ? r.side === 'total' : ['home', 'away'].includes(r.side)) ||
          !validDay(r.match_date) || !validDay(r.training_through) || r.training_through >= r.match_date) continue;
      const published = Date.parse(r.published_at);
      if (!Number.isFinite(published) || !/(Z|[+-]\d\d:\d\d)$/.test(r.published_at) || published > end) continue;
      // Today's games require a future kickoff read with a fresh bookmaker quote.
      const confirmedToday = r.match_date === today && r.quote && Date.parse(r.quote.kickoff) > end;
      if ((r.match_date <= today && !confirmedToday) || done.has(matchKey(r))) { excludedTime++; continue; }
      if ((league !== 'TUTTI' && r.league !== league) || (day !== 'all' && r.match_date !== day) ||
          (market !== 'all' && market !== `${r.target}:${r.scope}`)) continue;
      const key = marketKey(r), prev = latest.get(key);
      if (!prev || published > Date.parse(prev.published_at) ||
          (published === Date.parse(prev.published_at) && r.selection_id.localeCompare(prev.selection_id) < 0)) latest.set(key, r);
    }
    // Resolve the latest forecast BEFORE filtering by value: do not revive an
    // older, more optimistic forecast when the current one fails the threshold.
    let excludedOdds=0, excludedValue=0;
    const eligible=[];
    for (const r of latest.values()) {
      if (minOdds !== null || playWell) {
        const q=r.quote && withSisalQuotes([r],[r.quote],{now,runId:r.quote.run_id,onlyQuoted:true})[0]?.quote;
        if (!q || q.over_odds <= Math.max(1.05,minOdds ?? 1.05)) {excludedOdds++;continue;}
        if (playWell && value(r).expectedReturn + 1e-12 < minEdge) {excludedValue++;continue;}
      }
      eligible.push(r);
    }
    return {rows:eligible.sort(compare),markets:eligible.length,excludedTime,excludedOdds,excludedValue,today};
  }
  function prepare(rows, options = {}) {
    const prepared=eligibleMarkets(rows,options);
    // Price/value filters must act before choosing the best line of each game.
    const best = new Map();
    for (const r of prepared.rows) {
      const key = matchKey(r);
      if (!best.has(key) || compare(r, best.get(key)) < 0) best.set(key, r);
    }
    return {...prepared, rows:[...best.values()].sort(compare)};
  }
  function metrics(legs) {
    if (!legs.length) return null;
    const p = legs.map(r => r.p), product = p.reduce((a, b) => a * b, 1);
    return {
      probability: product, loss: 1 - product, fairOdds: 1 / product,
      lower: Math.max(0, p.reduce((a, b) => a + b, 0) - p.length + 1), upper: Math.min(...p),
      stress5: p.reduce((a, b) => a * Math.max(0, b - .05), 1)
    };
  }
  function suggest(rows, size, options = {}) {
    if (!Number.isInteger(size) || size < 1 || size > 10) throw new RangeError('Scegli da 1 a 10 eventi.');
    const prepared = prepare(rows, options), pool = prepared.rows;
    let best = null, bestScore = -Infinity;
    const chosen = [], used = new Set(), logs = pool.map(r => Math.log(r.p)), teams = pool.map(teamKeys);
    function search(start, score) {
      const need = size - chosen.length;
      if (!need) { if (score > bestScore) { bestScore = score; best = [...chosen]; } return; }
      if (pool.length - start < need) return;
      // Optimistic bound ignores conflicts. Pruning cannot discard a better feasible coupon.
      let upper = score;
      for (let j = start; j < start + need; j++) upper += logs[j];
      if (upper <= bestScore) return;
      for (let i = start; i <= pool.length - need; i++) {
        let bound = score;
        for (let j = i; j < i + need; j++) bound += logs[j];
        if (bound <= bestScore) break;
        if (teams[i].some(t => used.has(t))) continue;
        teams[i].forEach(t => used.add(t)); chosen.push(pool[i]);
        search(i + 1, score + logs[i]);
        chosen.pop(); teams[i].forEach(t => used.delete(t));
      }
    }
    search(0, 0);
    const legs = best || [];
    return {status: best ? 'suggested' : 'insufficient', size, legs, metrics: metrics(legs),
      matches: pool.length, markets: prepared.markets, excludedTime: prepared.excludedTime,
      excludedOdds:prepared.excludedOdds,excludedValue:prepared.excludedValue,today: prepared.today};
  }
  return {prepare, eligibleMarkets, value, suggest, metrics, romeDay, withSisalQuotes};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = OverSuggestion;
