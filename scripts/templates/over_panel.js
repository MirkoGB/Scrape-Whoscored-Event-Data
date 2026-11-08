'use strict';
const PAPER_LEGS=[];
function overMoney(n){return n==null?'—':fmt(n)+' u'}
function overPct(n){return n==null?'—':pct(n)}
function renderOver(){
 if(!D.over)return;
 const o=D.over,p=o.protocol;
 $('over-status').textContent=`${o.coverage.team_matches} gare valutate per squadra · ${o.coverage.total_matches} per i totali · ${o.coverage.prospective_quotes} quote prospettiche documentate`;
 $('over-decision').textContent=o.quotes.length?'Decisioni solo dopo verifica delle quote.':'Nessuna giocata.';
 $('over-explanation').textContent=o.quotes.length?'Il laboratorio resta ipotetico; solo il registro conserva le decisioni anteriori alle gare.':'Mancano quote di mercato pre-partita verificabili. La calibrazione è misurabile; il profitto non è ancora dimostrato.';
 $('over-protocol').textContent=`Protocollo congelato il ${date(p.frozen_at)}. Test futuro dal ${date(p.test_from)}. Ogni strategia: ${fmt(p.bankroll,0)} unità virtuali iniziali, massimo ${fmt(p.daily_budget,0)} unità per data di gioco; stop a ${fmt(p.stop_drawdown,0)} unità di calo dal picco. Budget simulato, non denaro reale.`;
 const cal=o.calibration.filter(r=>r.league===STATE.league&&r.target===STATE.target&&r.scope===$('over-scope').value);
 $('over-calibration').innerHTML=cal.map(r=>`<tr><td>${fmt(r.line,1)}</td><td>${r.n}</td><td>${pct(r.predicted)}</td><td>${pct(r.observed)}</td><td>${r.gap_low==null?'—':signed(r.gap_low*100,1)+' / '+signed(r.gap_high*100,1)+' pp'}</td><td>${fmt(r.brier,3)}</td><td>${signed(r.brier_skill*100,1)}%</td></tr>`).join('');
 $('over-performance').innerHTML=o.performance.map(r=>`<tr><td>${r.size===1?'Singole':'Multiple da '+r.size}</td><td>${r.bets}</td><td>${r.pending}</td><td>${overMoney(r.staked_settled)}</td><td>${overMoney(r.profit)}</td><td>${overPct(r.roi)}</td><td>${overPct(r.loss_rate)}</td><td>${r.max_losing_streak??'—'}</td><td>${overMoney(r.max_drawdown)}</td></tr>`).join('');
 $('over-risk').innerHTML=o.risk.map(r=>`<tr><td>${r.size} · ${ESC(r.scenario)}</td><td>${r.n}</td><td>${overPct(r.probability_loss)}</td><td>${overMoney(r.drawdown95)}</td><td>${r.losing_streak95==null?'—':fmt(r.losing_streak95,0)}</td></tr>`).join('');
 $('over-decisions').innerHTML=o.decisions.flatMap(d=>d.plans.map(p=>`<tr><td>${date(d.day)} · ${p.size}</td><td title="${ESC(p.reason)}">${p.status==='no_bet'?'Nessuna giocata':'Puntata virtuale'}</td><td>${fmt(p.metrics?.offered_odds)}</td><td>${overPct(p.metrics?.p_independent)}</td><td>${overPct(p.metrics?.p_robust)}</td><td>${fmt(p.metrics?.fair_independent)}</td><td>${p.metrics?signed(p.metrics.ev_robust*100,1)+'%':'—'}</td></tr>`)).join('')||'<tr><td colspan="7" class="empty">Nessuna decisione congelata: quote non ancora raccolte.</td></tr>';
 $('over-dependence').innerHTML=o.dependence.filter(r=>r.league===STATE.league).map(r=>`<p>${ESC(r.pair)}: <b>${signed(r.correlation)}</b> (${r.n} gare)</p>`).join('');
 $('over-sources').innerHTML=o.sources.map(r=>`<a href="${ESC(r.url)}" target="_blank" rel="noopener">${ESC(r.title)}</a>`).join(' · ');
 const days=[...new Set(o.candidates.map(r=>r.match_date))].sort(),prev=$('paper-day').value;
 $('paper-day').innerHTML=days.map(d=>`<option value="${d}">${date(d)}</option>`).join('');
 if(days.includes(prev))$('paper-day').value=prev;
 renderPaperOptions();renderPaperSlip();
}
function renderPaperOptions(){
 const rows=D.over.candidates.filter(r=>r.match_date===$('paper-day').value&&(STATE.league==='TUTTI'||r.league===STATE.league)&&r.target===STATE.target&&r.scope===$('over-scope').value);
 $('paper-selection').innerHTML=rows.map(r=>`<option value="${ESC(r.selection_id)}">${ESC(NAMES[r.league])} · ${ESC(r.home)} – ${ESC(r.away)} · ${ESC(r.side==='total'?'Totale':r.side==='home'?r.home:r.away)} Over ${fmt(r.line,1)} · ${pct(r.p)}</option>`).join('');
 if(!rows.length)$('paper-selection').innerHTML='<option value="">Nessun evento con questi filtri</option>';
}
function paperMetrics(legs,odds){
 const p=legs.map(r=>r.p),n=p.length,ind=p.reduce((a,b)=>a*b,1),low=Math.max(0,p.reduce((a,b)=>a+b,0)-n+1),up=Math.min(...p),rob=Math.max(0,p.reduce((a,b)=>a+Math.max(0,b-.05),0)-n+1),stress=Math.max(0,p.reduce((a,b)=>a+Math.max(0,b-.10),0)-n+1);
 return {ind,low,up,rob,stress,ev:odds?ind*odds-1:null,robEv:odds?rob*odds-1:null};
}
function renderPaperSlip(){
 $('paper-legs').innerHTML=PAPER_LEGS.map((r,i)=>`<tr><td>${ESC(r.home)} – ${ESC(r.away)}<br><small>${r.target==='shots'?'Tiri':'SoT'} · ${ESC(r.side==='total'?'totale':r.side==='home'?r.home:r.away)} Over ${fmt(r.line,1)}</small></td><td>${pct(r.p)}</td><td>${fmt(r.price)}</td><td><button class="button" data-remove-paper="${i}" aria-label="Rimuovi selezione ${i+1}">×</button></td></tr>`).join('')||'<tr><td colspan="4" class="empty">Nessun evento aggiunto. Nessuna giocata.</td></tr>';
 document.querySelectorAll('[data-remove-paper]').forEach(b=>b.addEventListener('click',()=>{PAPER_LEGS.splice(Number(b.dataset.removePaper),1);renderPaperSlip()}));
 if(!PAPER_LEGS.length){$('paper-metrics').innerHTML='';return}
 const input=Number($('paper-total-price').value),odds=PAPER_LEGS.length===1?PAPER_LEGS[0].price:input>1?input:null,m=paperMetrics(PAPER_LEGS,odds),product=PAPER_LEGS.reduce((a,r)=>a*r.price,1);
 $('paper-metrics').innerHTML=`<div class="cards"><div class="card"><div class="label">Probabilità · indipendenza</div><div class="value">${pct(m.ind)}</div><p>Scenario, non congiunta validata</p></div><div class="card"><div class="label">Intervallo senza indipendenza</div><div class="value" style="font-size:24px">${pct(m.low)} – ${pct(m.up)}</div><p>A probabilità marginali date</p></div><div class="card"><div class="label">Quota di pareggio</div><div class="value">${fmt(1/m.ind)}</div><p>Prudente: ${m.rob?fmt(1/m.rob):'non finita'}</p></div><div class="card"><div class="label">ROI atteso · indipendenza</div><div class="value">${m.ev==null?'—':signed(m.ev*100,1)+'%'}</div><p>Prudente: ${m.robEv==null?'—':signed(m.robEv*100,1)+'%'}</p></div></div><p class="small">Quota inserita ${odds?fmt(odds):'assente'} · prodotto delle singole ${fmt(product)} (indicativo). Probabilità di perdere: ${pct(1-m.ind)} nello scenario indipendente; intervallo ${pct(1-m.up)}–${pct(1-m.low)} senza indipendenza. Marginali −5 punti: probabilità prudente ${pct(m.rob)}. Stress −10 punti: ${pct(m.stress)}.</p><div class="callout"><b>Nessuna giocata registrata.</b> ${!odds?'Manca la quota complessiva offerta.':m.robEv<D.over.protocol.min_robust_ev?'Questa ipotesi non supera il criterio prudente: astensione.':'Il calcolo ipotetico supera la soglia prudente. Servono quote documentate, stesso bookmaker, tempi validi e decisione congelata prima delle gare.'}</div>`;
}
if(D.over){
 $('over-scope').addEventListener('change',renderOver);
 $('paper-day').addEventListener('change',renderPaperOptions);
 $('paper-total-price').addEventListener('input',renderPaperSlip);
 $('paper-add').addEventListener('click',()=>{
  const r=D.over.candidates.find(r=>r.selection_id===$('paper-selection').value),price=Number($('paper-price').value);let error='';
  if(!r||!Number.isFinite(price)||price<=1)error='Seleziona un evento e inserisci una quota maggiore di 1.';
  else if(PAPER_LEGS.length>=5)error='La simulazione confronta al massimo 5 eventi.';
  else if(PAPER_LEGS.some(x=>x.match_date!==r.match_date))error='Usa eventi della stessa data di gioco per confrontare il budget.';
  else if(PAPER_LEGS.some(x=>x.league===r.league&&(x.match_id===r.match_id||[x.home,x.away].some(t=>[r.home,r.away].includes(t)))))error='Stessa partita o squadra ripetuta: dipendenza non validata. Selezione esclusa.';
  if(error){$('paper-notice').textContent=error;return}
  PAPER_LEGS.push({...r,price});$('paper-notice').textContent='Evento aggiunto alla simulazione ipotetica.';renderPaperSlip();
 });
 $('paper-clear').addEventListener('click',()=>{PAPER_LEGS.length=0;$('paper-total-price').value='';$('paper-notice').textContent='';renderPaperSlip()});
 $('quote-export').addEventListener('click',()=>{
  const r=D.over.candidates.find(r=>r.selection_id===$('paper-selection').value),price=Number($('paper-price').value),kickoff=new Date($('quote-kickoff').value),now=new Date();
  if(!r||price<=1||!Number.isFinite(price)||!Number.isFinite(kickoff.getTime())||kickoff<=now||!$('quote-rule-check').checked||['quote-book','quote-source','quote-rules','quote-proof'].some(k=>!$(k).value.trim())){$('quote-message').textContent='Completa evento, quote, kickoff futuro, bookmaker, fonte, prova e conferma delle regole.';return}
  const under=$('quote-under').value?Number($('quote-under').value):null;
  if(under!==null&&(!Number.isFinite(under)||under<=1)){$('quote-message').textContent='La quota Under deve essere maggiore di 1.';return}
  const row={selection_id:r.selection_id,bookmaker:$('quote-book').value.trim(),over_odds:price,under_odds:under,kickoff:kickoff.toISOString(),observed_at:now.toISOString(),source_url:$('quote-source').value.trim(),rules_url:$('quote-rules').value.trim(),evidence_path:$('quote-proof').value.trim(),settlement_rule:'opta_90min_halfline'};
  download('rilevazione_over.json',JSON.stringify(row,null,2),'application/json');$('quote-message').textContent='Bozza esportata. Acquisiscila nel registro entro 60 minuti e prima del kickoff; non è ancora una quota registrata.';
 });
 renderOver();
}
