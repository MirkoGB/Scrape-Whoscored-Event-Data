from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
root=Path(__file__).resolve().parents[1]
options=webdriver.ChromeOptions()
options.binary_location=str(root/'reports/_chrome_for_extension_test/chrome-win64/chrome.exe')
options.add_argument('--headless=new');options.add_argument('--window-size=1440,1100')
options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
b=webdriver.Chrome(service=Service(str(root/'reports/_chrome_for_extension_test/chromedriver-win64/chromedriver.exe')),options=options)
try:
 b.get((root/'reports/analisi_2627_prestazioni.html').as_uri())
 b.execute_script("""
 const now=new Date(),future=new Date(now.getTime()+2*86400000),day=OverSuggestion.romeDay(future);
 const forecast=new Date(now.getTime()-86400000).toISOString(),train=OverSuggestion.romeDay(new Date(now.getTime()-2*86400000));
 const make=(id,p,line,odd)=>{const r={league:'ITA-serie-a',match_id:id,match_date:day,home:'TEST HOME '+id,away:'TEST AWAY '+id,p,line,target:'shots',scope:'team',side:'home',selection_id:id+'|'+line,published_at:forecast,training_through:train};return [r,{...r,run_id:'fixture',status:'matched',bookmaker:'Sisal',over_odds:odd,observed_at:new Date(now.getTime()-2000).toISOString(),recorded_at:new Date(now.getTime()-1000).toISOString(),kickoff:future.toISOString(),settlement_rule:'sisal_official_opta_fallback_90min_halfline'}]};
 const fixture=[make('A',.99,8.5,1.05),make('B',.95,8.5,1.08),make('B',.8,9.5,1.4),make('C',.7,8.5,1.5)];
 D.over.candidates=fixture.map(x=>x[0]);D.over.sisal={last_run:{id:'fixture',status:'collected',finished_at:now.toISOString()},observations:fixture.map(x=>x[1])};
 document.getElementById('suggest-size').value='1';runSuggestion();
 """)
 assert b.execute_script('return SUGGESTION.legs[0].line')==8.5
 assert b.execute_script('return SUGGESTION.legs[0].match_id')=='B'
 assert len(b.find_elements('css selector','#suggest-readable-matches details'))==3
 assert len(b.find_elements('css selector','#suggest-readable-matches tbody tr'))==4
 b.find_element('css selector','#suggest-readable-matches details summary').click()
 assert 'Esclusa dal suggeritore' in b.find_element('id','suggest-readable-matches').text
 b.find_element('id','suggest-play-well').click()
 assert b.execute_script('return SUGGESTION===null')
 assert not b.find_element('id','suggest-edge').get_attribute('disabled')
 assert 'scegli' in b.find_element('id','suggest-status').text.lower()
 assert len(b.find_elements('css selector','#suggest-readable-matches details'))==3
 b.find_element('id','suggest-edge').send_keys('5')
 b.find_element('id','suggest-run').click()
 assert b.execute_script('return SUGGESTION.legs[0].line')==9.5
 assert b.execute_script('return SUGGESTION.filters.minEdge')==.05
 assert '2 linee' in b.find_element('id','suggest-value-list').text
 before=b.execute_script('return SUGGESTION.legs.map(r=>r.selection_id)')
 # All seven columns sort by their underlying values in both directions.
 expected={'match':['B|9.5','C|8.5'],'p':['C|8.5','B|9.5'],
           'odds':['B|9.5','C|8.5'],'fairOdds':['B|9.5','C|8.5'],
           'probabilityGap':['C|8.5','B|9.5'],'expectedReturn':['C|8.5','B|9.5'],
           'stressReturn':['C|8.5','B|9.5']}
 for column,ascending in expected.items():
  for direction,order in [('ascending',ascending),('descending',ascending[::-1])]:
   b.find_element('css selector',f'#suggest-value-list button[data-sort="{column}"]').click()
   assert b.find_element('css selector',f'#suggest-value-list button[data-sort="{column}"]').find_element('xpath','..').get_attribute('aria-sort')==direction
   assert [r.get_attribute('data-selection-id') for r in b.find_elements('css selector','#suggest-value-list tbody tr')]==order
   assert b.execute_script('return SUGGESTION.legs.map(r=>r.selection_id)')==before
 assert len(b.find_elements('css selector','#suggest-readable-matches details[open]'))==1
 Select(b.find_element('id','suggest-size')).select_by_value('2');b.find_element('id','suggest-run').click()
 assert b.execute_script('return SUGGESTION.legs.length')==2
 assert b.execute_script('return SUGGESTION.legs.every(r=>r.quote.over_odds>1.05)')
 b.execute_script("document.getElementById('suggestion-lab').scrollIntoView()")
 b.save_screenshot(str(root/'reports/_giocare_bene_fixture.png'))
 b.find_element('id','suggest-edge').clear();b.find_element('id','suggest-edge').send_keys('20');b.find_element('id','suggest-run').click()
 assert b.execute_script('return SUGGESTION.status')=='insufficient'
 assert len(b.find_elements('css selector','#suggest-readable-matches details'))==3
 b.find_element('id','suggest-play-well').click()
 assert b.execute_script('return SUGGESTION.status')=='suggested'
 assert b.find_element('id','suggest-edge').get_attribute('disabled')
 # Inventory respects filters without requiring another coupon calculation.
 Select(b.find_element('id','suggest-market')).select_by_value('sot:team')
 assert not b.find_elements('css selector','#suggest-readable-matches details')
 assert 'Nessuna partita' in b.find_element('id','suggest-readable-matches').text
 Select(b.find_element('id','suggest-market')).select_by_value('all')
 assert len(b.find_elements('css selector','#suggest-readable-matches details'))==3
 Select(b.find_element('id','suggest-league')).select_by_value('ENG-premier-league')
 assert not b.find_elements('css selector','#suggest-readable-matches details')
 Select(b.find_element('id','suggest-league')).select_by_value('TUTTI')
 assert len(b.find_elements('css selector','#suggest-readable-matches details'))==3
 # Refresh removes stale quotes, including when there is no suggested coupon.
 b.execute_script("D.over.sisal.observations.forEach(q=>{q.observed_at=new Date(Date.now()-3601000).toISOString();q.recorded_at=q.observed_at;});refreshReadableMatches();")
 assert not b.find_elements('css selector','#suggest-readable-matches details')
 assert not [r for r in b.get_log('browser') if r['level']=='SEVERE']
 b.get((root/'reports/preparazione_over_2026-09-20.html').as_uri())
 b.find_element('id','play-well').click()
 assert 'Nessuna giocata' in b.find_element('id','coupon').text
 assert not [r for r in b.get_log('browser') if r['level']=='SEVERE']
 print('PASS: seven sortable columns, unchanged selections, grouped odds, excluded price label, filters, expansion persistence, quote expiry, value threshold, daily page; synthetic data only in browser memory.')
finally:b.quit()
