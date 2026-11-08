const test=require('node:test');
const assert=require('node:assert/strict');
require('../extensions/sisal-quotes/core.js');
const {readTab}=require('../extensions/sisal-quotes/connection.js');
const tab={id:7,url:'https://www.sisal.it/scommesse-matchpoint/evento/calcio/serie-a/fiorentina-napoli'};

function api(reply={ok:true,capture:{blocks:[]}}){
  const calls=[];
  return {calls,scripting:{async executeScript(x){calls.push(['inject',x]);}},
    tabs:{async sendMessage(...args){calls.push(['read',...args]);return reply;}}};
}
test('explicit read reconnects the top frame before requesting a confirmed save',async()=>{
  const chrome=api();const result=await readTab(chrome,tab,true);
  assert.equal(result.ok,true);
  assert.deepEqual(chrome.calls,[['inject',{target:{tabId:7,frameIds:[0]},files:['core.js','reader.js','content.js']}],
    ['read',7,{type:'sisal.read',manual:true},{frameId:0}]]);
});
test('opening the popup does not inject automatically',async()=>{
  const chrome=api({ok:false,paused:true});
  assert.equal((await readTab(chrome,tab)).paused,true);
  assert.equal(chrome.calls.length,1);
  assert.equal(chrome.calls[0][0],'read');
});
test('unsupported pages never receive a script or message',async()=>{
  for(const url of ['https://evil.test/','chrome://extensions','https://www.sisal.it/login','https://www.sisal.it/scommesse-matchpoint/blog/a']){
    const chrome=api();await assert.rejects(readTab(chrome,{...tab,url},true),/Pagina non supportata/);
    assert.deepEqual(chrome.calls,[]);
  }
});
test('permission errors and missing readers remain distinguishable',async()=>{
  const chrome=api();chrome.scripting.executeScript=async()=>{throw Error('Cannot access contents of url');};
  await assert.rejects(readTab(chrome,tab,true),/Chrome non consente.*Cannot access contents/);
  assert.deepEqual(chrome.calls,[]);
  chrome.tabs.sendMessage=async()=>{throw Error('Receiving end does not exist.');};
  await assert.rejects(readTab(chrome,tab),/Lettore non collegato.*Receiving end/);
});
test('storage and parser failures are not reported as successful reads',async()=>{
  await assert.rejects(readTab(api({ok:false,error:'Storage quota exceeded'}),tab,true),/Storage quota exceeded/);
  const chrome=api();chrome.tabs.sendMessage=async()=>undefined;
  await assert.rejects(readTab(chrome,tab,true),/non ha confermato/);
});
