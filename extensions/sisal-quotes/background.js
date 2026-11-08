'use strict';
importScripts('core.js');
let pending = Promise.resolve();
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (!['sisal.capture', 'sisal.clear'].includes(message?.type)) return false;
  pending = pending.catch(() => {}).then(async () => {
    try {
      if (message.type === 'sisal.clear') {
        if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL('popup.html')) throw Error('Origine del comando non valida.');
        await chrome.storage.local.set({captures:[], enabled:false});
        respond({ok:true}); return;
      }
      if (sender.id !== chrome.runtime.id || sender.frameId !== 0) throw Error('Origine del messaggio non valida.');
      // Chrome's sender.url can remain the initial URL after history.pushState.
      // Ask the SAME live document for its current URL, not an arbitrary tab.
      if (!SisalStore.publicUrl(sender.url) || !sender.documentId || sender.tab?.id == null)
        throw Error('Documento Sisal non verificabile. Ricarica la pagina.');
      const current = await chrome.tabs.sendMessage(sender.tab.id, {type:'sisal.location'}, {documentId:sender.documentId});
      if (!current?.url || new URL(current.url).origin !== new URL(sender.url).origin)
        throw Error('La pagina è cambiata durante la lettura. Riprova.');
      const capture = SisalStore.cleanCapture(message.capture, current.url);
      const saved = await chrome.storage.local.get({enabled:true, captures:[]});
      if (!saved.enabled && message.manual !== true) { respond({ok:false, paused:true}); return; }
      await chrome.storage.local.set({captures: SisalStore.merge(saved.captures, capture)});
      try { if (sender.tab?.id != null) {
        await chrome.action.setBadgeText({tabId:sender.tab.id, text:String(capture.blocks.length)});
        await chrome.action.setBadgeBackgroundColor({tabId:sender.tab.id, color: capture.blocks.length ? '#13776e' : '#986423'});
      }} catch (_) { /* Badge failure must not hide a successful storage write. */ }
      respond({ok:true, blocks:capture.blocks.length, capture});
    } catch (e) { respond({ok:false, error:e.message}); }
  });
  return true;
});
