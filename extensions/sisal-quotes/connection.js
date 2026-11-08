'use strict';
globalThis.SisalConnection = (() => {
  async function readTab(api, tab, manual = false) {
    if (!Number.isInteger(tab?.id) || !SisalStore.publicUrl(tab.url)) {
      throw Error('Pagina non supportata. Apri la partita su sisal.it/scommesse-matchpoint e poi premi Leggi questa pagina.');
    }
    if (manual) {
      // activeTab is granted by opening the toolbar popup. Reattach on the
      // explicit click, including tabs opened before installation/reloading.
      try {
        await api.scripting.executeScript({target:{tabId:tab.id, frameIds:[0]},
          files:['core.js', 'reader.js', 'content.js']});
      } catch (e) {
        throw Error('Chrome non consente di collegare il lettore. Controlla l’accesso al sito nei dettagli dell’estensione e ricarica la pagina. Dettaglio: '+e.message);
      }
    }
    let result;
    try {
      result = await api.tabs.sendMessage(tab.id, {type:'sisal.read', manual}, {frameId:0});
    } catch (e) {
      throw Error('Lettore non collegato alla scheda. Premi Leggi questa pagina per ricollegarlo; se persiste, ricarica estensione e pagina. Dettaglio: '+e.message);
    }
    if (!result || (!result.ok && !result.paused)) throw Error(result?.error || 'Il lettore non ha confermato il salvataggio.');
    return result;
  }
  return {readTab};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = globalThis.SisalConnection;
