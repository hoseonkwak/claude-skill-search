#!/usr/bin/env python3
"""
Build the self-contained static site from data/skills.json (+ stars), on the
shared ui.py design system. Home = popularity "Best"; search = client-side keyword.
(Semantic/hybrid search needs the local backend — see serve.py.)

Output: site/index.html (standalone) + site/artifact.html (body-only fragment)
"""
import json
import re
from html import escape
from pathlib import Path

import ui

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "skills.json").read_text(encoding="utf-8"))
skills = data["skills"]
stars = json.loads((ROOT / "data" / "stars.json").read_text(encoding="utf-8")) \
    if (ROOT / "data" / "stars.json").exists() else {}
safety = json.loads((ROOT / "data" / "safety.json").read_text(encoding="utf-8")) \
    if (ROOT / "data" / "safety.json").exists() else {}
collections = json.loads((ROOT / "data" / "collections.json").read_text(encoding="utf-8"))["collections"] \
    if (ROOT / "data" / "collections.json").exists() else []

_REPO = re.compile(r"github\.com/([^/#?]+)/([^/#?]+)", re.I)
def repo_of(url):
    m = _REPO.search(url or "")
    return f"{m.group(1)}/{m.group(2).replace('.git', '')}" if m else None

for s in skills:
    r = repo_of(s["url"])
    st = stars.get(r) if r else None
    s["_repo"] = r
    s["_stars"] = st["stars"] if st and st.get("stars") is not None else None
    s["_pushed"] = st.get("pushed") if st else None
    s["_arch"] = bool(st.get("archived")) if st else False
    sf = safety.get(s["url"])
    s["_risk"] = sf["level"] if sf else None
    s["_flags"] = sf.get("flags", []) if sf else []

BEST_BLOCK = {"anthropics/claude-cookbooks", "anthropics/claude-plugins-official",
              "anthropics/claude-plugins-public"}
# cap embedded data for the static artifact (keeps it light; local app has all)
CAP = 4000
_cur = [s for s in skills if s["tier"] == "curated"]
_cat = sorted((s for s in skills if s["tier"] == "catalog"),
              key=lambda s: (s["_stars"] or 0), reverse=True)
subset = _cur + _cat[:max(0, CAP - len(_cur))]
# make sure every collection's skills are embedded so they can render
_col_urls = {u for c in collections for u in c["urls"]}
_have = {s["url"] for s in subset}
subset += [s for s in skills if s["url"] in _col_urls and s["url"] not in _have]
_url2id = {s["url"]: s["id"] for s in subset}
col_payload = [{"id": c["id"], "emoji": c["emoji"], "name": c["name"], "group": c.get("group", "goal"),
                "ids": [_url2id[u] for u in c["urls"] if u in _url2id]} for c in collections]

best_ids, seen = [], set()
for s in sorted(subset, key=lambda s: ((s["_stars"] or 0), len(s["sources"])), reverse=True):
    if not s["description"] or s["_stars"] is None or s["_repo"] in BEST_BLOCK or s["_repo"] in seen:
        continue
    seen.add(s["_repo"])
    best_ids.append(s["id"])
    if len(best_ids) >= 30:
        break

slim = [{
    "id": s["id"], "name": s["name"], "desc": s["description"], "url": s["url"],
    "cat": s["category"], "tier": s["tier"], "au": s.get("author") or "",
    "v": bool(s.get("verified")), "src": s["sources"], "stars": s["_stars"],
    "pushed": s["_pushed"], "arch": s["_arch"], "risk": s["_risk"], "flags": s["_flags"],
} for s in subset]   # desc_ko는 싣지 않음 — 기계번역 표시 중단(아래 CLAUDE.md 결정)

payload = json.dumps({"skills": slim, "best": best_ids},
                     ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

cats = sorted({s["category"] for s in skills if s["tier"] == "curated"})
cat_opts = "".join(f'<option value="{escape(c, quote=True)}">{escape(c)}</option>' for c in cats)
n_cur = sum(1 for s in skills if s["tier"] == "curated")
n_star = sum(1 for s in skills if s["_stars"] is not None)

CONTROLLER = """
function showBest(){mode='best';setSec('인기 Best','GitHub 스타순 · 레포당 1개');hint.innerHTML='';
  let list=BEST.map(id=>BYID[id]).filter(Boolean);
  if(tier!=='all')list=list.filter(s=>s.tier===tier);
  paint(list)}
function run(){const q=qEl.value.trim().toLowerCase();
  if(!q){showBest();return}
  mode='search';setSec('검색 결과','');
  const terms=q.split(/\\s+/).filter(Boolean);
  let out=SK.filter(s=>{if(tier!=='all'&&s.tier!==tier)return false;
    if(!terms.length)return true;const hay=(s.name+' '+s.desc+' '+s.cat+' '+s.au).toLowerCase();
    return terms.every(t=>hay.includes(t))});
  out.sort((a,b)=>(b.stars||0)-(a.stars||0));
  secc.textContent=q?('"'+q+'"'):'';hint.innerHTML='<b>'+out.length.toLocaleString()+'</b>건';
  paint(out.slice(0,300));
  if(out.length>300)grid.insertAdjacentHTML('beforeend','<div class="empty">상위 300개 표시 · 검색어를 좁혀보세요 (총 '+out.length.toLocaleString()+'건)</div>')}
const COLBYID={};COLS.forEach(c=>COLBYID[c.id]=c);
function openCol(id,btn){clearCols();if(btn)btn.classList.add('on');mode='best';qEl.value='';
  const c=COLBYID[id];const list=(c?c.ids:[]).map(i=>BYID[i]).filter(Boolean);
  setSec('컬렉션','');secc.textContent=c?c.name:'';hint.innerHTML='<b>'+list.length+'</b>개';paint(list)}
showBest();
"""

NOTE = ('<div class="note">💡 이 페이지 검색은 <b>키워드 매칭</b>입니다. '
        '한국어 자연어 <b>의미 검색</b>은 로컬 앱(serve.py)에서 동작합니다.</div>')

html = ui.build_page(
    title="Skill Finder — Claude Skills 통합 검색",
    placeholder="키워드로 검색  —  예: pdf, security, react, git, database …",
    n=len(skills), nc=n_cur, ns=n_star, cat_options=cat_opts,
    egs=["pdf", "security", "react", "git", "database", "test", "slides", "docx"],
    footer="데이터: anthropics/claude-plugins-official + awesome-claude-skills(karanb192/travisvn/"
           "composio/mingrath/Chat2AnyLLM) + GitHub 확장 · Best = GitHub 스타순 · "
           "안전 뱃지 = SKILL.md 휴리스틱 스캔(참고용, 오탐 가능).",
    data_init="const D=" + payload + ";const SK=D.skills,BEST=D.best,BYID={};SK.forEach(s=>BYID[s.id]=s);",
    controller=CONTROLLER, debounce=110, note=NOTE, collections=col_payload)

out = ROOT / "site" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"wrote {out}  ({len(html):,} bytes)  |  {len(skills)} skills, {len(best_ids)} best, {n_star} starred")

frag = ui.fragment(html)
(ROOT / "site" / "artifact.html").write_text(frag, encoding="utf-8")
print(f"wrote {ROOT / 'site' / 'artifact.html'}  ({len(frag):,} bytes)")

# GitHub Pages copy (served from main:/docs)
docs = ROOT / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(html, encoding="utf-8")
(docs / ".nojekyll").write_text("", encoding="utf-8")
print(f"wrote {docs / 'index.html'}  (GitHub Pages)")
