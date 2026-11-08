const test=require('node:test');
const assert=require('node:assert/strict');
const S=require('../extensions/sisal-quotes/core.js');
const url='https://www.sisal.it/scommesse-matchpoint/evento/calcio/serie-a/monza-sassuolo';
const now=Date.parse('2026-09-19T10:00:00Z');
const capture=()=>({source_url:url,observed_at:new Date(now).toISOString(),events:[],headings:[],times:[],
  blocks:[{label:'U/O TIRI TOTALI CASA',outcomes:[{text:'Over 8.5 1.8',disabled:false}]}]});

test('only Sisal public pages can send captures',()=>{
  assert.ok(S.publicUrl(url));
  assert.ok(S.publicUrl('https://www.sisal.it/scommesse-matchpoint'));
  assert.equal(S.publicUrl('https://www.sisal.it/scommesse-matchpoint-fake'),false);
  for(const other of ['https://evil.test/scommesse-matchpoint/evento','https://areaprivata.sisal.it/login',
    'https://www.sisal.it.evil.test/scommesse-matchpoint/test','http://www.sisal.it/scommesse-matchpoint/test',
    'https://www.sisal.it/scommesse-matchpoint/blog/test','https://user:pass@www.sisal.it/scommesse-matchpoint/test']){
    assert.equal(S.publicUrl(other),false);
    assert.throws(()=>S.cleanCapture(capture(),other,now));
  }
  assert.throws(()=>S.cleanCapture(capture(),url+'/other',now));
});
test('retains only market metadata and removes query parameters and extra fields',()=>{
  const raw={...capture(),source_url:url+'?tracking=123',text:'PRIVATE BALANCE',cookies:'SECRET',title:'PERSONAL',token:'SECRET'};
  const saved=S.cleanCapture(raw,url+'?tracking=123',now);
  assert.equal(saved.source_url,url);
  for(const key of ['text','cookies','title','token'])assert.equal(key in saved,false);
  assert.equal(saved.blocks[0].outcomes[0].disabled,false);
  assert.equal(saved.transport,'chrome_extension');
});
test('empty or suspended current page replaces earlier quotes instead of retaining them',()=>{
  const old=S.cleanCapture(capture(),url,now);
  const empty={...old,observed_at:new Date(now+1000).toISOString(),blocks:[]};
  assert.deepEqual(S.merge([old],empty),[empty]);
  const suspended={...old,observed_at:new Date(now+2000).toISOString(),blocks:[{label:'X',outcomes:[{text:'Over 8.5 1.8',disabled:true}]}]};
  assert.equal(S.merge([empty],suspended)[0].blocks[0].outcomes[0].disabled,true);
  assert.deepEqual(S.merge([suspended],old),[suspended]);
});
test('bounds archive size and rejects bad clocks',()=>{
  let rows=[];
  for(let i=0;i<80;i++)rows=S.merge(rows,{...capture(),source_url:url+'/'+i,observed_at:new Date(now+i).toISOString()});
  assert.equal(rows.length,50);
  assert.ok(rows[0].source_url.endsWith('/30'));
  assert.throws(()=>S.cleanCapture({...capture(),observed_at:'invalid'},url,now));
  assert.throws(()=>S.cleanCapture({...capture(),observed_at:new Date(now-61000).toISOString()},url,now));
  assert.throws(()=>S.cleanCapture({...capture(),observed_at:new Date(now+10000).toISOString()},url,now));
});
