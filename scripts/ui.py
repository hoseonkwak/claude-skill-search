#!/usr/bin/env python3
"""
Shared front-end — modern & clean, Apple-flavored.
Light = pure white / SF system type; Dark = deep navy with white text.
Accent = Claude coral (#D97757). In-page theme toggle (persists to localStorage).
Plain strings (no f-strings) so CSS/JS braces stay literal.
"""
import json

CSS = """
:root{
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic","Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --bg:#ffffff;--panel:#ffffff;--panel-2:#f5f5f7;--ink:#1d1d1f;--ink2:#6e6e73;--faint:#9c9ca3;
  --line:#e7e7ec;--line2:#d7d7dd;
  --accent:#c8623f;--accent-2:#b1502f;--accent-soft:rgba(200,98,63,.12);--on-accent:#ffffff;
  --shadow:0 1px 2px rgba(0,0,0,.05),0 6px 20px -12px rgba(0,0,0,.18);
  --shadow-sm:0 1px 2px rgba(0,0,0,.10);
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0b1a30;--panel:#10233d;--panel-2:#172c48;--ink:#f2f5fa;--ink2:#aebacd;--faint:#7c89a1;
  --line:#20334f;--line2:#2c4162;
  --accent:#e2845f;--accent-2:#eb9878;--accent-soft:rgba(226,132,95,.16);--on-accent:#12233b;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.6);--shadow-sm:0 1px 3px rgba(0,0,0,.4);
}}
:root[data-theme="light"]{--bg:#ffffff;--panel:#ffffff;--panel-2:#f5f5f7;--ink:#1d1d1f;--ink2:#6e6e73;--faint:#9c9ca3;--line:#e7e7ec;--line2:#d7d7dd;--accent:#c8623f;--accent-2:#b1502f;--accent-soft:rgba(200,98,63,.12);--on-accent:#fff;--shadow:0 1px 2px rgba(0,0,0,.05),0 6px 20px -12px rgba(0,0,0,.18);--shadow-sm:0 1px 2px rgba(0,0,0,.10)}
:root[data-theme="dark"]{--bg:#0b1a30;--panel:#10233d;--panel-2:#172c48;--ink:#f2f5fa;--ink2:#aebacd;--faint:#7c89a1;--line:#20334f;--line2:#2c4162;--accent:#e2845f;--accent-2:#eb9878;--accent-soft:rgba(226,132,95,.16);--on-accent:#12233b;--shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.6);--shadow-sm:0 1px 3px rgba(0,0,0,.4)}

:root{--danger:#c0392b;--danger-soft:#fbe9e7;--warn:#b7791f;--warn-soft:#f8efd9;--ok:#2f855a;--ok-soft:#e6f4ec}
@media (prefers-color-scheme:dark){:root{--danger:#f0776a;--danger-soft:#3a1e1b;--warn:#e0a94a;--warn-soft:#2c2413;--ok:#5fbd8a;--ok-soft:#16291f}}
:root[data-theme="light"]{--danger:#c0392b;--danger-soft:#fbe9e7;--warn:#b7791f;--warn-soft:#f8efd9;--ok:#2f855a;--ok-soft:#e6f4ec}
:root[data-theme="dark"]{--danger:#f0776a;--danger-soft:#3a1e1b;--warn:#e0a94a;--warn-soft:#2c2413;--ok:#5fbd8a;--ok-soft:#16291f}
/* spacing (8pt grid) + type scale (×1.25) — VISUAL-DESIGN-PLAYBOOK.md */
:root{--sp2:8px;--sp3:12px;--sp4:16px;--sp5:24px;--sp6:32px;--sp7:48px;--sp8:64px;--sp9:96px;
  --tCap:13px;--tBody:16px;--tLg:20px;--tH2:25px}
*{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased;transition:background .3s,color .3s}
a{color:inherit;text-decoration:none}
.page{max-width:940px;margin:0 auto;padding:var(--sp5) clamp(18px,5vw,28px) 100px}
/* hero & chips span wide; reading content keeps a readable measure (B1) */
.controls,.sec,.list,.empty,.note,.intro,.legend,footer{max-width:760px;margin-inline:auto}

/* top bar */
.topbar{display:flex;justify-content:space-between;align-items:center;height:52px}
.brand{display:flex;align-items:center;gap:8px;font-weight:600;font-size:15.5px;letter-spacing:-.01em;cursor:pointer}
.brand:hover .bt,.brand:active{opacity:.85}
.brand .spark{color:var(--accent);display:flex}
.theme-btn{width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--ink2);cursor:pointer;display:grid;place-items:center;transition:.15s}
.theme-btn:hover{background:var(--panel-2);color:var(--ink);border-color:var(--line2)}
.theme-btn:active{transform:scale(.94)}

/* hero */
.hero{text-align:center;padding:clamp(24px,6vw,52px) 0 4px}
.hero h1{font-size:clamp(32px,6.4vw,56px);font-weight:700;letter-spacing:-.035em;line-height:1.05;margin:0 0 16px;text-wrap:balance}
.hero h1 .c{color:var(--accent)}
.hero .sub{font-size:clamp(16px,2.3vw,19px);color:var(--ink2);max-width:42ch;margin:0 auto;line-height:1.45}
.searchbox{display:flex;align-items:center;gap:11px;background:var(--panel-2);border:1.5px solid transparent;border-radius:15px;padding:15px 18px;max-width:580px;margin:26px auto 0;transition:.15s}
.searchbox:focus-within{background:var(--panel);border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.searchbox svg{width:20px;height:20px;stroke:var(--faint);flex:none}
.searchbox input{flex:1;min-width:0;border:0;background:transparent;font-family:var(--sans);font-size:17px;color:var(--ink);outline:none}
.searchbox input::placeholder{color:var(--faint)}
.stats{text-align:center;margin-top:16px;font-size:13px;color:var(--faint)}
.stats b{color:var(--ink2);font-weight:600;font-variant-numeric:tabular-nums}
.intro{font-size:13.5px;color:var(--ink2);margin:16px auto 0;line-height:1.55}
.intro b{color:var(--ink);font-weight:600}
.legend{font-size:11.5px;color:var(--faint);margin:9px 0 2px;line-height:1.7}
.legend .lg{font-weight:600;color:var(--ink2)}
.legend .lg.ok{color:var(--ok)}.legend .lg.warn{color:var(--warn)}.legend .lg.risk{color:var(--danger)}
.chips{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:20px}
.chips button{font-family:var(--sans);font-size:13px;color:var(--ink2);background:var(--panel-2);border:0;border-radius:980px;padding:7px 15px;cursor:pointer;transition:.13s}
.chips button:hover{background:var(--accent-soft);color:var(--accent)}
.cols-wrap{margin-top:26px}
.cols-label{display:block;font-size:12px;color:var(--faint);margin-bottom:11px}
.cols{display:flex;gap:9px;flex-wrap:wrap;justify-content:center}
.col-chip{display:inline-flex;align-items:center;gap:7px;font-family:var(--sans);font-size:13.5px;font-weight:500;
  color:var(--ink);background:var(--panel);border:1px solid var(--line2);border-radius:12px;padding:9px 15px;cursor:pointer;transition:.13s}
.col-chip:hover{border-color:var(--accent);color:var(--accent)}
.col-chip.on{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.col-chip .e{font-size:15px}
.cols.doms{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;max-width:720px;margin:0 auto}
.doms .col-chip{justify-content:flex-start;gap:11px;padding:16px;font-size:14px;font-weight:600;border-radius:14px;background:var(--panel);border:1px solid var(--line2)}
.doms .col-chip .e{font-size:21px}
.doms .col-chip:hover{border-color:var(--accent);background:var(--accent-soft);color:var(--accent)}
.doms .col-chip.on{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.copy{font-family:var(--sans);font-size:11.5px;font-weight:600;color:var(--accent);background:var(--accent-soft);
  border:0;border-radius:7px;padding:5px 11px;cursor:pointer;white-space:nowrap;transition:.12s}
.copy:hover{background:var(--accent);color:var(--on-accent)}
.copy.done{background:var(--ok);color:#fff}
.howtobtn{font-family:var(--mono);font-size:11px;color:var(--accent);background:none;border:0;padding:0;cursor:pointer}
.howtobtn:hover{text-decoration:underline}
.howto{display:block;margin-top:10px;padding:13px 15px;background:var(--panel-2);border-radius:11px;font-size:12.5px;color:var(--ink2);line-height:1.5;max-width:62ch}
.howto[hidden]{display:none}   /* display:block가 UA의 [hidden]{display:none}을 덮어써서 필요 */
.howto .ht{display:flex;gap:9px;align-items:flex-start;margin-top:9px}
.howto .ht:first-child{margin-top:0}
.howto .ht i{flex:none;width:18px;height:18px;border-radius:50%;background:var(--accent);color:var(--on-accent);font-size:11px;font-weight:700;font-style:normal;display:grid;place-items:center;margin-top:1px}
.howto .ht b{color:var(--ink)}
.ht-cmd{display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap}
.ht-cmd code{font-family:var(--mono);font-size:11.5px;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px 8px;color:var(--ink);word-break:break-all}

/* category before/after demo panel */
.demo{display:none;margin:0 0 18px}
.demo.on{display:block}
.demo-h{font-size:13px;font-weight:700;color:var(--ink2);margin:0 0 10px;letter-spacing:-.01em}
.ba{display:grid;grid-template-columns:1fr auto 1fr;align-items:stretch;gap:12px}
.ba-card{border-radius:14px;padding:13px 15px;border:1px solid var(--line2);display:flex;flex-direction:column;gap:9px}
.ba-card.before{background:var(--panel-2)}
.ba-card.after{background:var(--accent-soft);border-color:var(--accent)}
.ba-tag{font-family:var(--mono);font-size:10.5px;font-weight:700;letter-spacing:.05em}
.ba-card.before .ba-tag{color:var(--faint)}
.ba-card.after .ba-tag{color:var(--accent)}
.ba-tag em{font-style:normal;font-weight:500;font-family:var(--sans);font-size:12px;letter-spacing:0;color:var(--ink2);margin-left:7px}
.ba-code{margin:0;font-family:var(--mono);font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;color:var(--ink)}
.ba-card.before .ba-code{color:var(--ink2)}
.ba-arrow{align-self:center;font-size:22px;font-weight:700;color:var(--accent)}
@media(max-width:640px){.ba{grid-template-columns:1fr}.ba-arrow{transform:rotate(90deg)}}

/* controls */
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:34px 0 0}
.seg{display:inline-flex;background:var(--panel-2);border-radius:11px;padding:3px}
.seg button{border:0;background:none;font-family:var(--sans);font-size:13px;font-weight:500;color:var(--ink2);padding:6px 15px;border-radius:8px;cursor:pointer;transition:.13s}
.seg button:hover{color:var(--ink)}
.seg button.on{background:var(--panel);color:var(--ink);font-weight:600;box-shadow:var(--shadow-sm)}
select{font-family:var(--sans);font-size:13px;color:var(--ink2);background:var(--panel);border:1px solid var(--line2);border-radius:9px;padding:7px 30px 7px 12px;outline:none;cursor:pointer;max-width:200px;
  -webkit-appearance:none;appearance:none;background-image:linear-gradient(45deg,transparent 50%,var(--faint) 50%),linear-gradient(135deg,var(--faint) 50%,transparent 50%);background-position:right 14px top 15px,right 9px top 15px;background-size:5px 5px;background-repeat:no-repeat}
select:focus{border-color:var(--accent)}
.count{margin-left:auto;font-size:13px;color:var(--faint)}.count b{color:var(--accent);font-weight:600}

/* section head */
.sec{display:flex;align-items:baseline;gap:10px;margin:30px 0 4px}
.sec h2{font-size:var(--tH2);font-weight:650;letter-spacing:-.02em;margin:0}
.sec .sc{font-size:13px;color:var(--faint)}

/* list — clean Apple rows */
.list{margin-top:6px;border-top:1px solid var(--line)}
.row{display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:2px 16px;align-items:center;
  padding:16px 12px;margin:0 -12px;border-bottom:1px solid var(--line);border-radius:14px;color:inherit;transition:background .12s}
.row:hover{background:var(--panel-2)}
.lead{justify-self:center}
.rk{font-size:19px;font-weight:600;color:var(--faint);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.rk.hi{color:var(--accent)}
.rel{font-family:var(--mono);font-size:12px;color:var(--faint)}
.body{min-width:0}
.rhead{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.rtitle{font-weight:600;font-size:16px;letter-spacing:-.012em;color:var(--ink);word-break:break-word}
.tag{font-size:11px;font-weight:600;letter-spacing:.01em;color:var(--faint);white-space:nowrap}
.tag.cur{color:var(--accent)}
.tag.arch{color:var(--faint);font-weight:500}
.tag.risk{color:#fff;background:var(--danger);padding:1px 7px;border-radius:6px}
.tag.warn{color:var(--warn)}
.tag.safe{color:var(--ok)}
.fresh.s0{color:var(--ink2)}
.fresh.s1,.fresh.s2{color:var(--faint)}
.rmeta .rf{color:var(--warn)}
.rmeta .rf.hi{color:var(--danger)}
.rdesc{margin:4px 0 0;color:var(--ink2);font-size:13.5px;line-height:1.5;max-width:62ch}
.rdesc.none{color:var(--faint);font-style:italic;font-size:12.5px}
.rmeta{margin-top:8px;font-size:11.5px;color:var(--faint);display:flex;gap:6px 11px;flex-wrap:wrap;font-family:var(--mono)}
.rfig{display:flex;align-items:center;gap:12px;white-space:nowrap}
.star{font-size:13px;color:var(--ink2);font-weight:600;font-variant-numeric:tabular-nums}
.chev{color:var(--line2);font-size:20px;line-height:1}

.empty{color:var(--faint);padding:52px 12px;font-size:14px;text-align:center}
.note{margin-top:22px;background:var(--panel-2);border-radius:12px;padding:13px 16px;font-size:13px;color:var(--ink2);line-height:1.55}
.note b{color:var(--accent)}
footer{margin-top:32px;padding-top:18px;border-top:1px solid var(--line);color:var(--faint);font-size:12px;line-height:1.65}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:8px}

@media (max-width:560px){
  .row{grid-template-columns:30px minmax(0,1fr);gap:2px 12px}
  .rfig{grid-column:2;justify-content:flex-start;margin-top:7px}
  .chev{display:none}
}
@media (prefers-reduced-motion:no-preference){
  .row{opacity:0;animation:fade .3s ease forwards}
  @keyframes fade{to{opacity:1}}
}
"""

_SPARK = ('<span class="spark"><svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">'
          '<path d="M12 2c.6 5 3 7.4 8 8-5 .6-7.4 3-8 8-.6-5-3-7.4-8-8 5-.6 7.4-3 8-8z"/></svg></span>')

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="page">
  <header class="topbar">
    <div class="brand">__SPARK__ Skill Finder</div>
    <button class="theme-btn" id="themeToggle" aria-label="테마 전환"></button>
  </header>

  <section class="hero">
    <h1>필요한 <span class="c">Claude</span> 스킬을<br>한 곳에서 찾다</h1>
    <p class="sub">필요한 스킬, 용도만 말하면 찾아드려요. 안전한지·인기 있는지도 한눈에.</p>
    <div class="searchbox">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="q" type="search" placeholder="__PLACEHOLDER__" autocomplete="off">
    </div>
    <div class="stats">수록 <b>__N__</b> · 검증 <b>__NC__</b> · ★ <b>__NS__</b></div>
    <p class="intro">💡 <b>스킬</b>은 클로드에게 특정 작업을 가르치는 지시셋이에요. 마음에 드는 걸 골라 <b>설치 복사</b> 한 번이면 끝.</p>
    <div class="chips" id="egs"></div>
    <div class="cols-wrap"><span class="cols-label">분야별로 둘러보기</span><div class="cols doms" id="doms"></div></div>
    <div class="cols-wrap"><span class="cols-label">이런 걸 하고 싶다면</span><div class="cols" id="cols"></div></div>
  </section>

  <div class="controls">
    <div class="seg" id="tier"><button data-t="all" class="on">전체</button><button data-t="curated">검증</button><button data-t="catalog">수집</button></div>
    <span class="count" id="hint"></span>
  </div>

  <div class="sec"><h2 id="sech">인기 스킬</h2><span class="sc" id="secc"></span></div>
  <div class="demo" id="demo"></div>
  <div class="legend"><span class="lg ok">검증됨</span> 공식·큐레이션 · <span class="lg">수집</span> 자동수집 · ★ 인기(스타) · 🕒 최근 업데이트 · SKILL.md 스캔 <span class="lg ok">안전</span> <span class="lg warn">주의</span> <span class="lg risk">위험</span></div>
  <div class="list" id="grid"></div>
  <p class="empty" id="msg" style="display:none"></p>
  __NOTE__
  <footer>__FOOTER__</footer>
</div>
<script>
__DATA_INIT__
const grid=document.getElementById('grid'),msg=document.getElementById('msg'),qEl=document.getElementById('q'),
hint=document.getElementById('hint'),sech=document.getElementById('sech'),secc=document.getElementById('secc'),
egsEl=document.getElementById('egs'),themeBtn=document.getElementById('themeToggle'),colsEl=document.getElementById('cols'),domsEl=document.getElementById('doms');
const EGS=__EGS__,COLS=__COLLECTIONS__,DEMOS=__DEMOS__;let tier='all',mode='best';
const demoEl=document.getElementById('demo');
function renderDemo(id){if(!demoEl)return;const m=DEMOS[id];if(!m){demoEl.className='demo';demoEl.innerHTML='';return}
  demoEl.innerHTML='<p class="demo-h">이렇게 쓰면 이런 결과가 나와요</p><div class="ba">'
    +'<div class="ba-card before"><span class="ba-tag">BEFORE<em>'+esc(m.bc)+'</em></span><pre class="ba-code">'+esc(m.b)+'</pre></div>'
    +'<div class="ba-arrow">→</div>'
    +'<div class="ba-card after"><span class="ba-tag">AFTER<em>'+esc(m.ac)+'</em></span><pre class="ba-code">'+esc(m.a)+'</pre></div></div>';
  demoEl.className='demo on'}

/* theme toggle */
const SUN='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M4.5 4.5l1.7 1.7M17.8 17.8l1.7 1.7M2 12h2.4M19.6 12H22M4.5 19.5l1.7-1.7M17.8 6.2l1.7-1.7"/></svg>';
const MOON='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A8.5 8.5 0 1111.2 3a6.6 6.6 0 009.8 9.8z"/></svg>';
function effTheme(){const a=document.documentElement.getAttribute('data-theme');if(a)return a;return matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'}
function setTheme(t){document.documentElement.setAttribute('data-theme',t);try{localStorage.setItem('sf-theme',t)}catch(e){}themeBtn.innerHTML=t==='dark'?SUN:MOON}
themeBtn.onclick=()=>setTheme(effTheme()==='dark'?'light':'dark');
(function(){let t=null;try{t=localStorage.getItem('sf-theme')}catch(e){}if(t){setTheme(t)}else{themeBtn.innerHTML=effTheme()==='dark'?SUN:MOON}})();

function esc(s){return(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function host(u){try{return new URL(u).hostname.replace(/^www\\./,'')}catch(e){return'link'}}
function fstar(n){return n==null?'':(n>=1000?(n/1000).toFixed(n>=10000?0:1)+'k':''+n)}
function fresh(p){if(!p)return null;const t=Date.parse(p);if(!t)return null;const dys=(Date.now()-t)/864e5;
  if(dys<31)return{t:'최근 업데이트',s:0};const m=Math.floor(dys/30.4);
  if(m<12)return{t:m+'개월 전',s:m>=8?1:0};return{t:Math.floor(dys/365)+'년+ 전',s:2}}
function setSec(a,b){sech.textContent=a;secc.textContent=b||'';if(demoEl){demoEl.className='demo';demoEl.innerHTML=''}}
const FLAG={'pipe-to-shell':'쉘 파이프 실행','base64-exec':'base64 실행','rm-rf-root':'파일 대량삭제',
'prompt-injection':'프롬프트 인젝션','secret-exfil':'시크릿·네트워크','curl-eval':'원격 eval',
'shell-exec':'쉘 실행','sudo':'sudo 사용','chmod-777':'chmod 777','network-call':'네트워크 호출','reads-secrets':'시크릿 접근'};
function card(s,i){
  let lead;
  if(mode==='best'){lead=`<span class="rk${i<3?' hi':''}">${i+1}</span>`}
  else if(s.score!=null){lead=`<span class="rel">${s.score.toFixed(2)}</span>`}
  else{lead='<span class="rel">·</span>'}
  const tag=s.tier==='curated'?'<span class="tag cur">검증됨</span>':'<span class="tag">수집</span>';
  const arch=s.arch?'<span class="tag arch">보관됨</span>':'';
  const rk=s.risk==='risk'?'<span class="tag risk">위험</span>':s.risk==='caution'?'<span class="tag warn">주의</span>':s.risk==='ok'?'<span class="tag safe">안전</span>':'';
  const star=s.stars!=null?`<span class="star">★ ${fstar(s.stars)}</span>`:'';
  const au=s.au?`<span>${esc(s.au)}</span>`:'';
  const fr=fresh(s.pushed);
  const frx=fr?`<span class="fresh s${fr.s}">${fr.t}</span>`:'';
  const fl=(s.flags&&s.flags.length&&s.risk!=='ok')?`<span class="rf${s.risk==='risk'?' hi':''}">⚠ ${s.flags.slice(0,3).map(f=>FLAG[f]||f).join(', ')}</span>`:'';
  const d=s.desc?`<p class="rdesc">${esc(s.desc)}</p>`:'<p class="rdesc none">설명 준비 중</p>';
  const cmd=installCmd(s.url);
  const howto=`<span class="howto" hidden>`
    +`<span class="ht"><i>1</i><span><b>설치</b> — 터미널에서 실행<span class="ht-cmd"><code>${esc(cmd)}</code><button class="copy" data-url="${esc(s.url)}">복사</button></span></span></span>`
    +`<span class="ht"><i>2</i><span><b>재시작</b> — Claude Code를 다시 켜면 스킬을 인식해요.</span></span>`
    +`<span class="ht"><i>3</i><span><b>사용</b> — 하고 싶은 작업을 그냥 말하면 Claude가 이 스킬을 <b>자동으로</b> 써요.</span></span></span>`;
  return `<div class="row">
  <span class="lead">${lead}</span>
  <span class="body"><span class="rhead"><a class="rtitle" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>${tag}${arch}${rk}</span>${d}
    <span class="rmeta"><span>${esc(s.cat)}</span>${au}${frx}${fl}<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(host(s.url))} ↗</a><button class="howtobtn" type="button">사용법 ▾</button></span>${howto}</span>
  <span class="rfig">${star}<button class="copy" data-url="${esc(s.url)}" title="~/.claude/skills 에 설치">설치 복사</button></span></div>`;
}
function paint(list){grid.innerHTML=list.map(card).join('');msg.style.display=list.length?'none':'';if(!list.length)msg.textContent='찾는 스킬이 없습니다. 다른 표현으로 시도해 보세요.'}
EGS.forEach(t=>{const b=document.createElement('button');b.textContent=t;b.onclick=()=>{clearCols();qEl.value=t;run()};egsEl.appendChild(b)});
function _chip(c){const b=document.createElement('button');b.className='col-chip';b.dataset.id=c.id;b.innerHTML='<span class="e">'+c.emoji+'</span>'+esc(c.name);b.onclick=()=>openCol(c.id,b);return b}
COLS.filter(c=>c.group==='field').forEach(c=>domsEl.appendChild(_chip(c)));
COLS.filter(c=>c.group!=='field').forEach(c=>colsEl.appendChild(_chip(c)));
function clearCols(){document.querySelectorAll('.col-chip').forEach(x=>x.classList.remove('on'))}
function installCmd(url){const m=(url||'').match(/github\\.com\\/([^/#?]+)\\/([^/#?]+)(?:\\/tree\\/([^/]+)\\/(.+))?/);if(!m)return'# 설치 정보 없음';const owner=m[1],repo=m[2].replace(/\\.git$/,''),branch=m[3],path=m[4];const name=(path?path.split('/').pop():repo).replace(/[^a-zA-Z0-9_.-]/g,'-');const src=path?owner+'/'+repo+'/'+path+(branch?'#'+branch:''):owner+'/'+repo;return'npx degit '+src+' ~/.claude/skills/'+name}
grid.addEventListener('click',e=>{
  const cp=e.target.closest('.copy');
  if(cp){e.preventDefault();navigator.clipboard.writeText(installCmd(cp.dataset.url)).then(()=>{const t=cp.textContent;cp.textContent='복사됨 ✓';cp.classList.add('done');setTimeout(()=>{cp.textContent=t;cp.classList.remove('done')},1400)}).catch(()=>{cp.textContent='복사 실패'});return}
  const hb=e.target.closest('.howtobtn');
  if(hb){e.preventDefault();const p=hb.closest('.body').querySelector('.howto');if(!p)return;if(p.hasAttribute('hidden')){p.removeAttribute('hidden');hb.textContent='사용법 ▴'}else{p.setAttribute('hidden','');hb.textContent='사용법 ▾'}}
});
document.querySelectorAll('#tier button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#tier button').forEach(x=>x.classList.remove('on'));b.classList.add('on');tier=b.dataset.t;clearCols();run()});
const _brand=document.querySelector('.brand');if(_brand)_brand.onclick=()=>{qEl.value='';document.querySelectorAll('#tier button').forEach((x,i)=>x.classList.toggle('on',i===0));tier='all';clearCols();run()};
let _d;qEl.addEventListener('input',()=>{clearCols();clearTimeout(_d);_d=setTimeout(run,__DEBOUNCE__)});
__CONTROLLER__
</script>
</body>
</html>
"""


def build_page(*, title, placeholder, n, nc, ns, cat_options, egs, footer,
               data_init="", controller, debounce=200, note="", collections=None, demos=None):
    return (TEMPLATE
            .replace("__CSS__", CSS)
            .replace("__SPARK__", _SPARK)
            .replace("__TITLE__", title)
            .replace("__PLACEHOLDER__", placeholder)
            .replace("__N__", f"{n:,}").replace("__NC__", str(nc)).replace("__NS__", str(ns))
            .replace("__CATOPTS__", cat_options)
            .replace("__COLLECTIONS__", json.dumps(collections or [], ensure_ascii=False))
            .replace("__DEMOS__", json.dumps(demos or {}, ensure_ascii=False))
            .replace("__EGS__", json.dumps(egs, ensure_ascii=False))
            .replace("__FOOTER__", footer)
            .replace("__NOTE__", note)
            .replace("__CONTROLLER__", controller)
            .replace("__DEBOUNCE__", str(debounce))
            .replace("__DATA_INIT__", data_init))   # last: embedded data never re-scanned


def fragment(html):
    style = html[html.index("<style>"):html.index("</style>") + len("</style>")]
    inner = html[html.index('<div class="page">'):html.rindex("</script>") + len("</script>")]
    return style + "\n" + inner + "\n"
