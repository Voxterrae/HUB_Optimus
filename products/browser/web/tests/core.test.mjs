import test from 'node:test';
import assert from 'node:assert/strict';
import {createSearchController,safeExternalUrl,readDeviceState,writeDeviceState,clearDeviceState} from '../dist/core.mjs';
const sample = {query:{search:[{pageid:12,title:'<img onerror=alert(1)>',snippet:'A <span class="searchmatch">real</span> &amp; useful article'}]}};
const reply = (value=sample) => new Response(JSON.stringify(value),{headers:{'content-type':'application/json'}});
const deferred = () => {let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const memory = () => {const data=new Map();return {data,getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};};

test('explicit search uses one fixed locale endpoint and privacy request options', async()=>{
 let request;const ctl=createSearchController({fetchImpl:async(...args)=>{request=args;return reply();}});
 const rows=await ctl.search('  café & tea  ','ca');const u=new URL(request[0]);
 assert.equal(u.hostname,'ca.wikipedia.org');assert.equal(u.pathname,'/w/api.php');assert.equal(u.searchParams.get('srsearch'),'café & tea');assert.equal(u.searchParams.get('srlimit'),'10');
 for(const [key,value] of Object.entries({credentials:'omit',redirect:'error',referrerPolicy:'no-referrer',cache:'no-store'})) assert.equal(request[1][key],value);
 assert.equal(rows[0].url,'https://ca.wikipedia.org/?curid=12');assert.equal(rows[0].title,'<img onerror=alert(1)>');assert.equal(rows[0].snippet,'A real & useful article');
});
test('query validates UTF16 bound and unknown language uses Spanish without fetching invalid input',async()=>{
 let calls=0;const ctl=createSearchController({fetchImpl:async()=>{calls++;return reply();}});
 await assert.rejects(ctl.search(' ','es'),{code:'empty-query'});await assert.rejects(ctl.search('x'.repeat(501),'es'),{code:'query-too-long'});assert.equal(calls,0);
 await ctl.search('x'.repeat(500),'https://evil.test');assert.equal(calls,1);
});
test('at most ten valid positive page IDs become destinations; malformed rows stay inert',async()=>{
 const bad=[{pageid:-1,title:'bad'},{pageid:'3',title:'bad'},{pageid:1.2,title:'bad'},{pageid:2,title:{}},null];
 const good=Array.from({length:14},(_,i)=>({pageid:i+1,title:'Article',snippet:'<script>alert(1)</script>'}));
 const ctl=createSearchController({fetchImpl:async()=>reply({query:{search:[...bad,...good]}})});const rows=await ctl.search('a','de');
 assert.equal(rows.length,10);assert.equal(rows[0].url,'https://de.wikipedia.org/?curid=1');assert.equal(rows[0].snippet,'alert(1)');
});
test('malformed payload, HTTP failure, redirects and unavailable streaming body reject',async()=>{
 for(const response of [reply({}),reply({error:{code:'bad'}}),new Response('{'),new Response('{}',{status:500}),{ok:true,redirected:true,body:new ReadableStream()}, {ok:true,redirected:false,body:null}]){
  const ctl=createSearchController({fetchImpl:async()=>response});await assert.rejects(ctl.search('a','en'));
 }
});
test('real byte stream is bounded even without or with dishonest content-length',async()=>{
 for(const length of [null,'1']) {
  let cancelled=false;
  const body=new ReadableStream({start(c){c.enqueue(new Uint8Array(9));c.enqueue(new Uint8Array(9));},cancel(){cancelled=true;}});
  const ctl=createSearchController({maxBytes:16,fetchImpl:async()=>new Response(body,{headers:length?{'content-length':length}:{}})});
  await assert.rejects(ctl.search('a','en'),{code:'response-too-large'});assert.equal(cancelled,true);
 }
});
test('cancellation settles and invalidates a fetch that ignores AbortSignal',async()=>{
 const waiting=deferred();const ctl=createSearchController({fetchImpl:()=>waiting.promise});const pending=ctl.search('old','en');ctl.cancel();
 await assert.rejects(pending,{code:'cancelled'});waiting.resolve(reply());
});
test('superseded noncooperative response body cannot deliver stale results',async()=>{
 let streamControl;const body=new ReadableStream({start(c){streamControl=c;},cancel(){}});
 let calls=0;const ctl=createSearchController({fetchImpl:async()=>++calls===1?new Response(body):reply()});const old=ctl.search('old','es');
 await new Promise(r=>setImmediate(r));const current=ctl.search('new','fr');
 await assert.rejects(old,{code:'cancelled'});assert.equal((await current)[0].source,'fr.wikipedia.org');
 try{streamControl.enqueue(new TextEncoder().encode(JSON.stringify(sample)));streamControl.close();}catch{}
});
test('deadline covers an endlessly pending stream, independently of AbortSignal cooperation',async()=>{
 let trigger;const ctl=createSearchController({fetchImpl:async()=>new Response(new ReadableStream()),setTimer:fn=>{trigger=fn;return 1;},clearTimer(){}});
 const pending=ctl.search('a','en');await new Promise(r=>setImmediate(r));trigger();await assert.rejects(pending,{code:'timeout'});
});
test('URL sanitizer permits only absolute HTTP(S), without credentials, controls, backslashes or overlong values',()=>{
 assert.equal(safeExternalUrl('https://example.org/a?q=x'),'https://example.org/a?q=x');assert.equal(safeExternalUrl('http://example.org'),'http://example.org/');
 for(const value of ['javascript:alert(1)','data:text/html,x','//example.org','https://user:pass@example.org','https://example.org/\\evil','https://example.org/\nfoo','https://example.org/\u007ffoo','https://example.org/'+ 'a'.repeat(2048),{},null])assert.equal(safeExternalUrl(value),null);
});
test('persistence requires opt-in and only stores sanitized schema fields with 50 short saved links',()=>{
 const s=memory();assert.equal(writeDeviceState(s,{remember:false,query:'secret'}).ok,true);assert.equal(s.data.size,0);
 const state={remember:true,language:'fr',speechLanguage:'de',mode:'advanced',fontSize:22,theme:'light',contrast:true,reducedMotion:true,query:'secret',results:['private'],saved:Array.from({length:60},(_,i)=>({title:'a'.repeat(150),url:`https://example.org/${i}`,transcript:'secret'}))};
 assert.equal(writeDeviceState(s,state).ok,true);assert.equal(s.data.size,1);const json=JSON.parse(s.data.get('optimus.browser.pilot.v1'));assert.equal(json.schemaVersion,1);assert.equal(json.saved.length,50);assert.equal(json.saved[0].title.length,120);assert.equal(JSON.stringify(json).includes('secret'),false);
 assert.equal(readDeviceState(s).state.language,'fr');assert.equal(readDeviceState(s).state.speechLanguage,'de');
 s.setItem('unrelated','retain');assert.equal(clearDeviceState(s).ok,true);assert.equal(s.getItem('unrelated'),'retain');
});
test('corrupt, unsupported, hostile and denied storage safely report fallback',()=>{
 const s=memory();for(const raw of ['{','null','{"schemaVersion":2,"remember":true}']){s.setItem('optimus.browser.pilot.v1',raw);assert.ok(readDeviceState(s).error);assert.equal(readDeviceState(s).state,null);}
 s.setItem('optimus.browser.pilot.v1',JSON.stringify({schemaVersion:1,remember:true,saved:[{title:'evil',url:'javascript:alert(1)'}],fontSize:1,theme:'bad'}));assert.deepEqual(readDeviceState(s).state.saved,[]);assert.equal(readDeviceState(s).state.fontSize,18);
 const denied={getItem(){throw Error('denied')},setItem(){throw Error('denied')},removeItem(){throw Error('denied')}};assert.ok(readDeviceState(denied).error);assert.equal(writeDeviceState(denied,{remember:true}).ok,false);assert.equal(clearDeviceState(denied).ok,false);
});
test('a default controller never emits a request above the immutable host list',async()=>{
 for(const code of ['es','ca','en','de','fr','ru','evil.wikipedia.org']){
  let destination;const ctl=createSearchController({fetchImpl:async(url)=>{destination=new URL(url);return reply();}});
  await ctl.search('network',code);assert.ok(['es','ca','en','de','fr','ru'].some(x=>destination.host===`${x}.wikipedia.org`));
 }
});
test('advertised oversize body is cancelled before it is read',async()=>{
 let cancelled=false;const stream=new ReadableStream({cancel(){cancelled=true;}});
 const ctl=createSearchController({fetchImpl:async()=>new Response(stream,{headers:{'content-length':'1048577'}})});
 await assert.rejects(ctl.search('a','en'),{code:'response-too-large'});assert.equal(cancelled,true);
});
test('a late noncooperative fetch has its body cancelled and no result can apply after deadline',async()=>{
 let expire,cancelled=false;const transport=deferred();const ctl=createSearchController({fetchImpl:()=>transport.promise,setTimer:fn=>{expire=fn;return 1},clearTimer(){}});
 const pending=ctl.search('old','en');expire();await assert.rejects(pending,{code:'timeout'});
 transport.resolve(new Response(new ReadableStream({cancel(){cancelled=true;}})));await new Promise(r=>setImmediate(r));assert.equal(cancelled,true);
});
test('disabled remembering deletes an earlier snapshot without preserving query fields',()=>{
 const s=memory();writeDeviceState(s,{remember:true,language:'ca'});assert.equal(s.data.size,1);writeDeviceState(s,{remember:false,query:'private'});assert.equal(s.data.size,0);assert.deepEqual(readDeviceState(s),{state:null,error:null});
});
test('actual response bytes enforce the default 1MiB limit without a size header',async()=>{
 let cancelled=false;const body=new ReadableStream({start(c){c.enqueue(new Uint8Array(700000));c.enqueue(new Uint8Array(700000));},cancel(){cancelled=true;}});
 const ctl=createSearchController({maxBytes:5000000,fetchImpl:async()=>new Response(body)});await assert.rejects(ctl.search('a','en'),{code:'response-too-large'});assert.equal(cancelled,true);
});
test('timeout configuration cannot extend the ten second request deadline',async()=>{
 let observed;const ctl=createSearchController({timeoutMs:60000,setTimer:(fn,ms)=>{observed=ms;return 1},clearTimer(){},fetchImpl:async()=>reply()});await ctl.search('a','en');assert.equal(observed,10000);
});
test('fallback saved titles obey the 120 UTF16 bound when reading and writing device state',()=>{
 const url=`https://example.org/${'a'.repeat(220)}`;
 for(const title of ['', '\u0000\u001f\u007f\u009f']){
  const s=memory();assert.equal(writeDeviceState(s,{remember:true,saved:[{title,url}]}).ok,true);
  const written=JSON.parse(s.getItem('optimus.browser.pilot.v1'));
  assert.equal(written.saved[0].title,url.slice(0,120));assert.equal(written.saved[0].title.length,120);
  s.setItem('optimus.browser.pilot.v1',JSON.stringify({schemaVersion:1,remember:true,saved:[{title,url}]}));
  assert.equal(readDeviceState(s).state.saved[0].title,url.slice(0,120));
 }
});
for(const scenario of [
 {name:'HTTP 503',status:503,code:'http-error'},
 {name:'redirected response',redirected:true,code:'http-error'},
 {name:'advertised oversize',headers:{'content-length':'1048577'},code:'response-too-large'},
 {name:'missing body',withoutBody:true,code:'invalid-response'},
])test(`rejected ${scenario.name} aborts transport and cancels any real response body before settling`,async()=>{
 let bodyCancelled=false,signal;
 const stream=scenario.withoutBody?null:new ReadableStream({start(controller){controller.enqueue(new TextEncoder().encode('unread response'));},cancel(){bodyCancelled=true;}});
 const response=new Response(stream,{status:scenario.status??200,headers:scenario.headers});
 if(scenario.redirected)Object.defineProperty(response,'redirected',{value:true});
 const ctl=createSearchController({fetchImpl:async(_url,options)=>{signal=options.signal;return response;}});
 await assert.rejects(ctl.search('cleanup','en'),{code:scenario.code});
 assert.deepEqual({aborted:signal.aborted,bodyCancelled:stream?bodyCancelled:null},{aborted:true,bodyCancelled:stream?true:null},'settled rejection must release transport and its unread body');
 ctl.cancel();
});
test('opted-in device snapshots exclude unfinished saved-link draft text',()=>{
 const s=memory();const draft={title:'unfinished-private-title',url:'https://unfinished-private.example/'};
 assert.equal(writeDeviceState(s,{remember:true,language:'en',saved:[],savedDraft:draft}).ok,true);
 const raw=s.getItem('optimus.browser.pilot.v1');assert.equal(raw.includes('unfinished-private'),false);assert.equal(Object.hasOwn(JSON.parse(raw),'savedDraft'),false);
 assert.deepEqual(readDeviceState(s).state.saved,[]);
});
