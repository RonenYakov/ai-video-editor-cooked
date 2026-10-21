// Reference breakdowns for a creator.
//   CookedRef.list(el, handle)  -> tiles for GET /references?handle=
//   CookedRef.open(handle, id)  -> modal for GET /reference?handle=&id=
// Uses the page's colour tokens (--panel --ink --t2 --t3 --line --soft ...), same as ask.js. Requests ride the page cookie.
(()=>{
if(typeof document==='undefined')return;
const css=`.cr-grid{--r-panel:var(--panel,#fff);--r-ink:var(--ink,#0C0A09);--r-body:var(--t2,#57534E);--r-mute:var(--t3,#78716C);--r-line:var(--line,#E7E5E4);--r-soft:var(--soft,#F5F5F4);--r-onink:var(--onink,#fff);
 display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:14px;font:14px/20px system-ui,-apple-system,"Segoe UI",sans-serif}
.cr-x{--r-panel:var(--panel,#fff);--r-ink:var(--ink,#0C0A09);--r-body:var(--t2,#57534E);--r-mute:var(--t3,#78716C);--r-line:var(--line,#E7E5E4);--r-soft:var(--soft,#F5F5F4);--r-onink:var(--onink,#fff);
 font:14px/20px system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--r-ink)}
.cr-x *{box-sizing:border-box}
.cr-tile{display:flex;flex-direction:column;gap:8px;margin:0;padding:0;border:0;background:none;color:var(--r-ink);font:inherit;text-align:left;cursor:pointer}
.cr-th{position:relative;aspect-ratio:9/14;border-radius:14px;background:var(--r-soft) center/cover no-repeat;border:1px solid var(--r-line);overflow:hidden;transition:border-color .15s}
.cr-tile:hover .cr-th,.cr-tile:focus-visible .cr-th{border-color:var(--r-ink)}.cr-tile:focus-visible{outline:none}
.cr-tile:active .cr-th{transform:scale(.98)}
.cr-tt{font-size:13px;line-height:18px;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cr-bd{align-self:flex-start;padding:2px 9px;border-radius:999px;font-size:12px;line-height:16px;border:1px solid var(--r-line);color:var(--r-mute)}
.cr-bd.full{background:var(--r-ink);border-color:var(--r-ink);color:var(--r-onink)}
.cr-empty{color:var(--r-mute);font-size:14px}
.cr-ov{position:fixed;inset:0;z-index:9990;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(12,10,9,.46)}
.cr-md{width:100%;max-width:880px;max-height:calc(100vh - 32px);overflow:auto;background:var(--r-panel);border:1px solid var(--r-line);border-radius:20px;box-shadow:0 12px 40px rgba(0,0,0,.2);position:relative}
.cr-hd{position:sticky;top:0;z-index:1;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px 24px 14px;background:var(--r-panel);border-bottom:1px solid var(--r-line)}
.cr-hd h2{margin:0;font-size:19px;line-height:25px;font-weight:600;letter-spacing:-.01em}
.cr-sub{margin-top:2px;color:var(--r-mute);font-size:13px;line-height:18px}
.cr-sub a{color:inherit;text-decoration:underline 1px;text-underline-offset:3px}
.cr-close{width:36px;height:36px;flex-shrink:0;margin:0;padding:0;border:1px solid var(--r-line);border-radius:10px;background:none;color:var(--r-body);cursor:pointer;display:grid;place-items:center}
.cr-close:hover,.cr-close:focus-visible{border-color:var(--r-ink);color:var(--r-ink);outline:none}
.cr-bodyg{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:28px;padding:22px 24px 26px}
.cr-vid{position:relative;aspect-ratio:9/16;max-height:62vh;width:100%;border-radius:14px;overflow:hidden;background:#0C0A09 center/cover no-repeat;border:1px solid var(--r-line)}
.cr-vid video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#0C0A09}
.cr-vid a{position:absolute;left:12px;bottom:12px;padding:6px 12px;border-radius:10px;background:var(--r-panel);color:var(--r-ink);font-size:13px;text-decoration:none}
.cr-col{min-width:0;display:flex;flex-direction:column;gap:22px}
.cr-h{margin:0 0 8px;font-size:12px;line-height:16px;font-weight:600;color:var(--r-mute);letter-spacing:.02em}
.cr-tl{display:flex;gap:2px;height:30px;border-radius:9px;overflow:hidden}
.cr-seg{flex:0 0 auto;min-width:3px;height:100%;margin:0;padding:0;border:0;cursor:pointer;color:var(--r-onink);opacity:.92;transition:opacity .12s,transform .12s}
.cr-seg:hover,.cr-seg:focus-visible,.cr-seg.on{opacity:1;outline:none;transform:scaleY(1.12)}
.cr-bl{display:flex;flex-direction:column;margin-top:12px}
.cr-b{display:grid;grid-template-columns:12px minmax(0,1fr);gap:10px;align-items:start;width:100%;margin:0;padding:8px 6px;border:0;border-radius:10px;background:none;color:inherit;font:inherit;text-align:left;cursor:pointer}
.cr-b:hover,.cr-b:focus-visible{background:var(--r-soft);outline:none}
.cr-sw{width:12px;height:12px;margin-top:4px;border-radius:4px}
.cr-b b{font-weight:600}.cr-b .m{color:var(--r-mute);font-size:12.5px;margin-left:8px;font-variant-numeric:tabular-nums}
.cr-b q{display:block;margin-top:2px;color:var(--r-body);font-size:13px;line-height:18px;quotes:"\\201C" "\\201D"}
.cr-hook{padding:14px 16px;border:1px solid var(--r-line);border-radius:14px}
.cr-hook p{margin:0;font-size:15px;line-height:22px}.cr-hook .m{margin-top:6px;color:var(--r-mute);font-size:13px}
.cr-pace{display:flex;gap:18px;align-items:flex-end;height:74px}
.cr-pb{display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-start;gap:4px;height:100%}
.cr-pb i{display:block;width:34px;border-radius:5px 5px 2px 2px;background:var(--r-ink);opacity:.82}
.cr-pb span{font-size:12px;line-height:14px;color:var(--r-mute);font-variant-numeric:tabular-nums}
.cr-st{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:14px 18px;margin:0}
.cr-st div{min-width:0}.cr-st dt{color:var(--r-mute);font-size:12.5px;line-height:17px}.cr-st dd{margin:1px 0 0;font-size:16px;line-height:22px;font-weight:600;font-variant-numeric:tabular-nums}
.cr-note{padding:14px 16px;border:1px solid var(--r-line);border-radius:14px;background:var(--r-soft);color:var(--r-body);font-size:13.5px;line-height:20px}
.cr-note div{margin-bottom:10px}
.cr-pri{height:40px;margin:0;padding:0 18px;border:0;border-radius:10px;background:var(--r-ink);color:var(--r-onink);font:inherit;font-weight:600;cursor:pointer}
.cr-pri:disabled{opacity:.4;cursor:default}
.cr-pri:focus-visible{outline:2px solid var(--r-ink);outline-offset:2px}
@media (max-width:720px){.cr-bodyg{grid-template-columns:1fr;gap:20px;padding:18px 16px 22px}.cr-hd{padding:16px 16px 12px}.cr-vid{max-height:50vh;max-width:300px;margin:0 auto}.cr-ov{align-items:flex-end;padding:8px}}
@media (prefers-reduced-motion:reduce){.cr-seg,.cr-th{transition:none}}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>typeof v==='number'&&isFinite(v);
const clock=s=>{s=Math.max(0,Math.round(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const fmtN=n=>n>=1e6?(n/1e6).toFixed(1).replace(/\.0$/,'')+'M':n>=1e3?(n/1e3).toFixed(1).replace(/\.0$/,'')+'K':String(n);
const safeUrl=u=>/^https?:\/\//i.test(u||'')?u:'';
const X='<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
// neutral tones, one per distinct label, from the page's own ink
const TONES=[88,62,42,74,30,54,96,36];
const tone=n=>`color-mix(in srgb,var(--ink,#0C0A09) ${TONES[n%TONES.length]}%,var(--panel,#fff))`;

async function list(el,handle){
  el.innerHTML='';
  let refs=[];
  try{const r=await fetch('/references?handle='+encodeURIComponent(handle));if(r.ok)refs=(await r.json()).refs||[]}catch(e){}
  if(!refs.length){el.innerHTML='<div class="cr-x cr-empty">No references analysed yet.</div>';return}
  el.innerHTML=`<div class="cr-grid">${refs.map(r=>`<button type="button" class="cr-tile cr-x" data-id="${esc(r.id)}">
    <span class="cr-th"${r.thumb?` style="background-image:url('${esc(r.thumb)}')"`:''}></span><span class="cr-tt">${esc(r.title||'Untitled video')}</span>
    <span class="cr-bd${r.has_beats?' full':''}">${r.has_beats?'Full breakdown':'Numbers only'}</span></button>`).join('')}</div>`;
  el.querySelectorAll('.cr-tile').forEach(b=>b.onclick=()=>open(handle,b.dataset.id));
}

let openModal=null;
function stat(label,v,unit){return num(v)?`<div><dt>${esc(label)}</dt><dd>${esc(String(Math.round(v*10)/10))}${unit?` <span style="font-weight:400;color:var(--t3,#78716C);font-size:13px">${esc(unit)}</span>`:''}</dd></div>`:''}

async function open(handle,id){
  if(openModal)openModal.close();
  const prev=document.activeElement,ov=document.createElement('div');ov.className='cr-ov cr-x';
  ov.innerHTML='<div class="cr-md" role="dialog" aria-modal="true" aria-label="Reference breakdown" tabindex="-1"><div class="cr-hd"><div><h2>Loading...</h2></div><button type="button" class="cr-close" aria-label="Close">'+X+'</button></div></div>';
  document.body.appendChild(ov);
  const md=ov.firstChild,onKey=e=>{
    if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close();return}
    if(e.key==='Tab'){const f=[...md.querySelectorAll('button:not(:disabled),a[href],video[controls],[tabindex="0"]')].filter(x=>x.offsetParent!==null);
      if(!f.length){e.preventDefault();return}const a=f[0],z=f[f.length-1];
      if(e.shiftKey&&(document.activeElement===a||document.activeElement===md)){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}};
  function close(){document.removeEventListener('keydown',onKey,true);ov.remove();openModal=null;if(prev&&prev.focus)try{prev.focus()}catch(e){}}
  openModal={close};
  ov.addEventListener('mousedown',e=>{if(e.target===ov)close()});
  document.addEventListener('keydown',onKey,true);
  md.querySelector('.cr-close').onclick=close;md.focus();
  let d=null;
  try{const r=await fetch(`/reference?handle=${encodeURIComponent(handle)}&id=${encodeURIComponent(id)}`);if(r.ok)d=await r.json()}catch(e){}
  if(!openModal||openModal.close!==close)return;
  if(!d){md.querySelector('h2').textContent="Couldn't load this reference.";return}
  draw(md,d,handle,close);
}

function draw(md,d,handle,close){
  const b=d.beats,p=d.pace,v=d.visual,url=safeUrl(d.url),video=d.video_path?'/media?p='+encodeURIComponent(d.video_path):'';
  const sub=[d.platform,num(d.views)?fmtN(d.views)+' views':'',num(d.duration)?clock(d.duration):''].filter(Boolean).map(esc).join(' &nbsp;|&nbsp; ');
  const beats=b&&Array.isArray(b.beats)?b.beats.filter(x=>x&&num(x.dur_s)&&x.dur_s>0):[];
  const labels=[...new Set(beats.map(x=>x.label||'Beat'))],ix=l=>labels.indexOf(l||'Beat');
  const total=beats.reduce((s,x)=>s+x.dur_s,0);
  const thirds=p&&Array.isArray(p.wpm_thirds)?p.wpm_thirds.filter(num):[],maxW=Math.max(1,...thirds);
  const ps=p?[stat('Words per minute',p.wpm),stat('Median pause',p.pause_median_ms,'ms'),stat('Pauses per minute',p.pauses_per_min),stat('Longest pause',p.longest_pause_s,'s'),stat('First word at',p.first_word_at,'s'),stat('Filler words per 100',p.filler_rate_per_100w)].join(''):'';
  const vs=v?[stat('Cuts per 10 s',v.cuts_per_10s),stat('Median shot',v.median_shot_s,'s'),stat('Zooms per minute',v.zooms_per_min)].join(''):'';
  const fmt=typeof d.format==='string'&&d.format?d.format:'';
  const extra=b?[['Close',b.close],['Graphics',b.graphics],['Look',b.look],['Notes',b.notes]].filter(([,t])=>typeof t==='string'&&t.trim()):[];
  md.innerHTML=`<div class="cr-hd"><div style="min-width:0"><h2>${esc(d.title||'Untitled video')}</h2><div class="cr-sub">${d.handle?'@'+esc(String(d.handle).replace(/^@/,'')):''}${d.handle&&sub?' &nbsp;|&nbsp; ':''}${sub}${url?`${(d.handle||sub)?' &nbsp;|&nbsp; ':''}<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open original</a>`:''}</div></div>
  <button type="button" class="cr-close" aria-label="Close">${X}</button></div>
  <div class="cr-bodyg"><div><div class="cr-vid"${d.thumb?` style="background-image:url('${esc(d.thumb)}')"`:''}>${video?`<video controls playsinline preload="metadata" src="${esc(video)}"${d.thumb?` poster="${esc(d.thumb)}"`:''}></video>`:url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Watch original</a>`:''}</div></div>
  <div class="cr-col">
  ${b&&b.hook&&b.hook.text?`<section><h3 class="cr-h">Hook</h3><div class="cr-hook"><p>${esc(b.hook.text)}</p>${num(b.hook.ends_s)||num(b.hook.words)?`<div class="m">${num(b.hook.ends_s)?'Lands at '+clock(b.hook.ends_s).replace(/^0:/,'0:'):''}${num(b.hook.ends_s)&&num(b.hook.words)?', ':''}${num(b.hook.words)?b.hook.words+' words':''}</div>`:''}</div></section>`:''}
  ${beats.length?`<section><h3 class="cr-h">Structure</h3><div class="cr-tl" role="group" aria-label="Beat timeline">${beats.map((x,i)=>`<button type="button" class="cr-seg" data-i="${i}" style="width:${(x.dur_s/total*100).toFixed(2)}%;background:${tone(ix(x.label))}" aria-label="${esc(x.label||'Beat')}, from ${clock(x.start_s||0)}" title="${esc(x.label||'Beat')} ${clock(x.start_s||0)}"></button>`).join('')}</div>
  <div class="cr-bl">${beats.map((x,i)=>`<button type="button" class="cr-b" data-i="${i}"><i class="cr-sw" style="background:${tone(ix(x.label))}"></i><span><b>${esc(x.label||'Beat')}</b><span class="m">${clock(x.start_s||0)}${num(x.words)?', '+x.words+' words':''}${num(x.wpm)?', '+Math.round(x.wpm)+' wpm':''}</span>${x.quote?`<q>${esc(x.quote)}</q>`:''}</span></button>`).join('')}</div></section>`:''}
  ${thirds.length?`<section><h3 class="cr-h">Pace, words per minute by third</h3><div class="cr-pace">${thirds.map((w,i)=>`<div class="cr-pb"><i style="height:${Math.max(6,Math.round(w/maxW*48))}px"></i><span>${['Start','Middle','End'][i]||i+1}: ${Math.round(w)}</span></div>`).join('')}</div></section>`:''}
  ${ps.trim()?`<section><h3 class="cr-h">Speech</h3><dl class="cr-st">${ps}</dl></section>`:''}
  ${vs.trim()||fmt?`<section><h3 class="cr-h">Visuals</h3>${vs.trim()?`<dl class="cr-st">${vs}</dl>`:''}${fmt?`<div style="margin-top:10px;color:var(--t2,#57534E)">${esc(fmt)}</div>`:''}</section>`:''}
  ${extra.map(([k,t])=>`<section><h3 class="cr-h">${k}</h3><div style="color:var(--t2,#57534E)">${esc(t)}</div></section>`).join('')}
  ${d.needs_reanalyse||!b?`<div class="cr-note"><div>${b?'This video was analysed with an older version, so some detail is missing.':'Only the numbers were saved for this video. The beat by beat breakdown is not available.'}</div><button type="button" class="cr-pri" data-re>Re-analyse for full breakdown</button><span data-msg style="margin-left:12px"></span></div>`:''}
  </div></div>`;
  md.querySelector('.cr-close').onclick=close;
  const vid=md.querySelector('video');
  if(vid)vid.addEventListener('error',()=>{const box=vid.parentNode;vid.remove();if(url&&!box.querySelector('a'))box.insertAdjacentHTML('beforeend',`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Watch original</a>`)},{once:true});
  const seek=i=>{const x=beats[+i];if(!x)return;md.querySelectorAll('.cr-seg').forEach(s=>s.classList.toggle('on',s.dataset.i===String(i)));
    if(vid&&vid.isConnected){try{vid.currentTime=x.start_s||0;vid.play().catch(()=>{})}catch(e){}}};
  md.querySelectorAll('.cr-seg,.cr-b').forEach(e=>e.onclick=()=>seek(e.dataset.i));
  const re=md.querySelector('[data-re]');
  if(re)re.onclick=async()=>{
    re.disabled=true;const m=md.querySelector('[data-msg]');
    let ok=false;try{const r=await fetch('/job',{method:'POST',body:JSON.stringify({type:'teardown',handle:String(handle).replace(/^@/,''),platform:d.platform||undefined})});ok=r.ok}catch(e){}
    m.textContent=ok?'Started. Watch progress on the Home page.':'Could not start it. Try again.';if(!ok)re.disabled=false;
  };
}
window.CookedRef={list,open};
})();
