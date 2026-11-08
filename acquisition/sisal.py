"""Lettura dei mercati pubblici Sisal, senza accesso al conto o invio di giocate.

Il parser accetta solo etichette esplicite: nessuna inferenza da posizione delle
colonne, quote /100, fuzzy matching o prezzo ricostruito. Il formato STATS MATCH
è stato osservato su Fiorentina–Napoli il 19 settembre 2026.
Le osservazioni restano separate dalle quote ammesse dal protocollo economico.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BASE_URL = 'https://www.sisal.it/scommesse-matchpoint/sport/calcio'
RULES_URL = 'https://www.sisal.it/content/dam/new-dam/italy/canali/sisal-it/doc-pdf/scommesse/info-scommesse/calcio.pdf'
RULE = 'sisal_official_opta_fallback_90min_halfline'
ROME = ZoneInfo('Europe/Rome')
LEAGUES = {'ITA-serie-a': 'Serie A', 'ENG-premier-league': 'Premier League',
           'ESP-la-liga': 'Liga', 'GER-bundesliga': 'Bundesliga', 'FRA-ligue-1': 'Ligue 1'}

# Explicit source names, scoped to the league. No substring/fuzzy matching.
# Italian exonyms also occur in sot.calendario.NOMI_FONTE; Sisal spellings
# were observed in its public September 19, 2026 football listings.
TEAM_ALIASES = {
    'ITA-serie-a': {'Parma': 'Parma Calcio 1913', 'Milan': 'AC Milan'},
    'ENG-premier-league': {'Ipswich Town': 'Ipswich', 'Hull City': 'Hull',
                           'Nottingham': 'Nottingham Forest'},
    'ESP-la-liga': {'Athletic Bilbao': 'Athletic Club', 'Alavés': 'Deportivo Alaves',
                    'Siviglia': 'Sevilla', 'Barcellona': 'Barcelona',
                    'Deportivo La Coruña': 'Deportivo de A Coruna', 'Betis': 'Real Betis'},
    'GER-bundesliga': {'Amburgo': 'Hamburger SV', 'Colonia': 'FC Koln',
        'Borussia Monchengladbach': 'Borussia M.Gladbach', 'Mainz': 'Mainz 05',
        'Eintracht Francoforte': 'Eintracht Frankfurt', 'Friburgo': 'Freiburg',
        'Werder Brema': 'Werder Bremen', 'Stoccarda': 'VfB Stuttgart',
        'Lipsia': 'RB Leipzig', 'Elversberg Saar': 'Elversberg'},
    'FRA-ligue-1': {'Strasburgo': 'Strasbourg', 'Tolosa': 'Toulouse', 'Lione': 'Lyon',
                    'Nizza': 'Nice', 'Marsiglia': 'Marseille'},
}


def normal(value):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().lower()).split())


def team_key(league, name):
    aliases = {normal(k): normal(v) for k, v in TEAM_ALIASES.get(league, {}).items()}
    key = normal(name)
    return aliases.get(key, key)


def public_url(value):
    try:
        p = urlsplit(str(value))
        return (p.scheme == 'https' and p.hostname in ('www.sisal.it', 'sisal.it') and
                p.port in (None, 443) and not p.username and not p.password and
                (p.path == '/scommesse-matchpoint' or p.path.startswith('/scommesse-matchpoint/')) and
                not any(x in p.path for x in ('/blog', '/risultati', '/prenotate')))
    except ValueError:
        return False


def timestamp(value):
    t = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('Timestamp senza fuso orario')
    return t.astimezone(timezone.utc)


def market(label):
    """Solo le classi U/O tiri 90 minuti note; eventuale linea nell'intestazione."""
    text = ' '.join(str(label).lower().split()).replace(',', '.')
    team_prefix = re.fullmatch(r'squadra ([12]):\s*(u/o \d+\.5 tiri (?:in porta|totali))', text)
    if team_prefix:
        text = team_prefix[2] + ' squadra ' + team_prefix[1]
    m = re.fullmatch(
        r'(?:u\s*/\s*o|under\s*/\s*over)\s+(?:(\d+\.5)\s+)?'
        r'tiri\s+(in porta|totali)(?:\s+(?:(?:squadra\s+)?(casa|ospite|1|2)|totale partita|match))?', text)
    if not m:
        return None
    side = {'casa': 'home', '1': 'home', 'ospite': 'away', '2': 'away'}.get(m[3], 'total')
    return {'target': 'sot' if m[2] == 'in porta' else 'shots',
            'scope': 'total' if side == 'total' else 'team', 'side': side,
            'header_line': float(m[1]) if m[1] else None}


def prices(block):
    """Ogni esito deve portare la propria linea, oppure una linea nell'header."""
    kind = market(block.get('label', ''))
    if kind is None:
        return []
    values = {}
    conflicts = set()
    for item in block.get('outcomes', []):
        if item.get('disabled') is not False:
            continue
        text = ' '.join(str(item.get('text', '')).lower().replace(',', '.').split())
        m = re.fullmatch(r'(over|under)\s+(?:(\d+\.5)\s+)?(\d+\.\d{1,3})', text)
        if not m:
            continue
        line = float(m[2]) if m[2] else kind['header_line']
        odd = float(m[3])
        if line is None or not 1 < odd < 10000 or (kind['header_line'] is not None and line != kind['header_line']):
            continue
        key = (line, m[1])
        if key in values and values[key] != odd:
            conflicts.add(line)
        values[key] = odd
    return [{**{k: v for k, v in kind.items() if k != 'header_line'}, 'line': line,
             'over_odds': odd, 'under_odds': values.get((line, 'under')), 'market_label': block['label']}
            for (line, side), odd in values.items() if side == 'over' and line not in conflicts]


def event_identity(capture, candidates):
    """La coppia casa/ospite e il kickoff devono essere letti sulla pagina."""
    matches = {}
    for r in candidates:
        matches[(r['league'], str(r['match_id']))] = r
    found = {}
    for event in capture.get('events', []):
        try:
            kickoff = timestamp(event['kickoff'])
        except (KeyError, ValueError, TypeError):
            continue
        for key, r in matches.items():
            if (team_key(r['league'], event.get('home')) == team_key(r['league'], r['home'])
                    and team_key(r['league'], event.get('away')) == team_key(r['league'], r['away'])
                    and str(kickoff.astimezone(ROME).date()) == r['match_date']):
                found[(key, kickoff.isoformat())] = (r, kickoff)
    if len(found) != 1:
        raise ValueError('Partita o kickoff non riconosciuti in modo univoco sulla pagina')
    return next(iter(found.values()))


def match_capture(capture, candidates, now):
    if not public_url(capture.get('source_url', '')):
        raise ValueError('Fonte non appartenente alle pagine pubbliche Sisal previste')
    observed = timestamp(capture['observed_at'])
    clock = timestamp(now)
    if observed > clock or (clock - observed).total_seconds() > 3600:
        raise ValueError('Rilevazione futura o più vecchia di 60 minuti')
    event, kickoff = event_identity(capture, candidates)
    if kickoff <= clock:
        raise ValueError('Gara già iniziata')
    if capture.get('blocked'):
        raise ValueError('Pagina non accessibile')
    latest = {}
    for p in candidates:
        if (p['league'], str(p['match_id'])) != (event['league'], str(event['match_id'])):
            continue
        if timestamp(p['published_at']) > observed or p['training_through'] >= p['match_date']:
            continue
        key = (p['target'], p['scope'], p['side'], p['line'])
        if key not in latest or timestamp(p['published_at']) > timestamp(latest[key]['published_at']):
            latest[key] = p
    matched, excluded, seen, conflicts = [], [], {}, set()
    for block in capture.get('blocks', []):
        for q in prices(block):
            key = tuple(q[k] for k in ('target', 'scope', 'side', 'line'))
            if key in seen and (q['over_odds'], q['under_odds']) != (seen[key]['over_odds'], seen[key]['under_odds']):
                conflicts.add(key)
            seen[key] = q
    for key, q in seen.items():
        if key in conflicts:
            excluded.append({**q, 'reason': 'prezzi discordanti nella stessa rilevazione'})
        elif key not in latest:
            excluded.append({**q, 'reason': 'nessuna previsione anteriore per questa esatta linea'})
        else:
            p = latest[key]
            matched.append({**p, **q, 'bookmaker': 'Sisal', 'kickoff': kickoff.isoformat(),
                            'observed_at': observed.isoformat(), 'source_url': capture['source_url'],
                            'rules_url': RULES_URL, 'settlement_rule': RULE,
                            'status': 'matched', 'economic_eligible': False,
                            'rule_status': 'da_verificare',
                            'rule_note': 'Sisal: dati ufficiali, Opta in assenza. Equivalenza col modello da verificare.'})
    return matched, excluded


# Reads rendered text only. No cookies, network headers, account or bet endpoints.
DOM_SCRIPT = r"""
const visible=e=>e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden';
const text=e=>(e?.innerText||'').trim();
const all=[...document.querySelectorAll('body *')].filter(visible);
const head=/^(?:U\s*\/\s*O|Under\s*\/\s*Over)\s+(?:\d+[.,]5\s+)?Tiri\s+(?:in porta|totali)(?:\s+(?:squadra\s+)?(?:casa|ospite|1|2)|\s+totale partita|\s+match)?$/i;
const outcome=/^(?:Over|Under)\s+(?:\d+[.,]5\s+)?\d+[.,]\d{1,3}$/i;
const norm=s=>s.replace(/\s+/g,' ').trim();
const headings=all.filter(e=>head.test(norm(text(e)))&&![...e.children].some(c=>head.test(norm(text(c)))));
const anyHead=e=>/^(?:U\s*\/\s*O|Under\s*\/\s*Over)\s+.{1,130}$/i.test(norm(text(e)))&&!/\n\s*(?:Over|Under)\s+\d/i.test(text(e));
const boundaries=all.filter(e=>anyHead(e)&&![...e.children].some(anyHead));
const blocks=[];
// Sisal STATS MATCH: each explicit line has its own card and outcome buttons.
// Do not infer outcomes from data-qa IDs or neighbouring columns.
const knownLabels=new Set();
for(const card of document.querySelectorAll('[class*="template_mg-market-attribute__"]')){
 if(!visible(card))continue;
 // Desktop wraps the label with a second "Min - max" line; mobile does not.
 const description=card.querySelector('.mg-market-attribute-desc');
 const label=norm(text(description?description.firstElementChild:card.firstElementChild));
 const canonical=label.replace(/^SQUADRA ([12]):\s*(U\/O \d+[.,]5 TIRI (?:IN PORTA|TOTALI))$/i,'$2 SQUADRA $1');
 if(!head.test(canonical))continue;
 const outcomes=[...card.querySelectorAll('button[data-qa^="esito_"]')].filter(visible).map(e=>({
  text:norm(text(e)),disabled:!!e.closest('[disabled],[aria-disabled="true"],.disabled,.suspended')
 }));
 blocks.push({label,outcomes});knownLabels.add(label);
}
for(const h of headings){
 if(knownLabels.has(norm(text(h))))continue;
 let node=h.parentElement;
 for(let depth=0;node&&depth<6;depth++,node=node.parentElement){
  const hs=boundaries.filter(x=>node.contains(x));
  if(hs.length!==1)break;
  const cells=[...node.querySelectorAll('*')].filter(e=>visible(e)&&outcome.test(norm(text(e)))&&![...e.children].some(c=>outcome.test(norm(text(c)))));
  if(!cells.length)continue;
  blocks.push({label:norm(text(h)),outcomes:cells.map(e=>({text:norm(text(e)),disabled:!!e.closest('[disabled],[aria-disabled="true"],.disabled,.suspended')}))});
  break;
 }
}
const events=[];
// The Italian site publishes local time without an offset in this JSON-LD.
// Resolve Europe/Rome explicitly, independent of the computer's time zone.
const romeTime=s=>{
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(s))return null;
 const target=s.slice(0,19), base=Date.parse(target+'Z'), possible=[];
 const fmt=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 for(const offset of [1,2]){
  const d=new Date(base-offset*3600000);
  if(Number.isFinite(d.getTime())&&fmt.format(d).replace(' ','T')===target)possible.push(d.toISOString());
 }
 return possible.length===1?possible[0]:null;
};
const visit=x=>{
 if(Array.isArray(x)){x.forEach(visit);return}
 if(!x||typeof x!=='object')return;
 if([].concat(x['@type']||[]).includes('SportsEvent')){
  const name=t=>typeof t==='string'?t:t?.name;
  if(name(x.homeTeam)&&name(x.awayTeam)&&x.startDate)events.push({home:name(x.homeTeam),away:name(x.awayTeam),kickoff:x.startDate});
 }
 // Observed Sisal schema uses "type", competitor[] and a naive startDate.
 // Require the same URL, named home/away containers and visible date/time.
 if(x.type==='SportsEvent'&&x.url===location.origin+location.pathname&&Array.isArray(x.competitor)){
  const home=document.querySelector('[class*="PrematchSubheader_firstCompetitor__"]');
  const teams=[...document.querySelectorAll('[class*="PrematchSubheader_competitorName__"]')].filter(visible);
  const date=document.querySelector('[class*="PrematchSubheader_dateContainer__"]');
  const local=String(x.startDate||''), kickoff=romeTime(local);
  if(home&&teams.length===2&&teams[0]===home&&date&&kickoff){
   const h=text(home),a=text(teams[1]),shown=norm(text(date));
   // SportsEvent.name is a display title (Sisal uses "Atletico Bilbao" there
   // while competitor[] and the visible team both say "Athletic Bilbao").
   // Identity comes from the ordered competitors, same URL and visible date.
   if(x.competitor.length===2&&norm(String(x.competitor[0]?.name||''))===h&&norm(String(x.competitor[1]?.name||''))===a&&
      shown===local.slice(8,10)+'/'+local.slice(5,7)+' '+local.slice(11,16))
    events.push({home:h,away:a,kickoff});
  }
 }
 if(x['@graph'])visit(x['@graph']);
};
document.querySelectorAll('script[type="application/ld+json"]').forEach(s=>{try{visit(JSON.parse(s.textContent))}catch(e){}});
return {source_url:location.href, title:document.title, text:document.body.innerText,
 blocks,events,headings:all.filter(e=>/^H[1-3]$/.test(e.tagName)).map(text),
 times:[...document.querySelectorAll('time[datetime]')].filter(visible).map(e=>e.getAttribute('datetime')),
 links:[...document.querySelectorAll('a[href]')].filter(visible).map(e=>({url:e.href,text:norm(text(e))}))};
"""


def enrich_events(capture, candidates):
    """Fallback solo per titolo esatto Casa–Ospite e un unico <time> esplicito."""
    if capture.get('events'):
        return
    times = set(capture.get('times', []))
    if len(times) != 1:
        return
    headings = set(map(normal, capture.get('headings', [])))
    events = {}
    for r in candidates:
        if normal(r['home'] + ' - ' + r['away']) in headings:
            events[(r['home'], r['away'])] = {'home': r['home'], 'away': r['away'], 'kickoff': next(iter(times))}
    capture['events'] = list(events.values())


def discovered_links(capture, candidates, league_pages=False):
    matches = {(normal(r['home']), normal(r['away'])) for r in candidates}
    names = {normal(LEAGUES[r['league']]) for r in candidates if r['league'] in LEAGUES}
    names |= {'la liga'} if 'liga' in names else set()
    out = set()
    for link in capture.get('links', []):
        if not public_url(link.get('url', '')):
            continue
        label = ' ' + normal(link.get('text', '')) + ' '
        paired = any(' ' + h + ' ' in label and ' ' + a + ' ' in label for h, a in matches)
        if (league_pages and normal(label) in names) or (not league_pages and paired):
            out.add(link['url'])
    return sorted(out)


class PublicBrowser:
    def __init__(self, driver_path=None, timeout=25, headed=False):
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        options = webdriver.ChromeOptions()
        if not headed:
            options.add_argument('--headless=new')
        for arg in ('--disable-gpu', '--no-first-run', '--no-default-browser-check', '--window-size=1440,1080'):
            options.add_argument(arg)
        options.page_load_strategy = 'eager'
        # Driver supplied explicitly for reproducibility; otherwise Selenium Manager resolves it.
        service = Service(driver_path, service_args=['--disable-build-check']) if driver_path else Service()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(timeout)
        self.driver.set_script_timeout(timeout)

    def close(self):
        self.driver.quit()

    def read(self, url, evidence_dir):
        from selenium.webdriver.support.ui import WebDriverWait
        if not public_url(url):
            raise ValueError('URL non ammesso')
        b = self.driver
        b.get(url)
        WebDriverWait(b, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        for e in b.find_elements('css selector', '#onetrust-reject-all-handler'):
            if e.is_displayed():
                e.click()
        # Only navigation tabs and collapsed market headers, never outcome buttons.
        for e in b.find_elements('css selector', '[role="tab"],button'):
            if e.is_displayed() and e.text.strip().lower() in ('statistiche', 'stats match'):
                e.click()
                break
        for e in b.find_elements('css selector', '[aria-expanded="false"]'):
            if e.is_displayed() and market(e.text):
                e.click()
        capture = b.execute_script(DOM_SCRIPT)
        capture['observed_at'] = datetime.now(timezone.utc).isoformat()
        errors = ('ERR_HTTP', 'ERR_CONNECTION', 'ERR_NAME_NOT_RESOLVED', 'Access Denied', 'Verify you are human')
        capture['blocked'] = any(x.lower() in capture['text'].lower() for x in errors) or not public_url(capture['source_url'])
        if capture['blocked']:
            capture['blocked_reason'] = next((x for x in errors if x.lower() in capture['text'].lower()), 'Pagina non pubblica o non accessibile')
        evidence_dir.mkdir(parents=True, exist_ok=True)
        b.save_screenshot(str(evidence_dir / 'page.png'))
        return capture
