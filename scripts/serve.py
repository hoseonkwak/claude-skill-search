#!/usr/bin/env python3
"""
Local web app (Phase 2 redesign): hybrid semantic+lexical search + popularity
"Best" leaderboard, on the shared ui.py design system.

    python scripts/serve.py            # -> http://localhost:8000
    python scripts/serve.py 8080
"""
import json
import os
import sys
from html import escape
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import core
import ui

N = len(core.SKILLS)
N_CUR = sum(1 for s in core.SKILLS if s["tier"] == "curated")
N_STAR = sum(1 for s in core.SKILLS if s["stars"] is not None)
CATS = sorted({s["category"] for s in core.SKILLS if s["tier"] == "curated"})
CAT_OPTS = "".join(f'<option value="{escape(c, quote=True)}">{escape(c)}</option>' for c in CATS)
_col_path = core.DATA / "collections.json"
COLLECTIONS = json.loads(_col_path.read_text(encoding="utf-8"))["collections"] if _col_path.exists() else []
COL_BY_ID = {c["id"]: c for c in COLLECTIONS}
_demo_path = core.DATA / "category_demos.json"
DEMOS = json.loads(_demo_path.read_text(encoding="utf-8")) if _demo_path.exists() else {}
COL_META = [{"id": c["id"], "emoji": c["emoji"], "name": c["name"], "group": c.get("group", "goal")}
            for c in COLLECTIONS]
print(f"ready: {N} skills, {N_CUR} curated, {N_STAR} starred, {len(COLLECTIONS)} collections", flush=True)

CONTROLLER = """
async function loadBest(){mode='best';setSec('인기 Best','GitHub 스타순 · 레포당 1개');hint.innerHTML='';
  const p=new URLSearchParams({tier:tier,k:30});
  const r=await fetch('/api/best?'+p);const j=await r.json();paint(j.results||[])}
let _seq=0;
async function run(){const q=qEl.value.trim();if(!q){loadBest();return}
  mode='search';const my=++_seq;setSec('검색 결과','');
  const p=new URLSearchParams({q:q,tier:tier,k:30});
  try{const r=await fetch('/api/search?'+p);const j=await r.json();if(my!==_seq)return;
  const res=j.results||[];secc.textContent=q?('"'+j.query+'"'):'';hint.innerHTML='<b>'+res.length+'</b>건';paint(res)}
  catch(e){if(my===_seq){grid.innerHTML='';msg.style.display='';msg.textContent='검색 오류: '+e}}}
async function openCol(id,btn){clearCols();if(btn)btn.classList.add('on');mode='best';qEl.value='';setSec('컬렉션','');
  const r=await fetch('/api/collection?id='+encodeURIComponent(id));const j=await r.json();
  secc.textContent=j.name||'';hint.innerHTML='<b>'+(j.results||[]).length+'</b>개';paint(j.results||[]);renderDemo(id)}
loadBest();
"""

PAGE = ui.build_page(
    title="Skill Finder — Claude Skills 의미 검색",
    placeholder="하고 싶은 작업을 자연어로  —  예: pdf에서 표 뽑기, 보안 취약점 점검 …",
    n=N, nc=N_CUR, ns=N_STAR, cat_options=CAT_OPTS,
    egs=["pdf에서 표 뽑기", "코드 리뷰 자동화", "웹 보안 취약점 점검", "슬라이드 만들기",
         "react 컴포넌트", "데이터베이스 마이그레이션", "깃 커밋 메시지", "엑셀 데이터 분석"],
    footer="검색 = 하이브리드(다국어 임베딩 의미유사도 + BM25 어휘 + KO→EN 용어확장) · "
           "Best = 실제 GitHub 스타순(레포당 1개) · 신선도 = 최근 커밋 · "
           "안전 뱃지 = SKILL.md 휴리스틱 스캔(참고용, 오탐 가능).",
    controller=CONTROLLER, debounce=200, collections=COL_META, demos=DEMOS).encode("utf-8")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")   # allow the static site to call
        self.send_header("Cache-Control", "public, max-age=60")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        tier = qs.get("tier", ["all"])[0]
        cat = qs.get("cat", [""])[0] or None
        if u.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif u.path == "/api/best":
            k = min(60, int(qs.get("k", ["30"])[0] or 30))
            self._json({"results": core.best(tier, k, cat)})
        elif u.path == "/api/collection":
            c = COL_BY_ID.get(qs.get("id", [""])[0])
            self._json({"name": c["name"], "results": core.rows_for_urls(c["urls"])}
                       if c else {"name": "", "results": []})
        elif u.path == "/api/search":
            q = (qs.get("q", [""])[0]).strip()
            k = min(60, int(qs.get("k", ["30"])[0] or 30))
            results = core.search(q, tier, k, cat=cat) if q else core.best(tier, k, cat)
            self._json({"query": q, "results": results})
        else:
            self._send(404, b"not found", "text/plain")


port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
print(f"serving on http://localhost:{port}  (Ctrl+C to stop)", flush=True)
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
