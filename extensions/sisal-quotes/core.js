'use strict';
globalThis.SisalStore = (() => {
  function publicUrl(value) {
    try {
      const u = new URL(value);
      return u.protocol === 'https:' && ['www.sisal.it', 'sisal.it'].includes(u.hostname) &&
        !u.username && !u.password && (!u.port || u.port === '443') &&
        (u.pathname === '/scommesse-matchpoint' || u.pathname.startsWith('/scommesse-matchpoint/')) && !/\/(blog|risultati|prenotate)(\/|$)/.test(u.pathname);
    } catch (_) { return false; }
  }
  function cleanCapture(raw, senderUrl, now = Date.now()) {
    if (!publicUrl(senderUrl) || !publicUrl(raw?.source_url)) throw Error('Pagina Sisal non riconosciuta.');
    const sender = new URL(senderUrl), source = new URL(raw.source_url);
    if (sender.origin + sender.pathname !== source.origin + source.pathname) throw Error('La pagina è cambiata: ripeti la lettura.');
    const observed = Date.parse(raw.observed_at);
    if (!Number.isFinite(observed) || observed > now + 5000 || now - observed > 60000) throw Error('Orario della lettura non valido.');
    const strings = (rows, n, length) => (Array.isArray(rows) ? rows : []).filter(x => typeof x === 'string').slice(0, n).map(x => x.slice(0, length));
    const capture = {
      source_url: source.origin + source.pathname, observed_at: new Date(observed).toISOString(),
      transport: 'chrome_extension', blocked: false,
      events: (Array.isArray(raw.events) ? raw.events : []).slice(0, 8).map(e => ({
        home: String(e.home || '').slice(0, 100), away: String(e.away || '').slice(0, 100), kickoff: String(e.kickoff || '').slice(0, 60)})),
      headings: strings(raw.headings, 20, 160), times: strings(raw.times, 10, 60),
      blocks: (Array.isArray(raw.blocks) ? raw.blocks : []).slice(0, 200).map(b => ({
        label: String(b.label || '').slice(0, 140),
        outcomes: (Array.isArray(b.outcomes) ? b.outcomes : []).slice(0, 80).map(o => ({
          text: String(o.text || '').slice(0, 120), disabled: o.disabled !== false}))})),
      frame_hosts: strings(raw.frame_hosts, 10, 150)
    };
    if (JSON.stringify(capture).length > 50000) throw Error('Pagina troppo grande per la raccolta locale.');
    return capture;
  }
  function merge(captures, capture) {
    // Latest complete view of each page, including empty/suspended markets.
    const previous = captures.find(c => c.source_url === capture.source_url);
    if (previous && Date.parse(previous.observed_at) > Date.parse(capture.observed_at)) return captures;
    return [...captures.filter(c => c.source_url !== capture.source_url), capture]
      .sort((a,b) => Date.parse(a.observed_at) - Date.parse(b.observed_at)).slice(-50);
  }
  return {publicUrl, cleanCapture, merge};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = globalThis.SisalStore;
