'use strict';
(() => {
  // A manual read can re-inject this file. Keep exactly one observer/listener.
  globalThis.__sisalCollector?.dispose();
  let enabled = true, timer = null, lastScan = 0, disposed = false;
  const ready = chrome.storage.local.get({enabled:true}).then(s => {enabled=s.enabled;});
  async function scan(manual = false) {
    await ready;
    if (disposed) return {ok:false, error:'Lettore sostituito: ripeti la lettura.'};
    if (!SisalStore.publicUrl(location.href)) return {ok:false, error:'Pagina Sisal non supportata.'};
    if (!enabled && !manual) return {ok:false, paused:true};
    lastScan = Date.now();
    try {
      const capture = SisalReader.capture();
      return await chrome.runtime.sendMessage({type:'sisal.capture', capture, manual});
    } catch (e) { return {ok:false, error:e.message}; }
  }
  function schedule() {
    if (disposed || !enabled || timer !== null) return;
    timer = setTimeout(() => {timer=null; scan();}, Math.max(700, 2500-(Date.now()-lastScan)));
  }
  ready.then(schedule).catch(() => {});
  const onChanged = changes => {
    if (changes.enabled) {enabled=changes.enabled.newValue; if(enabled) schedule();}
  };
  const onMessage = (message, _sender, respond) => {
    if (message?.type === 'sisal.location') {
      respond({url:location.href}); return false;
    }
    if (message?.type !== 'sisal.read') return false;
    scan(message.manual === true).then(respond, e=>respond({ok:false,error:e.message})); return true;
  };
  chrome.storage.onChanged.addListener(onChanged);
  chrome.runtime.onMessage.addListener(onMessage);
  const observer = new MutationObserver(schedule);
  observer.observe(document.body, {childList:true, subtree:true, characterData:true,
    attributes:true, attributeFilter:['disabled','aria-disabled','class','style','hidden']});
  const interval = setInterval(schedule, 30000);
  addEventListener('popstate', schedule);
  globalThis.__sisalCollector = {dispose() {
    disposed=true;clearTimeout(timer);clearInterval(interval);observer.disconnect();
    removeEventListener('popstate',schedule);
    try {chrome.storage.onChanged.removeListener(onChanged);} catch (_) {}
    try {chrome.runtime.onMessage.removeListener(onMessage);} catch (_) {}
  }};
})();
