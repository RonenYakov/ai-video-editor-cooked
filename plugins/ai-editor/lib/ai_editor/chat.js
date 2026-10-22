// Claude chat panel for a project, plus the mic (local dictation) used by it and by any textarea.
//   CookedChat.mount(el,{slug,context,placeholder}) -> {send(text),focus(),destroy()}
//   CookedChat.dictateButton(textarea)  -> the mic button, placed after the textarea
// Uses the page's colour tokens (--panel --ink --t2 --t3 --line --soft ...), same as ask.js. Requests ride the page cookie.
(()=>{
if(typeof document==='undefined')return;
const css=`.cc,.cc-x{--c-panel:var(--panel,#fff);--c-ink:var(--ink,#0C0A09);--c-body:var(--t2,#57534E);--c-mute:var(--t3,#78716C);--c-faint:var(--t4,#A8A29E);
 --c-line:var(--line,#E7E5E4);--c-soft:var(--soft,#F5F5F4);--c-onink:var(--onink,#fff);--c-red:#DC2626}
.cc{display:flex;flex-direction:column;height:100%;min-height:0;background:var(--c-panel);color:var(--c-ink);font:14px/21px system-ui,-apple-system,"Segoe UI",sans-serif;text-align:left}
.cc *{box-sizing:border-box}
.cc-hd{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-bottom:1px solid var(--c-line);flex-shrink:0}
.cc-hd b{font-size:15px;font-weight:600;letter-spacing:-.01em}
.cc-btn{height:32px;margin:0;padding:0 12px;border:1px solid var(--c-line);border-radius:10px;background:none;color:var(--c-body);font:inherit;font-size:13px;cursor:pointer}
.cc-btn:hover,.cc-btn:focus-visible{border-color:var(--c-ink);color:var(--c-ink);outline:none}
.cc-btn:disabled{opacity:.4;cursor:default;border-color:var(--c-line);color:var(--c-body)}
.cc-msgs{flex:1;min-height:0;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:16px;scroll-behavior:auto}
.cc-empty{margin:auto;max-width:300px;text-align:center;color:var(--c-mute);font-size:14px;line-height:21px}
.cc-u{align-self:flex-end;max-width:85%;padding:9px 14px;border-radius:14px;background:var(--c-soft);white-space:pre-wrap;overflow-wrap:anywhere}
.cc-a{align-self:flex-start;max-width:100%;overflow-wrap:anywhere}
.cc-a p{margin:0 0 10px}.cc-a>*:last-child{margin-bottom:0}
.cc-a ul,.cc-a ol{margin:0 0 10px;padding-left:22px}.cc-a li{margin:2px 0}
.cc-a code{padding:1px 5px;border-radius:5px;background:var(--c-soft);font:12.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.cc-a pre{margin:0 0 10px;padding:12px 14px;border:1px solid var(--c-line);border-radius:12px;background:var(--c-soft);overflow-x:auto}
.cc-a pre code{padding:0;background:none;font-size:12.5px;line-height:19px}
.cc-a a{color:inherit;text-decoration:underline 1px;text-underline-offset:3px}
.cc-tool{align-self:flex-start;max-width:100%;padding:3px 10px;border:1px solid var(--c-line);border-radius:999px;color:var(--c-mute);font-size:12.5px;line-height:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cc-dots{align-self:flex-start;display:flex;gap:5px;padding:8px 2px}
.cc-dots i{width:6px;height:6px;border-radius:50%;background:var(--c-faint);animation:ccd 1.1s ease-in-out infinite}
.cc-dots i:nth-child(2){animation-delay:.15s}.cc-dots i:nth-child(3){animation-delay:.3s}
@keyframes ccd{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
.cc-err{align-self:flex-start;color:var(--c-red);font-size:13px}
.cc-foot{flex-shrink:0;padding:10px 14px 14px;border-top:1px solid var(--c-line)}
.cc-box{display:flex;align-items:flex-end;gap:8px;padding:8px;border:1px solid var(--c-line);border-radius:14px;background:var(--inbg,transparent)}
.cc-box:focus-within{border-color:var(--c-ink)}
.cc-ta{flex:1;min-width:0;max-height:180px;margin:0;padding:6px 6px;border:0;background:none;color:inherit;font:inherit;resize:none;outline:none}
.cc-ta::placeholder{color:var(--c-mute)}
.cc-ic{width:36px;height:36px;margin:0;padding:0;border:0;border-radius:10px;background:none;color:var(--c-body);display:grid;place-items:center;cursor:pointer;flex-shrink:0}
.cc-ic:hover,.cc-ic:focus-visible{background:var(--c-soft);color:var(--c-ink);outline:none}
.cc-ic:disabled{opacity:.4;cursor:default;background:none}
.cc-send{background:var(--c-ink);color:var(--c-onink)}
.cc-send:hover,.cc-send:focus-visible{background:var(--c-ink);color:var(--c-onink);opacity:.85}
.cc-send:disabled{opacity:.25;background:var(--c-ink);color:var(--c-onink)}
.cc-ic:active{transform:scale(.96)}
.cc-rec{display:none;align-items:center;gap:8px;padding:0 4px 0 6px;font-size:13px;color:var(--c-body);font-variant-numeric:tabular-nums}
.cc-rec.on{display:flex}
.cc-rec>i{width:9px;height:9px;border-radius:50%;background:var(--c-red);animation:ccp 1.2s ease-in-out infinite}
@keyframes ccp{50%{opacity:.35}}
.cc-lv{display:flex;align-items:center;gap:2px;height:18px}.cc-lv s{display:block;width:3px;height:100%;border-radius:2px;background:var(--c-ink);transform:scaleY(.15);transform-origin:center;opacity:.6}
.cc-ic.cc-live{color:var(--c-red)}
.cc-lang{font:600 11px/1 inherit;letter-spacing:.02em;color:var(--t3,#78716c);background:none;border:1px solid var(--line,#e7e5e4);border-radius:6px;padding:4px 6px;cursor:pointer;align-self:center}
.cc-lang:hover{color:var(--ink,#0c0a09)}
.cc-note{min-height:0;margin:8px 4px 0;font-size:13px;line-height:18px;color:var(--c-red)}
.cc-note:empty{display:none}.cc-note.info{color:var(--c-mute)}
.cc-note button{margin-left:8px;height:26px;padding:0 10px;border:1px solid var(--c-line);border-radius:8px;background:none;color:var(--c-ink);font:inherit;font-size:12.5px;cursor:pointer}
@media (prefers-reduced-motion:reduce){.cc-dots i,.cc-rec>i{animation:none}}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MIC='<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><rect x="6.5" y="2" width="5" height="9" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3.5 8.5a5.5 5.5 0 0011 0M9 14v2.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';
const SEND='<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const STOP='<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="2" y="2" width="10" height="10" rx="2" fill="currentColor"/></svg>';

async function post(u,b){const r=await fetch(u,{method:'POST',body:JSON.stringify(b||{})});let j={};try{j=await r.json()}catch(e){}return Object.assign(j,{_ok:r.ok})}

// Minimal safe markdown: escape first, then code blocks, lists, paragraphs, bold, inline code, http(s) links.
function md(src){
  const blocks=[];let t=esc(src).replace(/```[^\n`]*\n?([\s\S]*?)(```|$)/g,(_,c)=>{blocks.push(`<pre><code>${c.replace(/\n$/,'')}</code></pre>`);return `\u0000${blocks.length-1}\u0000`});
  const inline=s=>s.replace(/`([^`\n]+)`/g,'<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g,'<b>$1</b>')
    .replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const out=[];let list=null,para=[];
  const flushP=()=>{if(para.length){out.push(`<p>${inline(para.join('<br>'))}</p>`);para=[]}};
  const flushL=()=>{if(list){out.push(`<${list.t}>${list.items.map(i=>`<li>${inline(i)}</li>`).join('')}</${list.t}>`);list=null}};
  for(const line of t.split('\n')){
    const m=/^\s*([-*]|\d+[.)])\s+(.*)$/.exec(line),b=/^\u0000(\d+)\u0000$/.exec(line.trim());
    if(b){flushP();flushL();out.push(blocks[+b[1]])}
    else if(m){flushP();const tag=/\d/.test(m[1])?'ol':'ul';if(!list||list.t!==tag){flushL();list={t:tag,items:[]}}list.items.push(m[2])}
    else if(!line.trim()){flushP();flushL()}
    else{flushL();para.push(line)}
  }
  flushP();flushL();
  return out.join('').replace(/\u0000(\d+)\u0000/g,(_,i)=>blocks[+i]);
}

// ---- dictation: one function, used by the chat composer and by dictateButton ----
// note(text,kind,action): shows or clears an inline message. kind 'info' | 'err'; action {label,run} adds a button.
function dictate(ta,btn,note,meter){
  let rec=null,stream=null,ctx=null,chunks=[],timer=null,raf=0,t0=0,busy=false;
  const label=btn.getAttribute('aria-label')||'Dictate';
  const bars=meter?[...meter.lv.children]:[];
  // spoken language: a known one transcribes about twice as fast as auto-detect on a laptop CPU
  const LANGS=['auto','he','en'],NAMES={auto:'Auto',he:'HE',en:'EN'};
  let lang;try{lang=localStorage.getItem('cc-lang')}catch(e){}
  if(!LANGS.includes(lang))lang=/^he\b/i.test(navigator.language||'')?'he':'auto';
  const lb=document.createElement('button');lb.type='button';lb.className='cc-lang';
  const showLang=()=>{lb.textContent=NAMES[lang];lb.title='Spoken language: '+(lang==='auto'?'detect automatically (slower)':lang==='he'?'Hebrew':'English')+'. Click to change.'};
  lb.onclick=()=>{lang=LANGS[(LANGS.indexOf(lang)+1)%LANGS.length];try{localStorage.setItem('cc-lang',lang)}catch(e){}showLang()};
  showLang();btn.insertAdjacentElement('beforebegin',lb);
  function cleanup(){clearInterval(timer);cancelAnimationFrame(raf);if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;
    if(ctx){try{ctx.close()}catch(e){}ctx=null}if(meter)meter.box.classList.remove('on');btn.classList.remove('cc-live')}
  function insert(text){
    const s=ta.selectionStart??ta.value.length,e=ta.selectionEnd??s,before=ta.value.slice(0,s);
    const add=(before&&!/\s$/.test(before)?' ':'')+text.trim();
    ta.setRangeText(add,s,e,'end');ta.dispatchEvent(new Event('input',{bubbles:true}));ta.focus();
  }
  async function send(blob,type){
    busy=true;btn.disabled=true;note('Transcribing...','info');
    try{
      const r=await fetch('/dictate'+(lang==='auto'?'':'?lang='+lang),{method:'POST',headers:{'Content-Type':type},body:blob});let j={};try{j=await r.json()}catch(e){}
      if(r.ok&&typeof j.text==='string'){note('');if(j.text.trim())insert(j.text);else note('Nothing was heard. Try again.','info')}
      else if(j.code==='no_model'||j.code==='no_venv'||j.code==='no_ffmpeg')
        note(j.code==='no_ffmpeg'?'Dictation needs ffmpeg, which setup installs.':'Dictation is not set up yet.','err',{label:'Run setup',run:async()=>{const x=await post('/job',{type:'setup'});note(x._ok?'Setup started. Check Home for progress, then try again.':'Could not start setup. Run it from Settings.','info')}});
      else note("Couldn't transcribe, try again.",'err');
    }catch(e){note("Couldn't transcribe, try again.",'err')}
    busy=false;btn.disabled=false;
  }
  async function start(){
    note('');
    if(!navigator.mediaDevices||!window.MediaRecorder)return note('This browser cannot record audio.','err');
    try{stream=await navigator.mediaDevices.getUserMedia({audio:true})}
    catch(e){return note(e&&e.name==='NotFoundError'?'No microphone found.':'Microphone access is blocked. Allow it in the browser address bar and try again.','err')}
    const mime=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'].find(m=>MediaRecorder.isTypeSupported(m))||'';
    chunks=[];rec=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);
    rec.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
    rec.onstop=()=>{const type=rec.mimeType||mime||'audio/webm',blob=new Blob(chunks,{type});rec=null;cleanup();
      if(blob.size<800)return note('That was too short. Try again.','info');send(blob,type.split(';')[0]==='audio/webm'?'audio/webm;codecs=opus':type)};
    rec.start();t0=Date.now();btn.classList.add('cc-live');btn.setAttribute('aria-label','Stop recording');
    if(meter){meter.box.classList.add('on');meter.time.textContent='0:00';
      timer=setInterval(()=>{const s=Math.floor((Date.now()-t0)/1000);meter.time.textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')},250);
      try{ctx=new (window.AudioContext||window.webkitAudioContext)();const an=ctx.createAnalyser();an.fftSize=256;ctx.createMediaStreamSource(stream).connect(an);
        const d=new Uint8Array(an.frequencyBinCount),calm=matchMedia('(prefers-reduced-motion:reduce)').matches;
        const tick=()=>{an.getByteFrequencyData(d);const n=bars.length,step=Math.floor(d.length/2/n);
          bars.forEach((b,i)=>{let v=0;for(let k=0;k<step;k++)v+=d[i*step+k];v=v/step/255;b.style.transform=`scaleY(${calm?.5:Math.min(1,.15+v*1.8)})`});raf=requestAnimationFrame(tick)};tick()}catch(e){}}
  }
  function stop(){if(rec&&rec.state!=='inactive'){btn.setAttribute('aria-label',label);rec.stop()}}
  btn.addEventListener('click',()=>{if(busy)return;rec?stop():start()});
  return {destroy(){if(rec){rec.onstop=null;try{rec.stop()}catch(e){}rec=null}cleanup();lb.remove()}};
}
function noteFn(el){return (text,kind,action)=>{el.textContent=text||'';el.className=el.className.replace(/\binfo\b/g,'').trim()+(kind==='info'?' info':'');
  if(action){const b=document.createElement('button');b.type='button';b.textContent=action.label;b.onclick=action.run;el.appendChild(b)}}}

function dictateButton(ta){
  const btn=document.createElement('button');btn.type='button';btn.className='cc-x cc-ic';btn.innerHTML=MIC;btn.setAttribute('aria-label','Dictate');btn.title='Dictate (click to start and stop)';
  btn.style.cssText+=';display:inline-grid;vertical-align:middle';
  const note=document.createElement('div');note.className='cc-x cc-note';note.setAttribute('role','status');
  ta.after(btn);btn.after(note);
  dictate(ta,btn,noteFn(note));
  return btn;
}

// ---- the panel ----
function mount(el,opts){
  opts=opts||{};const slug=opts.slug||'',ctxInfo=opts.context;
  el.innerHTML=`<div class="cc"><div class="cc-hd"><b>Claude</b><button type="button" class="cc-btn" data-new>New chat</button></div>
  <div class="cc-msgs" role="log" aria-live="polite"></div>
  <div class="cc-foot"><div class="cc-box"><textarea class="cc-ta" rows="1" placeholder="Message Claude" aria-label="Message Claude"></textarea>
  <div class="cc-rec" role="status"><i></i><span data-time>0:00</span><span class="cc-lv"><s></s><s></s><s></s><s></s><s></s></span></div>
  <button type="button" class="cc-ic" data-mic aria-label="Dictate" title="Dictate (click to start and stop)">${MIC}</button>
  <button type="button" class="cc-ic cc-send" data-send aria-label="Send" title="Send">${SEND}</button></div><div class="cc-note" role="status"></div></div></div>`;
  const $=s=>el.querySelector(s),msgs=$('.cc-msgs'),ta=$('.cc-ta'),sendB=$('[data-send]'),newB=$('[data-new]'),micB=$('[data-mic]'),noteEl=$('.cc-note');
  const note=noteFn(noteEl);if(opts.placeholder)ta.placeholder=opts.placeholder;
  let turn=null,es=null,poll=null,seen=0,cur=null,curText='',typing=null,stick=true,gone=false,raf=0,first=true;
  const mic=dictate(ta,micB,note,{box:$('.cc-rec'),time:$('[data-time]'),lv:$('.cc-lv')});
  msgs.addEventListener('scroll',()=>{stick=msgs.scrollHeight-msgs.scrollTop-msgs.clientHeight<48});
  const down=()=>{if(stick)msgs.scrollTop=msgs.scrollHeight};
  const add=(cls,html)=>{const d=document.createElement('div');d.className=cls;if(html!=null)d.innerHTML=html;msgs.appendChild(d);down();return d};
  const clearEmpty=()=>{const e=msgs.querySelector('.cc-empty');if(e)e.remove()};
  const empty=()=>{if(!msgs.children.length)add('cc-empty','Ask Claude to cut, restyle or explain anything in this project.')};
  const user=t=>{clearEmpty();add('cc-u').textContent=t};
  const asst=t=>{clearEmpty();const d=add('cc-a',md(t));return d};
  const tool=s=>{clearEmpty();const d=add('cc-tool');d.textContent=s;cur=null;curText=''};
  const err=t=>{add('cc-err').textContent=t};
  function showTyping(on){if(on&&!typing){typing=add('cc-dots','<i></i><i></i><i></i>')}else if(!on&&typing){typing.remove();typing=null}}
  function running(on){
    sendB.innerHTML=on?STOP:SEND;sendB.setAttribute('aria-label',on?'Stop':'Send');sendB.title=on?'Stop':'Send';sendB.disabled=false;
  }
  function paint(){raf=0;if(cur){cur.innerHTML=md(curText);down()}}
  function ev(e){
    if(!e||typeof e!=='object')return;
    if(e.type==='text'&&e.text){showTyping(false);if(!cur){clearEmpty();cur=add('cc-a');curText=''}curText+=e.text;if(!raf)raf=requestAnimationFrame(paint)}
    else if(e.type==='tool'){showTyping(false);if(raf){cancelAnimationFrame(raf);paint()}tool(e.summary||e.name||'Working');showTyping(true)}
    else if(e.type==='error'){finish();err(e.text||'Something went wrong. Try again.')}
    else if(e.type==='done')finish();
  }
  function finish(){
    if(raf){cancelAnimationFrame(raf);paint()}
    if(es){es.close();es=null}clearInterval(poll);poll=null;showTyping(false);cur=null;curText='';turn=null;running(false);
  }
  function pollEvents(t){
    clearInterval(poll);
    poll=setInterval(async()=>{try{const r=await fetch(`/chat/events?turn=${encodeURIComponent(t)}&since=${seen}`);if(!r.ok)return;const j=await r.json();
      if(t!==turn)return;(j.events||[]).forEach(ev);seen=j.next??seen+(j.events||[]).length;if(j.finished&&t===turn)finish()}catch(e){}},700);
  }
  function listen(t){
    seen=0;
    try{es=new EventSource(`/chat/stream?turn=${encodeURIComponent(t)}&since=0`)}catch(e){return pollEvents(t)}
    es.onmessage=m=>{if(t!==turn)return;seen++;try{ev(JSON.parse(m.data))}catch(e){}};
    es.onerror=()=>{if(t!==turn)return;if(es)es.close();es=null;if(turn===t)pollEvents(t)};   // the stream broke: carry on by polling from where we were
  }
  async function send(text){
    text=String(text??ta.value).trim();if(!text||turn)return;
    note('');ta.value='';grow();stick=true;user(text);showTyping(true);turn='pending';running(true);
    let j;try{j=await post('/chat',{slug,text,context:first?ctxInfo:undefined})}catch(e){j={_ok:false}}
    if(!j._ok||!j.turn){turn=null;showTyping(false);running(false);err((j&&j.error)||'Claude could not be reached. Try again.');return}
    first=false;if(gone)return;turn=j.turn;listen(turn);
  }
  async function stop(){
    const t=turn;if(!t||t==='pending')return;try{await post('/chat/stop',{turn:t})}catch(e){}
    setTimeout(()=>{if(turn===t)finish()},1500);   // the stream normally ends with "done"; if not, release the composer
  }
  function grow(){ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,180)+'px'}
  ta.addEventListener('input',grow);
  ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send()}});
  sendB.addEventListener('click',()=>turn?stop():send());
  newB.addEventListener('click',async()=>{if(turn){await stop();finish()}await post('/chat/new',{slug});msgs.innerHTML='';first=true;note('');empty();ta.focus()});
  (async()=>{
    try{const r=await fetch('/chat/history?slug='+encodeURIComponent(slug));if(r.ok){const j=await r.json();
      for(const m of j.messages||[]){if(m.role==='user')user(m.text||'');else{(m.tools||[]).forEach(s=>tool(s));if(m.text)asst(m.text)}}
      first=!(j.messages||[]).length}}catch(e){}
    empty();stick=true;msgs.scrollTop=msgs.scrollHeight;
  })();
  return {send,focus:()=>ta.focus(),destroy(){gone=true;mic.destroy();finish();el.innerHTML=''}};
}
window.CookedChat={mount,dictateButton};
})();
