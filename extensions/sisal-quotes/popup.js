'use strict';
const $ = id => document.getElementById(id);
async function refresh() {
  const state = await chrome.storage.local.get({enabled:true,captures:[]});
  $('enabled').checked = state.enabled;
  $('count').textContent = `${state.captures.length} pagine nell’archivio locale`;
  $('export').disabled = !state.captures.length;
  $('clear').disabled = !state.captures.length;
}
async function read(manual = false) {
  $('read').disabled = true;
  try {
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    const result = await SisalConnection.readTab(chrome, tab, manual);
    if (result.paused) {$('status').textContent='Raccolta in pausa.'; return;}
    if (!result.ok) throw Error(result.error || 'Pagina non supportata.');
    const c = result.capture;
    $('status').textContent = c.blocks.length ? `Pagina salvata nell’archivio: ${c.blocks.length} mercati leggibili · ${new Date(c.observed_at).toLocaleTimeString('it-IT')}. Abbinamento alla previsione da verificare durante l’importazione.` : 'Pagina salvata nell’archivio, ma nessun mercato riconosciuto. Apri STATS MATCH e ripeti la lettura.';
    $('preview').replaceChildren();
    for (const b of c.blocks) {
      const card = document.createElement('div'); card.className='market';
      const label=document.createElement('strong');label.textContent=b.label;card.append(label);
      const prices=document.createElement('span');prices.textContent=b.outcomes.map(o=>o.text+(o.disabled?' · sospeso':'')).join(' | ');card.append(prices);
      $('preview').append(card);
    }
    await refresh();
  } catch (e) {
    $('status').textContent = 'Lettura non salvata. '+e.message;
    $('preview').replaceChildren();
  } finally {$('read').disabled=false;}
}
$('enabled').addEventListener('change', async () => {
  await chrome.storage.local.set({enabled:$('enabled').checked});
  $('status').textContent=$('enabled').checked?'Raccolta attiva nelle pagine Sisal aperte.':'Raccolta in pausa.';
});
$('read').addEventListener('click', () => read(true));
$('clear').addEventListener('click', async () => {
  const result = await chrome.runtime.sendMessage({type:'sisal.clear'});
  if (!result.ok) {$('feedback').textContent=result.error;return;}
  $('preview').replaceChildren();$('status').textContent='Archivio svuotato e raccolta in pausa.';await refresh();
});
$('export').addEventListener('click', async () => {
  const {captures=[]}=await chrome.storage.local.get('captures');
  if (!captures.length) return;
  const bundle={schema:'sisal-chrome-captures',version:1,exported_at:new Date().toISOString(),captures};
  const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='sisal_quote_'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
  $('feedback').textContent='JSON esportato. Trascinalo su scripts/importa_quote_sisal.cmd per aggiornare il report. Le quote devono avere meno di 60 minuti.';
});
chrome.storage.onChanged.addListener(changes => {
  if (changes.captures || changes.enabled) refresh().catch(e=>{$('feedback').textContent=e.message;});
});
refresh().then(() => read()).catch(e=>{$('status').textContent='Archivio non accessibile: '+e.message;});
