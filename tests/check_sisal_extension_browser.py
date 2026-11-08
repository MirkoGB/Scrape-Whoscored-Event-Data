"""Chrome MV3 integration: synthetic local site, never real bookmaker quotes."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import shutil
import threading
import time
import uuid

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

root=Path(__file__).resolve().parents[1]
source=root/'extensions/sisal-quotes'
test_extension=root/'reports/_extension_fixture_build'
test_extension.mkdir(exist_ok=True)
for path in source.iterdir():
    if path.is_file(): shutil.copyfile(path,test_extension/path.name)
# Only this isolated copy is allowed on the synthetic local server.
manifest=json.loads((test_extension/'manifest.json').read_text(encoding='utf-8'))
manifest['name']='Sisal — test sintetico'
manifest['content_scripts'][0]['matches']=['http://127.0.0.1/scommesse-matchpoint/evento/*']
manifest['host_permissions']=['http://127.0.0.1/*']  # Fixture-only permission: popup opened as a tab does not grant activeTab.
manifest['content_scripts'][0]['exclude_matches']=[]
(test_extension/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
core=(test_extension/'core.js').read_text(encoding='utf-8')
core=core.replace("u.protocol === 'https:' && ['www.sisal.it', 'sisal.it'].includes(u.hostname)","u.protocol === 'http:' && u.hostname === '127.0.0.1'")
core=core.replace("(!u.port || u.port === '443')",'true')
(test_extension/'core.js').write_text(core,encoding='utf-8')
kickoff=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
html=f'''<!doctype html><meta charset="utf-8"><title>Fixture sintetica — nessuna quota reale</title>
<header><p>Saldo personale non esportabile: SECRET-BALANCE</p></header>
<h1>Juventus – Atalanta</h1><time datetime="{kickoff}">Data test</time>
<section><h3>U/O TIRI TOTALI CASA</h3><button id="over" onclick="window.betClicks=(window.betClicks||0)+1">Over 8,5 1,80</button><button>Under 8,5 2,10</button></section>
<section><h3>U/O TIRI IN PORTA SQUADRA OSPITE</h3><button disabled>Over 3,5 1,90</button></section>'''
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data=html.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(data)
    def log_message(self,*_):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
downloads=root/'reports/_extension_downloads';downloads.mkdir(exist_ok=True)
opt=webdriver.ChromeOptions()
opt.binary_location=str(root/'reports/_chrome_for_extension_test/chrome-win64/chrome.exe')
for arg in ('--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--window-size=900,1000'):
    opt.add_argument(arg)
opt.add_argument('--user-data-dir='+str(root/('reports/_chrome_extension_integration_'+uuid.uuid4().hex)))
opt.add_argument('--load-extension='+str(test_extension))
opt.add_experimental_option('prefs',{'download.default_directory':str(downloads),'download.prompt_for_download':False})
opt.set_capability('goog:loggingPrefs',{'browser':'ALL'})
b=webdriver.Chrome(service=Service(str(root/'reports/_chrome_for_extension_test/chromedriver-win64/chromedriver.exe')),options=opt)
wait=WebDriverWait(b,8)
try:
    b.get('chrome://extensions/')
    ext=b.execute_async_script("const cb=arguments[0];chrome.developerPrivate.getExtensionsInfo({},rows=>cb(rows.find(e=>e.name==='Sisal — test sintetico')))")
    assert ext and ext['state']=='ENABLED'
    b.get('chrome-extension://'+ext['id']+'/popup.html')
    b.execute_async_script("const cb=arguments[0];chrome.storage.local.set({captures:[],enabled:true}).then(cb)")
    b.get(f'http://127.0.0.1:{server.server_port}/scommesse-matchpoint/evento/calcio/serie-a/fixture')
    fixture_handle=b.current_window_handle
    b.switch_to.new_window('tab')
    popup_handle=b.current_window_handle
    b.get('chrome-extension://'+ext['id']+'/popup.html')
    def captures():
        return b.execute_async_script("const cb=arguments[0];chrome.storage.local.get({captures:[]}).then(x=>cb(x.captures))")
    wait.until(lambda _:len(captures())==1)
    saved=captures()[0]
    assert len(saved['blocks'])==2
    assert saved['blocks'][1]['outcomes'][0]['disabled'] is True
    assert 'SECRET-BALANCE' not in json.dumps(saved)
    # Opening popup.html in a tab is not the toolbar popup. Point its active-tab lookup
    # to the fixture; all content/background messages and storage remain real Chrome APIs.
    b.execute_async_script("const cb=arguments[0];chrome.tabs.query({}).then(t=>{const page=t.find(x=>!x.active);chrome.tabs.query=async()=>[page];cb(page.id)})")
    b.find_element('id','read').click()
    wait.until(lambda _:'2 mercati leggibili' in b.find_element('id','status').text)
    assert '1,80' in b.find_element('id','preview').text
    b.save_screenshot(str(root/'reports/estensione_sisal_popup_test.png'))
    b.switch_to.window(fixture_handle)
    b.execute_script("document.getElementById('over').textContent='Over 8,5 1,95'")
    assert b.execute_script('return window.betClicks||0')==0
    b.switch_to.window(popup_handle)
    wait.until(lambda _:'1,95' in json.dumps(captures()))
    b.find_element('id','enabled').click()
    b.switch_to.window(fixture_handle)
    b.execute_script("document.getElementById('over').textContent='Over 8,5 2,05'")
    b.switch_to.window(popup_handle)
    time.sleep(3)
    assert '2,05' not in json.dumps(captures())
    b.find_element('id','enabled').click()
    wait.until(lambda _:'2,05' in json.dumps(captures()))
    # A manual read must save even while automatic collection is paused.
    b.find_element('id','enabled').click()
    b.switch_to.window(fixture_handle)
    b.execute_script("document.getElementById('over').textContent='Over 8,5 2,11'")
    b.switch_to.window(popup_handle)
    b.find_element('id','read').click()
    wait.until(lambda _:'2,11' in json.dumps(captures()))
    assert not b.find_element('id','enabled').is_selected()
    # No static content script on this route: reproduce an already-open tab.
    b.switch_to.window(fixture_handle)
    b.get(f'http://127.0.0.1:{server.server_port}/scommesse-matchpoint')
    b.switch_to.window(popup_handle)
    b.execute_async_script("const cb=arguments[0];chrome.tabs.query({}).then(t=>chrome.tabs.get(t[0].id)).then(t=>{chrome.tabs.query=async()=>[t];cb(t.id)})")
    b.find_element('id','read').click()
    wait.until(lambda _:len(captures())==2)
    assert 'Pagina salvata' in b.find_element('id','status').text
    assert '2 pagine' in b.find_element('id','count').text
    # Reconnecting twice still updates the same page, without duplicate entries.
    b.find_element('id','read').click()
    wait.until(lambda _:'Pagina salvata' in b.find_element('id','status').text)
    assert len(captures())==2
    # Same-document navigation, as used by Sisal when selecting another event.
    b.switch_to.window(fixture_handle)
    b.execute_script("history.pushState({},'', '/scommesse-matchpoint/evento/calcio/serie-a/second-fixture')")
    b.switch_to.window(popup_handle)
    b.execute_async_script("const cb=arguments[0];chrome.tabs.query({}).then(t=>chrome.tabs.get(t[0].id)).then(t=>{chrome.tabs.query=async()=>[t];cb(t.id)})")
    b.find_element('id','read').click()
    time.sleep(1)
    print('SPA STATUS:',b.find_element('id','status').text,flush=True)
    wait.until(lambda _:len(captures())==3)
    prior=set(downloads.glob('*.json'))
    b.find_element('id','export').click()
    wait.until(lambda _:len(set(downloads.glob('*.json'))-prior)==1)
    file=next(iter(set(downloads.glob('*.json'))-prior))
    bundle=json.loads(file.read_text(encoding='utf-8'))
    assert bundle['schema']=='sisal-chrome-captures'
    assert len(bundle['captures'])==3
    assert 'SECRET-BALANCE' not in file.read_text(encoding='utf-8')
    b.find_element('id','clear').click()
    time.sleep(1)
    print('CLEAR FEEDBACK', b.find_element('id','feedback').text, b.find_element('id','status').text)
    wait.until(lambda _:not captures())
    assert not b.find_element('id','enabled').is_selected()
    assert not [e for e in b.get_log('browser') if e['level']=='SEVERE']
    print('PASS: late attachment, manual save while paused, repeated reconnect, installed MV3 extension, auto capture, mutation, suspended prices, pause/resume, JSON export, clearing, private text excluded, no bet clicks.')
finally:
    b.quit();server.shutdown();server.server_close()
