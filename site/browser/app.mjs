import {LANGUAGES,normalizeLanguage,t} from './i18n.mjs';
import {VoiceController} from './voice.mjs';
import {createSearchController,safeExternalUrl,readDeviceState,writeDeviceState,clearDeviceState} from './core.mjs';

const defaults={remember:false,language:'es',speechLanguage:'es',mode:'balanced',fontSize:18,theme:'dark',contrast:false,reducedMotion:false,saved:[]};
let storage;try{storage=window.localStorage;}catch{storage={getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}};}
const loaded=readDeviceState(storage);
const state={...defaults,...loaded.state};
// Unfinished form text belongs to this page session, never the persisted preferences.
const savedDraft={title:'',url:''};
const routes=['home','saved','guide','settings'];
const routeFromHash=()=>routes.includes(location.hash.slice(1))?location.hash.slice(1):'home';
let route=routeFromHash(),query='',results=[],busy=false,searchMessage='',notice='',storageError=!!loaded.error,voiceMessage='voice.idle',rate=1,revision=0;
const search=createSearchController();const voice=new VoiceController();
const root=document.getElementById('app');
const tr=(key,params)=>t(state.language,key,params);
function node(tag,text,attrs={}){const element=document.createElement(tag);if(text!==undefined&&text!==null)element.textContent=text;for(const [key,value] of Object.entries(attrs)){if(key==='class')element.className=value;else element.setAttribute(key,String(value));}return element;}
function append(parent,...children){for(const child of children)if(child)parent.append(child);return parent;}
function copy(tag,key,attrs={},params){return node(tag,tr(key,params),attrs);}
function button(key,handler,attrs={}){const b=copy('button',key,{type:'button',...attrs});b.addEventListener('click',handler);return b;}
function persist(){if(!state.remember)return;if(!writeDeviceState(storage,state).ok){state.remember=false;storageError=true;}}
function invalidate(){revision++;search.cancel();voice.stop();busy=false;voiceMessage='voice.idle';}
function setting(key,value){
 if(key==='language'||key==='speechLanguage'){invalidate();results=[];searchMessage='';}
 state[key]=value;persist();render();
}
function select(key,value,options,id,change){
 const wrap=node('div',null,{class:'field'}),label=copy('label',key,{for:id}),control=node('select',null,{id});
 for(const option of options){const item=node('option',option.label,{value:option.value});item.selected=String(option.value)===String(value);control.append(item);}
 control.addEventListener('change',()=>change(control.value));return append(wrap,label,control);
}
const languageOptions=()=>LANGUAGES.map(x=>({value:x.code,label:x.name}));
const speechLocale=()=>LANGUAGES.find(x=>x.code===state.speechLanguage).locale;
function externalLink(title,url){const safe=safeExternalUrl(url);if(!safe)return node('span',title);const a=node('a',title,{href:safe,target:'_blank',rel:'noopener noreferrer',referrerpolicy:'no-referrer'});a.append(copy('span','accessibility.newTab',{class:'sr-only'}));return a;}
function navigate(next){if(next===route)return;location.hash=next;}
window.addEventListener('hashchange',()=>{invalidate();route=routeFromHash();results=[];searchMessage='';notice='';render({heading:true});window.scrollTo({top:0,behavior:'instant'});});
window.addEventListener('pagehide',()=>{const wasBusy=busy;invalidate();if(wasBusy)searchMessage='search.cancelled';});
window.addEventListener('pageshow',event=>{if(event.persisted)render();});
document.addEventListener('visibilitychange',()=>{if(document.hidden){invalidate();searchMessage='';render();}});
function navigation(className){
 const nav=node('nav',null,{class:className,'aria-label':tr('accessibility.navigation')});
 const symbols={home:'⌂',saved:'◇',guide:'✧',settings:'⚙'};
 for(const page of routes){const a=node('a',null,{href:`#${page}`});if(page===route)a.setAttribute('aria-current','page');append(a,node('span',symbols[page],{'aria-hidden':'true',class:'nav-symbol'}),copy('span',`nav.${page}`));nav.append(a);}return nav;
}
function render({heading=false}={}){
 const focused=document.activeElement?.id;const selection=document.activeElement instanceof HTMLInputElement?[document.activeElement.selectionStart,document.activeElement.selectionEnd]:null;
 document.documentElement.lang=state.language;document.documentElement.style.fontSize=`${state.fontSize}px`;document.title=`${tr(`nav.${route}`)} · ${tr('app.name')}`;
 document.body.dataset.theme=state.theme;document.body.dataset.mode=state.mode;document.body.classList.toggle('contrast',state.contrast);document.body.classList.toggle('quiet',state.reducedMotion);
 const skip=copy('a','accessibility.skip',{href:'#main',class:'skip'});skip.addEventListener('click',event=>{event.preventDefault();document.getElementById('main').focus();});
 const sidebar=node('aside',null,{class:'sidebar'}),brand=node('a',null,{href:'#home',class:'brand','aria-label':tr('app.name')});
 append(brand,node('img',null,{src:'./assets/optimus.svg',alt:'',width:44,height:44}),copy('span','app.name'));
 append(sidebar,brand,navigation('side-nav'),append(node('div',null,{class:'sidebar-note'}),node('img',null,{src:'./assets/hub-optimus-operator-icon.svg',alt:'',width:40,height:40}),copy('p','guide.intro')));
 const workspace=node('div',null,{class:'workspace'}),header=node('header',null,{class:'topbar'});
 append(header,copy('a','app.name',{href:'#home',class:'mobile-brand'}),copy('span','app.tagline',{class:'tagline'}),select('settings.language',state.language,languageOptions(),'top-language',value=>setting('language',normalizeLanguage(value))));
 const main=node('main',null,{id:'main',tabindex:'-1','aria-label':tr('accessibility.main')});
 if(storageError)main.append(copy('p','settings.storageError',{role:'status',class:'notice warning'}));
 if(notice)main.append(copy('p',notice,{role:'status',class:'notice'},{max:50}));
 const content=node('div',null,{class:'page'});
 if(route==='home')renderHome(content);if(route==='saved')renderSaved(content);if(route==='guide')renderGuide(content);if(route==='settings')renderSettings(content);
 append(main,content,append(node('footer',null,{class:'footer'}),copy('span','app.name'),button('privacy.title',openPrivacy,{class:'text-button',id:'privacy-open'})));
 append(workspace,header,main);root.replaceChildren(skip,sidebar,workspace,navigation('bottom-nav'));
 if(heading)document.getElementById('page-heading')?.focus();else if(focused){const replacement=document.getElementById(focused);replacement?.focus({preventScroll:true});if(selection&&replacement instanceof HTMLInputElement&&replacement.type!=='range'&&replacement.type!=='checkbox')try{replacement.setSelectionRange(...selection);}catch{}}
}
function heading(parent,title,intro){append(parent,copy('p','app.tagline',{class:'eyebrow'}),copy('h1',title,{id:'page-heading',tabindex:'-1'}),copy('p',intro,{class:'intro'}));}
function renderHome(parent){
 const layout=node('div',null,{class:'home-layout'}),primary=node('section',null,{class:'primary'});heading(primary,'home.title','home.intro');
 const form=node('form',null,{class:'search-form'}),label=copy('label','search.label',{for:'query'}),disclosure=copy('p','search.notice',{id:'search-disclosure',class:'muted'});
 const row=node('div',null,{class:'search-row'}),input=node('input',null,{type:'search',id:'query',name:'query',maxlength:500,autocomplete:'off','aria-describedby':'search-disclosure',placeholder:tr('search.placeholder')});input.value=query;
 input.addEventListener('input',()=>{query=input.value;const wasBusy=busy;invalidate();results=[];searchMessage=wasBusy?'search.cancelled':'';document.getElementById('search-status').textContent=searchMessage?tr(searchMessage):'';document.getElementById('result-list')?.replaceChildren();document.getElementById('result-list')?.setAttribute('aria-busy','false');document.getElementById('search-cancel').hidden=true;document.getElementById('result-heading')?.remove();});
 const submit=copy('button','search.submit',{type:'submit',id:'search-submit',class:'primary-button'});append(row,input,submit);
 const cancel=button('action.cancel',()=>{invalidate();searchMessage='search.cancelled';render();},{id:'search-cancel'});cancel.hidden=!busy;
 const status=copy('p',searchMessage||'search.results',{id:'search-status',role:'status','aria-live':'polite',class:'search-status'},{max:500,count:results.length});if(!searchMessage)status.textContent='';
 form.addEventListener('submit',event=>{event.preventDefault();submitSearch();});append(form,label,disclosure,row,cancel,status);primary.append(form);
 if(results.length)primary.append(copy('h2','search.resultCount',{id:'result-heading'},{count:results.length}));
 const resultList=node('div',null,{id:'result-list',class:'result-list','aria-busy':busy});for(const result of results)resultList.append(resultCard(result));primary.append(resultList);
 const quick=node('section',null,{class:'quick-links'});quick.append(copy('h2','nav.saved'));
 if(!state.saved.length)quick.append(copy('p','saved.empty',{class:'muted'}));else for(const item of state.saved.slice(0,state.mode==='simple'?2:3))quick.append(externalLink(item.title,item.url));
 quick.append(button('nav.saved',()=>navigate('saved'),{class:'text-button'}));primary.append(quick);
 if(state.mode!=='simple')primary.append(append(node('section',null,{class:'adapt-card'}),copy('h2','settings.title'),copy('p','settings.intro'),button('nav.settings',()=>navigate('settings'),{class:'text-button'})));
 append(layout,primary,voicePanel());parent.append(layout);
}
async function submitSearch(){
 invalidate();const own=revision;results=[];busy=true;searchMessage='search.loading';render();
 try{const rows=await search.search(query,state.language);if(own!==revision)return;results=rows;searchMessage=rows.length?'search.resultCount':'search.empty';}
 catch(err){if(own!==revision)return;searchMessage=({'empty-query':'search.noQuery','query-too-long':'search.queryTooLong',cancelled:'search.cancelled'})[err.code]||'search.error';}
 finally{if(own===revision){busy=false;render();}}
}
function resultCard(result){
 const card=node('article',null,{class:'result-card'});append(card,copy('p','search.source',{class:'source'}),append(node('h3'),externalLink(result.title,result.url)),node('p',result.snippet,{class:'muted'}));
 const saved=state.saved.some(x=>x.url===result.url),b=button(saved?'search.saved':'search.save',()=>{if(saved)return;addSaved(result.title,result.url);render();},{id:`save-${new URL(result.url).searchParams.get('curid')}`,'aria-label':`${tr(saved?'search.saved':'search.save')}: ${result.title}`});b.setAttribute('aria-disabled',String(saved));card.append(b);return card;
}
function addSaved(title,rawUrl){
 const url=safeExternalUrl(rawUrl);if(!url){notice='saved.invalidUrl';return false;}if(state.saved.some(x=>x.url===url)){notice='search.saved';return true;}if(state.saved.length>=50){notice='saved.limit';return false;}
 state.saved.push({title:(title.trim()||url).replace(/[\u0000-\u001f\u007f-\u009f]/gu,'').slice(0,120),url});persist();notice='search.saved';return true;
}
function renderSaved(parent){
 heading(parent,'saved.title','saved.intro');parent.append(copy('p','privacy.external',{class:'muted'}));
 const list=node('div',null,{class:'saved-list'});if(!state.saved.length)list.append(copy('p','saved.empty',{class:'empty'}));
 state.saved.forEach((item,index)=>{const card=node('article',null,{class:'saved-card'});append(card,externalLink(item.title,item.url),button('action.delete',()=>{state.saved.splice(index,1);persist();notice='saved.removed';render();const next=document.getElementById(`delete-${Math.min(index,state.saved.length-1)}`)||document.getElementById('add-title');next?.focus();},{id:`delete-${index}`,'aria-label':`${tr('action.delete')}: ${item.title}`}));list.append(card);});parent.append(list);
 const form=node('form',null,{class:'panel add-form'});append(form,copy('h2','saved.add'));
 for(const [id,key,type,max,field] of [['add-title','saved.linkTitle','text',120,'title'],['add-url','saved.linkUrl','url',2048,'url']]){const input=node('input',null,{id,type,maxlength:max,required:true,autocomplete:'off'});input.value=savedDraft[field];input.addEventListener('input',()=>{savedDraft[field]=input.value;});append(form,copy('label',key,{for:id}),input);}
 append(form,copy('button','saved.add',{type:'submit',class:'primary-button'}),copy('p','settings.savedLimit',{class:'muted'}));
 form.addEventListener('submit',event=>{event.preventDefault();const title=form.querySelector('#add-title').value,url=form.querySelector('#add-url').value;if(addSaved(title,url)){savedDraft.title='';savedDraft.url='';render();document.getElementById('add-title').focus();}else{let error=form.querySelector('[role="alert"]');if(!error){error=node('p',null,{role:'alert'});form.append(error);}error.textContent=tr(notice,{max:50});notice='';}});parent.append(form);
}
function renderGuide(parent){
 heading(parent,'guide.title','guide.intro');const grid=node('div',null,{class:'guide-grid'});
 for(const [title,paragraphs] of [['search.label',['guide.search','guide.offline']],['voice.title',['guide.voice','voice.dictationNotice']],['privacy.title',['privacy.storage','guide.browser','guide.devices']]]){const card=node('section',null,{class:'panel'});card.append(copy('h2',title));for(const key of paragraphs)card.append(copy('p',key,{class:'muted'}));grid.append(card);}parent.append(grid);
 parent.append(button('privacy.title',openPrivacy,{class:'primary-button',id:'guide-privacy-open'}));
}
function checkSetting(key){const wrap=node('label',null,{class:'check-field',for:`setting-${key}`}),input=node('input',null,{type:'checkbox',id:`setting-${key}`});input.checked=state[key];input.addEventListener('change',()=>{
 if(key==='remember'){state.remember=input.checked;if(input.checked)persist();else if(!clearDeviceState(storage).ok)storageError=true;render();}else setting(key,input.checked);
 });return append(wrap,input,copy('span',`settings.${key}`));}
function renderSettings(parent){
 heading(parent,'settings.title','settings.intro');const panel=node('section',null,{class:'settings-panel panel'});
 for(const [key,options] of [['language',languageOptions()],['speechLanguage',languageOptions()],['mode',['simple','balanced','advanced'].map(value=>({value,label:tr(`settings.${value}`)}))],['fontSize',[18,22,26].map(value=>({value,label:`${value} px`}))],['theme',['dark','light'].map(value=>({value,label:tr(`settings.${value}`)}))]])panel.append(select(`settings.${key}`,state[key],options,`setting-${key}`,value=>setting(key,key==='fontSize'?Number(value):value)));
 for(const key of ['contrast','reducedMotion','remember'])panel.append(checkSetting(key));panel.append(copy('p','privacy.storage',{class:'muted'}));
 panel.append(button('settings.clearData',()=>{invalidate();state.remember=false;state.saved=[];savedDraft.title='';savedDraft.url='';query='';results=[];notice='';searchMessage='';const outcome=clearDeviceState(storage);storageError=!outcome.ok;if(outcome.ok)notice='settings.dataCleared';render();},{class:'text-button',id:'clear-device-data'}));parent.append(panel);
}
const voiceKey=value=>({'permission-denied':'voice.permissionDenied','download-required':'voice.downloadRequired',available:'voice.idle',cancelled:'voice.idle',disposed:'voice.idle'})[value]||`voice.${value}`;
function voiceState(value){voiceMessage=voiceKey(value);const status=document.getElementById('voice-status');if(status)status.textContent=tr(voiceMessage);}
function voicePanel(){
 const panel=node('aside',null,{class:'voice-panel panel'});append(panel,node('img',null,{src:'./assets/hub-optimus-operator-icon.svg',alt:'',width:48,height:48}),copy('h2','voice.title'),copy('p','voice.localNotice',{class:'muted'}),select('settings.speechLanguage',state.speechLanguage,languageOptions(),'voice-language',value=>setting('speechLanguage',value)));
 const rateControl=node('input',null,{type:'range',id:'voice-rate',min:0.5,max:2,step:0.25});rateControl.value=rate;rateControl.addEventListener('input',()=>{rate=Number(rateControl.value);document.getElementById('rate-value').textContent=`${rate}×`;});append(panel,copy('label','voice.rate',{for:'voice-rate'}),rateControl,node('output',`${rate}×`,{id:'rate-value',for:'voice-rate'}));
 append(panel,button('voice.read',()=>{voice.stop();const result=voice.speak(['guide.intro','guide.search','guide.voice'].map(key=>t(state.speechLanguage,key)).join(' '),{lang:speechLocale(),rate,onState:voiceState});if(!result.started)voiceState(result.reason);},{id:'read-help',class:'voice-action'}),copy('p','voice.dictationNotice',{class:'muted'}),button('voice.dictate',async()=>{
 const wasBusy=busy;invalidate();results=[];searchMessage=wasBusy?'search.cancelled':'';const own=revision;render();const outcome=await voice.dictate({lang:speechLocale(),onState:voiceState,onText:text=>{if(own!==revision)return;query=String(text).slice(0,500);results=[];searchMessage='';voiceMessage='voice.transcriptReady';render();document.getElementById('query')?.focus();}});if(own===revision&&!outcome.started)voiceState(outcome.reason);
 },{id:'dictate',class:'voice-action'}),button('action.stop',()=>{voice.stop();voiceState('idle');},{id:'stop-voice'}),copy('p',voiceMessage,{id:'voice-status',role:'status','aria-live':'polite'}));
 return panel;
}
function openPrivacy(){
 const previous=document.activeElement,dialog=node('dialog',null,{class:'privacy-dialog','aria-labelledby':'privacy-heading'});dialog.append(copy('h2','privacy.title',{id:'privacy-heading'}));for(const key of ['privacy.search','privacy.storage','privacy.voice','privacy.external','privacy.scope'])dialog.append(copy('p',key));
 dialog.append(button('action.close',()=>dialog.close(),{class:'primary-button'}));dialog.addEventListener('close',()=>{dialog.remove();const target=(previous?.id&&document.getElementById(previous.id))||(previous?.isConnected?previous:null)||document.getElementById('page-heading');target?.focus();});document.body.append(dialog);dialog.showModal();
}
render();
