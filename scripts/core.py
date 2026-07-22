#!/usr/bin/env python3
"""
Shared search core (Phase 1.5): hybrid retrieval = semantic (model2vec cosine)
+ lexical (BM25) + KO->EN glossary query expansion, plus a popularity "best" list
ranked by real GitHub stars. Imported by serve.py / search.py / demo_search.py.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from model2vec import StaticModel

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SKILLS = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))["skills"]
META = json.loads((DATA / "embed_meta.json").read_text(encoding="utf-8"))
EMB = np.load(DATA / "embeddings.npy").astype(np.float32)
STARS = json.loads((DATA / "stars.json").read_text(encoding="utf-8")) \
    if (DATA / "stars.json").exists() else {}
SAFETY = json.loads((DATA / "safety.json").read_text(encoding="utf-8")) \
    if (DATA / "safety.json").exists() else {}

BACKEND = META.get("backend", "model2vec")
if BACKEND == "sentence-transformers":
    from sentence_transformers import SentenceTransformer
    _MODEL = SentenceTransformer(META["model"])

    def _encode(texts):
        return np.asarray(_MODEL.encode(texts, convert_to_numpy=True,
                                        normalize_embeddings=False), dtype=np.float32)
else:
    _MODEL = StaticModel.from_pretrained(META["model"])

    def _encode(texts):
        return np.asarray(_MODEL.encode(texts), dtype=np.float32)

_REPO = re.compile(r"github\.com/([^/#?]+)/([^/#?]+)", re.I)


def repo_of(url):
    m = _REPO.search(url or "")
    return f"{m.group(1)}/{m.group(2).replace('.git', '')}" if m else None


for s in SKILLS:  # attach repo + star count + freshness
    r = repo_of(s["url"])
    s["repo"] = r
    st = STARS.get(r) if r else None
    s["stars"] = st["stars"] if st and st.get("stars") is not None else None
    s["pushed"] = st.get("pushed") if st else None
    s["archived"] = bool(st.get("archived")) if st else False
    sf = SAFETY.get(s["url"])
    s["risk"] = sf["level"] if sf else None
    s["flags"] = sf.get("flags", []) if sf else []

BY_URL = {s["url"]: s for s in SKILLS}

# ---------- lexical BM25 index ----------
_TOKEN = re.compile(r"[a-z0-9]+|[가-힣]+")


def tok(t):
    return _TOKEN.findall((t or "").lower())


def _text(s):
    parts = [s["name"]]
    if s["description"]:
        parts.append(s["description"])
    parts.append(s["category"])
    return " ".join(parts)


_DOCS = [tok(_text(s)) for s in SKILLS]
_N = len(_DOCS)
_doc_len = np.array([len(d) for d in _DOCS], dtype=np.float32)
_avgdl = float(_doc_len.mean()) or 1.0
_df = Counter()
_postings = defaultdict(list)  # token -> [(doc_idx, tf), ...]
for _i, _d in enumerate(_DOCS):
    for _t, _c in Counter(_d).items():
        _df[_t] += 1
        _postings[_t].append((_i, _c))
_idf = {t: math.log(1 + (_N - d + 0.5) / (d + 0.5)) for t, d in _df.items()}
_K1, _B = 1.5, 0.75


def _bm25(qtokens):
    scores = np.zeros(_N, dtype=np.float32)
    for t in set(qtokens):
        p = _postings.get(t)
        if not p:
            continue
        w = _idf[t]
        for i, c in p:
            scores[i] += w * (c * (_K1 + 1)) / (c + _K1 * (1 - _B + _B * _doc_len[i] / _avgdl))
    return scores


# ---------- KO -> EN domain glossary (query expansion) ----------
# stopgap until a stronger multilingual model; feeds BOTH semantic + lexical.
GLOSSARY = {
    "보안": "security", "취약점": "vulnerability", "테스트": "testing", "테스팅": "testing",
    "디버그": "debug", "디버깅": "debugging", "배포": "deploy deployment",
    "문서": "document documentation", "슬라이드": "slide presentation",
    "발표": "presentation", "프레젠테이션": "presentation", "커밋": "commit",
    "리뷰": "review", "코드": "code", "검색": "search", "자동화": "automation",
    "번역": "translation", "이미지": "image", "브라우저": "browser", "웹": "web",
    "데이터베이스": "database", "데이터": "data", "분석": "analysis",
    "마이그레이션": "migration", "프론트엔드": "frontend", "프론트": "frontend",
    "백엔드": "backend", "컴포넌트": "component", "깃허브": "github", "깃": "git",
    "워크플로우": "workflow", "스프레드시트": "spreadsheet", "엑셀": "excel spreadsheet",
    "보고서": "report", "요약": "summary summarize", "메시지": "message",
    "알림": "notification", "결제": "payment", "인증": "authentication",
    "차트": "chart", "그래프": "graph", "일정": "schedule calendar", "캘린더": "calendar",
    "이메일": "email", "크롤": "crawl scrape", "스크래핑": "scraping",
    "리팩터": "refactor", "리팩토링": "refactoring", "최적화": "optimization",
    "테스트케이스": "test case", "api": "api", "데브옵스": "devops",
}


def expand(query):
    q = query.lower()
    extra = [en for ko, en in GLOSSARY.items() if ko in q]
    return (query + " " + " ".join(extra)).strip() if extra else query


def _norm(a):
    m = float(a.max()) if a.size else 0.0
    return a / m if m > 0 else a


def _row(s, score=None):
    r = {"name": s["name"], "url": s["url"], "desc": s["description"], "cat": s["category"],
         "tier": s["tier"], "au": s.get("author") or "", "v": bool(s.get("verified")),
         "src": s["sources"], "stars": s["stars"],
         "pushed": s.get("pushed"), "arch": s.get("archived", False),
         "risk": s.get("risk"), "flags": s.get("flags", [])}
    if score is not None:
        r["score"] = round(score, 3)
    return r


def rows_for_urls(urls):
    return [_row(BY_URL[u]) for u in urls if u in BY_URL]


def search(query, tier="all", k=25, alpha=0.78, cat=None):
    """Hybrid: alpha * semantic + (1-alpha) * lexical, both min-max normalized.
    Semantic uses the ORIGINAL query (multilingual model reads KO natively);
    lexical uses the glossary-EXPANDED query (EN terms help latin keyword hits)."""
    v = _encode([query])[0]
    v = v / (np.linalg.norm(v) or 1.0)
    sem = np.clip(EMB @ v, 0, None)
    lex = _bm25(tok(expand(query)))
    final = alpha * _norm(sem) + (1 - alpha) * _norm(lex)
    order = np.argsort(-final)
    out = []
    for i in order:
        s = SKILLS[i]
        if tier != "all" and s["tier"] != tier:
            continue
        if cat and s["category"] != cat:
            continue
        out.append(_row(s, float(final[i])))
        if len(out) >= k:
            break
    return out


# meta / marketplace / example repos — not a single installable skill; keep out of Best
BEST_BLOCK = {
    "anthropics/claude-cookbooks", "anthropics/claude-plugins-official",
    "anthropics/claude-plugins-public",
}


def best(tier="all", k=24, cat=None):
    """Most popular skills by real GitHub stars, one per repo, good cards only."""
    cand = [s for s in SKILLS
            if s["description"] and s["stars"] is not None and s["repo"] not in BEST_BLOCK]
    if tier != "all":
        cand = [s for s in cand if s["tier"] == tier]
    if cat:
        cand = [s for s in cand if s["category"] == cat]
    cand.sort(key=lambda s: (s["stars"], len(s["sources"])), reverse=True)
    out, seen = [], set()
    for s in cand:
        if s["repo"] in seen:
            continue
        seen.add(s["repo"])
        out.append(_row(s))
        if len(out) >= k:
            break
    return out
