'use strict';
let SUGGESTION = null;
const SUGGESTION_SORT = {key:'p', direction:'descending'};
const SUGGESTION_COLUMNS = [
  ['match','Partita / selezione'], ['p','P modello'], ['odds','Quota Sisal'],
  ['fairOdds','Quota pareggio modello'], ['probabilityGap','Distacco dalla probabilità di pareggio Sisal'],
  ['expectedReturn','Rendimento atteso'], ['stressReturn','Con P −5 punti']
];
const SUGGESTION_FINISHED = D.matches.map(r => ({league: r.campionato, match_id: r.matchId}));
function suggestionLabel(r) {
  const subject = r.side === 'total' ? 'Totale partita' : r.side === 'home' ? r.home : r.away;
  return `${subject} · Over ${fmt(r.line, 1)} ${r.target === 'shots' ? 'tiri' : 'tiri in porta'}`;
}
function suggestionFilters() {
  return {league: $('suggest-league').value, market: $('suggest-market').value, day: $('suggest-day').value,
    availability: 'sisal', minOdds:1.05, playWell:$('suggest-play-well').checked,
    minEdge:$('suggest-play-well').checked ? Number($('suggest-edge').value)/100 : 0};
}
function sisalCandidates(now = new Date()) {
  const sisal = D.over.sisal || {}, run = sisal.last_run;
  const quoted = OverSuggestion.withSisalQuotes(D.over.candidates, sisal.observations, {now, runId: run?.id, onlyQuoted: true});
  const statuses = {access_failed:'Accesso al sito non riuscito', failed:'Raccolta non riuscita', no_future_predictions:'Previsioni future da aggiornare',
    no_event_links:'Nessun link alle partite riconosciuto', no_matching_markets:'Nessun mercato leggibile e abbinabile', collected:'Raccolta eseguita'};
  $('sisal-status').textContent = run ? `${statuses[run.status] || run.status} il ${new Date(run.finished_at).toLocaleString('it-IT', {timeZone:'Europe/Rome'})} (ora italiana). ${quoted.length} selezioni con quota recente. Le regole di liquidazione restano da verificare.` : 'Raccolta non ancora eseguita.';
  return OverSuggestion.withSisalQuotes(D.over.candidates, sisal.observations,
    {now, runId: run?.id, onlyQuoted: true});
}
function refreshSuggestionDays() {
  const prev = $('suggest-day').value;
  const eligible = OverSuggestion.prepare(sisalCandidates(), {finished: SUGGESTION_FINISHED}).rows;
  const days = [...new Set(eligible.map(r => r.match_date))].sort();
  $('suggest-day').innerHTML = '<option value="all">Tutte le date future</option>' + days.map(d => `<option value="${ESC(d)}">${date(d)}</option>`).join('');
  if (days.includes(prev)) $('suggest-day').value = prev;
  // Preserve an explicitly selected day even when it expires: do not widen the request.
  else if (prev && prev !== 'all') {
    const option = document.createElement('option'); option.value = prev;
    option.textContent = date(prev) + ' · non più disponibile';
    $('suggest-day').append(option); $('suggest-day').value = prev;
  }
}
function renderSuggestionValues(rows, filters) {
  const container=$('suggest-value-list'), open=container.querySelector('details')?.open ?? true;
  if (!filters.playWell) {container.innerHTML='';return;}
  const {key,direction}=SUGGESTION_SORT, sign=direction==='ascending'?1:-1;
  const entries=rows.map(r=>({r,v:OverSuggestion.value(r),match:`${r.home} – ${r.away} · ${suggestionLabel(r)}`}));
  entries.sort((a,b)=>{
    const av=key==='match'?a.match:key==='p'?a.r.p:a.v[key];
    const bv=key==='match'?b.match:key==='p'?b.r.p:b.v[key];
    const delta=key==='match'?av.localeCompare(bv,'it',{numeric:true,sensitivity:'base'}):av-bv;
    return sign*delta || String(a.r.selection_id).localeCompare(String(b.r.selection_id));
  });
  container.innerHTML=`<details ${open?'open':''}><summary>${rows.length} linee con vantaggio atteso almeno ${fmt(filters.minEdge*100,1)}%</summary>
    <p class="small">Clicca su una colonna per ordinare; un secondo clic inverte l'ordine. Ogni riga è un'alternativa: gli esiti della stessa partita non vanno sommati nella schedina. Il rendimento è stimato dal modello, con regole Sisal da verificare.</p>
    <div class="scroll"><table><thead><tr>${SUGGESTION_COLUMNS.map(([k,label])=>`<th scope="col" aria-sort="${k===key?direction:'none'}"><button type="button" class="suggest-sort" data-sort="${k}" aria-label="${ESC(label)}: ordina ${k===key&&direction==='ascending'?'decrescente':'crescente'}">${ESC(label)} <span aria-hidden="true">${k===key?(direction==='ascending'?'↑':'↓'):'↕'}</span></button></th>`).join('')}</tr></thead>
    <tbody>${entries.map(({r,v})=>`<tr data-selection-id="${ESC(r.selection_id)}"><td>${ESC(r.home)} – ${ESC(r.away)}<br>${ESC(suggestionLabel(r))}</td><td>${pct(r.p)}</td><td>${fmt(v.odds)}</td><td>${fmt(v.fairOdds,3)}</td><td>${signed(v.probabilityGap*100,1)} punti</td><td>${signed(v.expectedReturn*100,1)}%</td><td>${signed(v.stressReturn*100,1)}%</td></tr>`).join('') || '<tr><td colspan="7" class="empty">Nessuna linea raggiunge il margine scelto.</td></tr>'}</tbody></table></div></details>`;
}
function renderReadableMatches(candidates, options) {
  const container=$('suggest-readable-matches');
  const expanded=new Set([...container.querySelectorAll('details[open]')].map(el=>el.dataset.matchKey));
  // Date, league and market apply; coupon price and value thresholds do not.
  const rows=OverSuggestion.eligibleMarkets(candidates,{...options,minOdds:null,playWell:false,minEdge:0}).rows;
  const groups=new Map();
  for (const r of rows) {
    const key=JSON.stringify([r.league,String(r.match_id)]);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(r);
  }
  const matches=[...groups.entries()].sort((a,b)=>Date.parse(a[1][0].quote.kickoff)-Date.parse(b[1][0].quote.kickoff) || a[1][0].home.localeCompare(b[1][0].home,'it'));
  container.innerHTML=`<h3>Partite con quote Sisal leggibili</h3><p class="small">${matches.length} partite · ${rows.length} linee Over abbinate alle previsioni. Quote dell'ultima raccolta, rilevate da meno di 60 minuti, per gare non ancora iniziate. L'elenco segue campionato, data e mercato; include anche le quote escluse dalla soglia 1,05 o da “Giocare bene”. Apri una partita per leggere le singole quote. Orari italiani; regole di liquidazione da verificare.</p>`+
    (matches.map(([key,lines])=>{
      lines.sort((a,b)=>a.target.localeCompare(b.target) || a.scope.localeCompare(b.scope) || a.side.localeCompare(b.side) || a.line-b.line);
      const r=lines[0],odds=lines.map(x=>x.quote.over_odds);
      return `<details class="readable-match" data-match-key="${ESC(key)}" ${expanded.has(key)?'open':''}><summary>${ESC(r.home)} – ${ESC(r.away)} · ${lines.length} linee · quote ${fmt(Math.min(...odds))}–${fmt(Math.max(...odds))}<small>${ESC(NAMES[r.league]||r.league)} · ${ESC(new Date(r.quote.kickoff).toLocaleString('it-IT',{timeZone:'Europe/Rome'}))}</small></summary>
        <div class="scroll"><table><thead><tr><th scope="col">Mercato / selezione</th><th scope="col">Quota Sisal</th><th scope="col">P modello</th><th scope="col">Rilevata alle</th></tr></thead><tbody>${lines.map(x=>`<tr data-selection-id="${ESC(x.selection_id)}"><td>${ESC(suggestionLabel(x))}</td><td><b>${fmt(x.quote.over_odds)}</b>${x.quote.over_odds<=1.05?'<br><small>Esclusa dal suggeritore: quota ≤ 1,05</small>':''}</td><td>${pct(x.p)}</td><td>${ESC(new Date(x.quote.observed_at).toLocaleString('it-IT',{timeZone:'Europe/Rome'}))}</td></tr>`).join('')}</tbody></table></div></details>`;
    }).join('') || '<p class="empty">Nessuna partita con quote recenti abbinate nei filtri scelti. Importa nuove quote Sisal e riapri il report aggiornato.</p>');
}
function refreshReadableMatches() {
  const now=new Date();
  renderReadableMatches(sisalCandidates(now),{...suggestionFilters(),now,finished:SUGGESTION_FINISHED});
}
function clearSuggestion() {
  SUGGESTION = null;
  $('suggest-export').disabled = true;
  $('suggest-result').innerHTML = '';
  $('suggest-value-list').innerHTML = '';
  refreshReadableMatches();
  $('suggest-status').textContent = 'Filtri aggiornati. Premi “Trova la schedina” per ricalcolare.';
}
function runSuggestion() {
  $('suggest-edge').disabled=!$('suggest-play-well').checked;
  if ($('suggest-play-well').checked && (!$('suggest-edge').value.trim() || !$('suggest-edge').checkValidity())) {
    clearSuggestion();
    $('suggest-status').textContent='Giocare bene: scegli il vantaggio atteso minimo, da 0,1% a 100%.';
    $('suggest-result').innerHTML='<div class="callout"><b>Nessuna giocata.</b> Imposta il margine desiderato per applicare il filtro.</div>';
    return;
  }
  refreshSuggestionDays();
  const now = new Date(), filters = suggestionFilters(), size = Number($('suggest-size').value);
  const candidates=sisalCandidates(now),options={now, finished:SUGGESTION_FINISHED,...filters};
  const result = OverSuggestion.suggest(candidates, size, options);
  const valueRows=OverSuggestion.eligibleMarkets(candidates,options).rows;
  renderSuggestionValues(valueRows,filters);
  renderReadableMatches(candidates,options);
  SUGGESTION = {...result, generated_at: now.toISOString(), filters};
  $('suggest-export').disabled = result.status !== 'suggested';
  const pool = `${result.markets} mercati su ${result.matches} partite future nei filtri scelti`;
  if (result.status !== 'suggested') {
    $('suggest-status').textContent = `${pool}. Non esiste una combinazione ammissibile da ${size} eventi.`;
    $('suggest-result').innerHTML = '<div class="callout"><b>Nessuna giocata.</b> Non ci sono abbastanza partite compatibili con quote recenti superiori a 1,05 e con il margine richiesto. Aggiorna le quote o modifica numero di eventi e filtri.</div>';
    return;
  }
  const m = result.metrics;
  const offered = size === 1 ? result.legs[0].quote?.over_odds : null;
  const priceText = offered ? `${fmt(offered)} · Sisal, rilevata; regole da verificare` : 'non verificata';
  const evText = offered ? `${signed((m.probability * offered - 1) * 100, 1)}% · ipotesi di regole equivalenti` : 'non calcolabile senza quota';
  $('suggest-status').textContent = `${size} eventi selezionati · ${pool}. Quote > 1,05${filters.playWell ? `, vantaggio atteso ≥ ${fmt(filters.minEdge*100,1)}% per evento` : ''}. Massimo del prodotto delle probabilità fra gli eventi ammessi.`;
  $('suggest-result').innerHTML = `
    <div class="cards">
      <div class="card"><div class="label">Probabilità di vincita stimata</div><div class="value">${pct(m.probability)}</div><p>Di prendere tutti gli eventi, assumendo indipendenza</p></div>
      <div class="card"><div class="label">Probabilità di perdere</div><div class="value">${pct(m.loss)}</div><p>Almeno un evento perso, assumendo indipendenza</p></div>
      <div class="card"><div class="label">Quota di pareggio</div><div class="value">${fmt(m.fairOdds, 3)}</div><p>Calcolata dal modello, assumendo indipendenza</p></div>
      <div class="card"><div class="label">Con probabilità ridotte di 5 punti</div><div class="value">${pct(m.stress5)}</div><p>Scenario di sensibilità, assumendo indipendenza</p></div>
    </div>
    <div class="scroll"><table><thead><tr><th>Data / campionato</th><th>Partita</th><th>Evento suggerito</th><th>Probabilità singola</th><th>Quota di mercato</th></tr></thead><tbody>${result.legs.map(r => `<tr><td>${date(r.match_date)}<br><small>${ESC(NAMES[r.league] || r.league)}</small></td><td>${ESC(r.home)} – ${ESC(r.away)}</td><td><b>${ESC(suggestionLabel(r))}</b><br><small>Previsione: ${ESC(new Date(r.published_at).toLocaleString('it-IT', {timeZone: 'Europe/Rome'}))} · ora italiana</small></td><td>${pct(r.p)}</td><td>${r.quote ? `${fmt(r.quote.over_odds)} · Sisal<br><small>${ESC(new Date(r.quote.observed_at).toLocaleString('it-IT', {timeZone:'Europe/Rome'}))}<br>Regole da verificare</small>` : 'Da verificare'}</td></tr>`).join('')}</tbody></table></div>
    <p class="small">Senza assumere indipendenza: probabilità congiunta compresa fra ${pct(m.lower)} e ${pct(m.upper)}, a probabilità delle singole date. Quota offerta: <b>${priceText}</b>. Rendimento atteso: <b>${evText}</b>. ${size > 1 ? 'La quota complessiva della multipla deve essere rilevata separatamente.' : ''}</p>
    <div class="callout"><b>Selezioni proposte dal modello; nessuna giocata registrata.</b> Verifica disponibilità delle linee, quote e regole del bookmaker. Il suggerimento da solo non dimostra un vantaggio economico.</div>`;
}
function exportSuggestion() {
  // Re-check time and filters so an overnight-open page cannot export stale selections.
  runSuggestion();
  if (SUGGESTION?.status !== 'suggested') return;
  const m = SUGGESTION.metrics;
  const singlePrice = SUGGESTION.size === 1 ? SUGGESTION.legs[0].quote?.over_odds : null;
  const content = [
    'Schedina suggerita dal modello · simulazione',
    `Generata: ${SUGGESTION.generated_at}`,
    `Filtri: ${JSON.stringify(SUGGESTION.filters)} · eventi: ${SUGGESTION.size}`,
    'Quota Sisal strettamente superiore a 1,05 per ogni evento.',
    SUGGESTION.filters.playWell ? `Giocare bene: EV modello minimo ${fmt(SUGGESTION.filters.minEdge*100,1)}% per selezione.` : 'Giocare bene: disattivato.',
    ...SUGGESTION.legs.map((r, i) => `${i + 1}. ${date(r.match_date)} · ${NAMES[r.league] || r.league} · ${r.home} – ${r.away}\n   ${suggestionLabel(r)} · P singola ${pct(r.p)}\n   Previsione ${r.published_at} · ID ${r.selection_id}${r.quote ? `\n   Quota Sisal ${fmt(r.quote.over_odds)} · ${r.quote.observed_at} · ${r.quote.source_url} · regole da verificare` : ''}`),
    `Probabilità di prendere tutti gli eventi (indipendenza): ${pct(m.probability)}`,
    `Probabilità di perdere (indipendenza): ${pct(m.loss)}`,
    `Limiti senza indipendenza, a marginali date: ${pct(m.lower)} – ${pct(m.upper)}`,
    `Probabilità con marginali −5 punti (indipendenza, scenario): ${pct(m.stress5)}`,
    `Quota di pareggio (indipendenza): ${fmt(m.fairOdds, 3)}`,
    singlePrice ? `Quota Sisal rilevata: ${fmt(singlePrice)}. EV modello: ${signed((m.probability * singlePrice - 1) * 100, 1)}%, ipotizzando regole equivalenti da verificare.` : 'Quota offerta: non verificata. Rendimento atteso: non calcolabile.',
    'Linee da verificare presso il bookmaker. Probabilità stimate, non garanzie.',
    'Nessuna giocata registrata. Il protocollo economico rimane separato.'
  ].join('\n\n');
  download('schedina_suggerita.txt', content, 'text/plain;charset=utf-8');
}
if (D.over) {
  const leagues = [...new Set(D.over.candidates.map(r => r.league))].sort();
  $('suggest-league').innerHTML = '<option value="TUTTI">Tutti i campionati</option>' + leagues.map(l => `<option value="${ESC(l)}">${ESC(NAMES[l] || l)}</option>`).join('');
  refreshSuggestionDays();
  ['suggest-size', 'suggest-market', 'suggest-league', 'suggest-day', 'suggest-availability'].forEach(id => $(id).addEventListener('change', clearSuggestion));
  ['suggest-play-well','suggest-edge'].forEach(id=>$(id).addEventListener('change',runSuggestion));
  $('suggest-run').addEventListener('click', runSuggestion);
  $('suggest-export').addEventListener('click', exportSuggestion);
  $('suggest-value-list').addEventListener('click',event=>{
    const button=event.target.closest('button[data-sort]');
    if (!button) return;
    const key=button.dataset.sort;
    if (!SUGGESTION_COLUMNS.some(([k])=>k===key)) return;
    SUGGESTION_SORT.direction=SUGGESTION_SORT.key===key && SUGGESTION_SORT.direction==='ascending'?'descending':'ascending';
    SUGGESTION_SORT.key=key;
    // Refresh eligibility when sorting too, so expired prices cannot linger.
    runSuggestion();
    $('suggest-value-list').querySelector(`button[data-sort="${key}"]`)?.focus({preventScroll:true});
  });
  // Re-check an open tab when Rome's calendar date advances.
  setInterval(() => {
    if (SUGGESTION) runSuggestion();
    else refreshReadableMatches();
  }, 30000);
  runSuggestion();
}
