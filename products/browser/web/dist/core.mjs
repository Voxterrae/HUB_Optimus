const HOSTS=Object.freeze({es:'es.wikipedia.org',ca:'ca.wikipedia.org',en:'en.wikipedia.org',de:'de.wikipedia.org',fr:'fr.wikipedia.org',ru:'ru.wikipedia.org'});
const KEY='optimus.browser.pilot.v1';
const error=code=>Object.assign(new Error(code),{code});
const language=value=>Object.hasOwn(HOSTS,value)?value:'es';
const ignore=promise=>Promise.resolve(promise).catch(()=>{});

/** Only explicit calls issue requests. Cancellation settles even if transport ignores abort. */
export function createSearchController({fetchImpl=globalThis.fetch,timeoutMs=10000,maxBytes=1048576,setTimer=globalThis.setTimeout,clearTimer=globalThis.clearTimeout}={}) {
 let active=null;
 const limit=Number.isFinite(maxBytes)?Math.max(1,Math.min(1048576,maxBytes)):1048576;
 const deadline=Number.isFinite(timeoutMs)?Math.max(1,Math.min(10000,timeoutMs)):10000;
 function cancel(){active?.invalidate('cancelled');}
 async function search(query,locale){
  cancel();
  if(typeof query!=='string'||!query.trim())throw error('empty-query');
  if(query.length>500)throw error('query-too-long');
  const host=HOSTS[language(locale)],abort=new AbortController();
  let rejectStop,response,reader,timer,invalid=false;
  const stopped=new Promise((_,reject)=>{rejectStop=reject;});
  const token={invalidate(code){if(invalid)return;invalid=true;abort.abort();if(reader)ignore(reader.cancel());rejectStop(error(code));}};
  active=token;
  const check=()=>{if(invalid||active!==token)throw error('cancelled');};
  const url=new URL(`https://${host}/w/api.php`);
  url.search=new URLSearchParams({action:'query',list:'search',srsearch:query.trim(),srnamespace:'0',srlimit:'10',srprop:'snippet',format:'json',formatversion:'2',origin:'*'}).toString();
  timer=setTimer(()=>token.invalidate('timeout'),deadline);
  const work=(async()=>{
   response=await fetchImpl(url.href,{signal:abort.signal,credentials:'omit',redirect:'error',referrerPolicy:'no-referrer',cache:'no-store',headers:{Accept:'application/json'}});
   if(invalid){if(response.body)ignore(response.body.cancel());check();}
   check();
   if(!response.ok||response.redirected)throw error('http-error');
   if(!response.body||typeof response.body.getReader!=='function')throw error('invalid-response');
   const stated=Number(response.headers?.get('content-length'));
   if(Number.isFinite(stated)&&stated>limit){ignore(response.body.cancel());throw error('response-too-large');}
   reader=response.body.getReader();let bytes=0;const chunks=[];
   while(true){const {done,value}=await reader.read();check();if(done)break;bytes+=value.byteLength;if(bytes>limit){ignore(reader.cancel());throw error('response-too-large');}chunks.push(value);}
   check();const combined=new Uint8Array(bytes);let offset=0;for(const chunk of chunks){combined.set(chunk,offset);offset+=chunk.byteLength;}
   let payload;try{payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(combined));}catch{throw error('invalid-response');}
   if(payload?.error||!Array.isArray(payload?.query?.search))throw error('invalid-response');
   const rows=[];const seen=new Set();
   for(const row of payload.query.search){
    if(!row||!Number.isSafeInteger(row.pageid)||row.pageid<=0||typeof row.title!=='string'||!row.title.trim()||seen.has(row.pageid))continue;
    seen.add(row.pageid);rows.push({title:row.title.slice(0,500),snippet:plainSnippet(row.snippet),url:`https://${host}/?curid=${row.pageid}`,source:host});if(rows.length===10)break;
   }
   check();return rows;
  })();
  try{return await Promise.race([work,stopped]);}
  catch(cause){abort.abort();if(reader)ignore(reader.cancel());else if(response?.body)ignore(response.body.cancel());throw cause;}
  finally{clearTimer(timer);if(active===token)active=null;}
 }
 return {search,cancel};
}
function plainSnippet(value){
 if(typeof value!=='string')return '';
 return value.replace(/<[^>]*>/g,'').replace(/&(?:amp|lt|gt|quot|apos|#39|nbsp);/g,entity=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'",'&#39;':"'",'&nbsp;':' '})[entity]).slice(0,2000);
}
export function safeExternalUrl(input){
 if(typeof input!=='string'||input.length>2048||!/^https?:\/\//i.test(input)||/[\u0000-\u0020\u007f-\u009f\\]/u.test(input))return null;
 try{const url=new URL(input);if(!['https:','http:'].includes(url.protocol)||url.username||url.password||!url.hostname||url.href.length>2048)return null;return url.href;}catch{return null;}
}
function sanitizeState(input){
 const pick=(value,allowed,fallback)=>allowed.includes(value)?value:fallback;
 const saved=[];const seen=new Set();
 for(const item of Array.isArray(input.saved)?input.saved:[]){const url=safeExternalUrl(item?.url);if(!url||typeof item.title!=='string'||seen.has(url))continue;seen.add(url);saved.push({title:(item.title.replace(/[\u0000-\u001f\u007f-\u009f]/gu,'')||url).slice(0,120),url});if(saved.length===50)break;}
 return {remember:input.remember===true,language:language(input.language),speechLanguage:language(input.speechLanguage),mode:pick(input.mode,['simple','balanced','advanced'],'balanced'),fontSize:pick(input.fontSize,[18,22,26],18),theme:pick(input.theme,['light','dark'],'dark'),contrast:input.contrast===true,reducedMotion:input.reducedMotion===true,saved};
}
export function readDeviceState(storage){
 try{const raw=storage.getItem(KEY);if(raw===null)return {state:null,error:null};if(raw.length>200000)throw error('storage-corrupt');const value=JSON.parse(raw);if(!value||value.schemaVersion!==1||value.remember!==true)throw error('storage-corrupt');return {state:sanitizeState(value),error:null};}catch{return {state:null,error:'storage-unavailable'};}
}
export function writeDeviceState(storage,state){
 try{if(state?.remember!==true){storage.removeItem(KEY);return {ok:true,error:null};}storage.setItem(KEY,JSON.stringify({schemaVersion:1,...sanitizeState(state)}));return {ok:true,error:null};}catch{return {ok:false,error:'storage-unavailable'};}
}
export function clearDeviceState(storage){try{storage.removeItem(KEY);return {ok:true,error:null};}catch{return {ok:false,error:'storage-unavailable'};}}
