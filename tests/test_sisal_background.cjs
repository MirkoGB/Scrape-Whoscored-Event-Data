const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const store=require('../extensions/sisal-quotes/core.js');
const url='https://www.sisal.it/scommesse-matchpoint/evento/calcio/serie-a/frosinone-como';
async function save({current=url,source=url,documentId='document-1',frameId=0}={}){
  let listener;const calls=[],writes=[];
  const chrome={runtime:{id:'extension',getURL:p=>'chrome-extension://extension/'+p,onMessage:{addListener:f=>listener=f}},
    tabs:{async sendMessage(id,msg,options){calls.push({id,msg,options});return {url:current};}},
    storage:{local:{async get(){return {enabled:true,captures:[]};},async set(s){writes.push(s);}}},
    action:{async setBadgeText(){},async setBadgeBackgroundColor(){}}};
  vm.runInNewContext(fs.readFileSync('extensions/sisal-quotes/background.js','utf8'),{chrome,SisalStore:store,URL,importScripts(){}});
  const response=await new Promise(resolve=>listener({type:'sisal.capture',capture:{source_url:source,
    observed_at:new Date().toISOString(),blocks:[],events:[]}},
    {id:'extension',frameId,documentId,tab:{id:42},url:'https://www.sisal.it/scommesse-matchpoint/sport/calcio'},resolve));
  return {response,calls,writes};
}
test('SPA capture uses the same live document URL, not the stale sender URL',async()=>{
  const r=await save();assert.equal(r.response.ok,true);assert.equal(r.writes[0].captures[0].source_url,url);
  assert.equal(r.calls[0].options.documentId,'document-1');assert.equal(r.calls[0].msg.type,'sisal.location');
});
test('navigation during capture cannot save the previous game under the new URL',async()=>{
  const r=await save({current:url+'/other'});assert.equal(r.response.ok,false);assert.equal(r.writes.length,0);
});
test('untrusted origin, missing document identity and subframes are rejected',async()=>{
  for(const options of [{current:'https://evil.test/x'},{documentId:null},{frameId:1}]){
    const r=await save(options);assert.equal(r.response.ok,false);assert.equal(r.writes.length,0);
  }
});
