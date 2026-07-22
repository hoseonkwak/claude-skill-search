#!/usr/bin/env python3
"""
Tier 3 source expansion (quality-first): discover skill repos via GitHub repo
search (sorted by stars), then extract every SKILL.md as a skill with its
frontmatter description. Applies a star quality bar to keep noise out.

Auth: <project>/.gh_token or $GITHUB_TOKEN. Needs 5000/hr (token) — search API
is 30/min, so search is paced; tree/raw calls are concurrent.

Output: data/expanded.json {"skills":[...]}  + merges stars into data/stars.json
Resumable-ish: skips repos already in the dataset / stars cache.
Usage: expand_github.py [MIN_STARS] [NEW_CAP] [PER_REPO]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MIN_STARS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
NEW_CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
PER_REPO = int(sys.argv[3]) if len(sys.argv) > 3 else 15


def get_token():
    f = ROOT / ".gh_token"
    if f.exists() and f.read_text(encoding="utf-8").strip():
        return f.read_text(encoding="utf-8").strip()
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


TOKEN = get_token()
if not TOKEN:
    sys.exit("no token — put one in .gh_token (search API needs auth)")
H = {"User-Agent": "skill-finder", "Accept": "application/vnd.github+json",
     "Authorization": f"Bearer {TOKEN}"}

REPO = re.compile(r"github\.com/([^/#?]+)/([^/#?]+)", re.I)
def repo_of(url):
    m = REPO.search(url or "")
    return f"{m.group(1)}/{m.group(2).replace('.git', '')}" if m else None


# known repos: already in dataset or star cache
skills = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))["skills"]
stars = json.loads((DATA / "stars.json").read_text(encoding="utf-8")) \
    if (DATA / "stars.json").exists() else {}
known = {repo_of(s["url"]) for s in skills if repo_of(s["url"])}
known |= set(stars.keys())
print(f"known repos: {len(known)}", flush=True)

QUERIES = [
    "topic:claude-skills", "topic:claude-skill", "topic:agent-skills",
    "topic:claude-code-skills", "topic:claude-code",
    '"SKILL.md" in:readme', "claude skills in:name,description",
    "agent skills SKILL.md",
]


def _get(url, timeout=25, tries=4):
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout) as r:
                return json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                ra = e.headers.get("Retry-After") or e.headers.get("X-RateLimit-Reset")
                time.sleep(min(20, int(ra) if (ra and str(ra).isdigit() and int(ra) < 60) else 4 * (a + 1)))
                continue
            raise
    raise urllib.error.URLError("retries exhausted")


# ---- 1. discover candidate repos via repo search (sorted by stars) ----
cands = {}   # full_name -> {stars, pushed, branch}
for q in QUERIES:
    for page in range(1, 11):                     # up to 1000 per query
        url = ("https://api.github.com/search/repositories?q="
               + urllib.parse.quote(q) + f"&sort=stars&order=desc&per_page=100&page={page}")
        try:
            d, _ = _get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  search fail q={q!r} p{page}: {e}"); break
        items = d.get("items", [])
        if not items:
            break
        for it in items:
            fn = it["full_name"]
            if it.get("stargazers_count", 0) < MIN_STARS or fn in known or fn in cands:
                continue
            cands[fn] = {"stars": it["stargazers_count"], "pushed": it.get("pushed_at"),
                         "branch": it.get("default_branch") or "main",
                         "archived": it.get("archived", False)}
        time.sleep(2.2)                            # search API ~30/min
    print(f"  after q={q!r}: {len(cands)} new candidates", flush=True)
    if len(cands) >= NEW_CAP:
        break

todo = dict(list(cands.items())[:NEW_CAP])
print(f"candidate new repos (stars>={MIN_STARS}): {len(todo)}", flush=True)

# ---- 2. for each repo, find SKILL.md files & parse descriptions ----
JUNK = {"tests", "test", "fixtures", "fixture", "examples", "example",
        "node_modules", ".git", "dist", "build", "vendor", ".github", "templates"}


def parse_fm(text):
    text = text.lstrip("﻿").lstrip()
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    fm = text[3:end] if end > 0 else text[3:4000]
    lines = fm.splitlines()
    name = desc = None
    for i, l in enumerate(lines):
        m = re.match(r"(name|description):\s*(.*)", l)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v in ("|", ">", "|-", ">-", "|+", ">+", ""):
            blk = []
            for l2 in lines[i + 1:]:
                if re.match(r"\s+\S", l2):
                    blk.append(l2.strip())
                elif l2.strip() == "":
                    blk.append("")
                else:
                    break
            v = " ".join(blk).strip()
        v = v.strip().strip("\"'").strip()
        if k == "name" and not name:
            name = v
        elif k == "description" and not desc:
            desc = v
    return name, desc


def raw(repo, branch, path):
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(path)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "skill-finder"}),
                                    timeout=12) as r:
            return r.read(20000).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def harvest(item):
    fn, meta = item
    try:
        d, _ = _get(f"https://api.github.com/repos/{fn}/git/trees/{meta['branch']}?recursive=1", timeout=25)
    except Exception:  # noqa: BLE001
        return fn, []
    paths = [t["path"] for t in d.get("tree", []) if t.get("type") == "blob"
             and t["path"].lower().endswith("skill.md")
             and not (set(t["path"].lower().split("/")[:-1]) & JUNK)]
    paths.sort(key=lambda p: (p.count("/"), len(p)))
    out = []
    for p in paths[:PER_REPO]:
        txt = raw(fn, meta["branch"], p)
        if not txt:
            continue
        name, desc = parse_fm(txt)
        if not desc:
            continue
        d0 = "/".join(p.split("/")[:-1])
        out.append({
            "name": name or f"{fn.split('/')[-1]}/{d0.split('/')[-1] or 'skill'}",
            "url": f"https://github.com/{fn}" + (f"/tree/{meta['branch']}/{d0}" if d0 else ""),
            "description": desc, "category": "Source Catalog", "tier": "catalog",
            "source_list": "github-expand", "repo": fn, "branch": meta["branch"], "path": d0 or ".",
        })
    return fn, out


records, done = [], 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for fn, recs in ex.map(harvest, todo.items()):
        records.extend(recs)
        stars[fn] = {"stars": todo[fn]["stars"], "pushed": todo[fn]["pushed"],
                     "archived": todo[fn]["archived"]}
        done += 1
        if done % 200 == 0:
            print(f"  harvested {done}/{len(todo)} repos, {len(records)} skills", flush=True)
            (DATA / "expanded.json").write_text(json.dumps({"skills": records}, ensure_ascii=False, indent=2), encoding="utf-8")
            (DATA / "stars.json").write_text(json.dumps(stars, ensure_ascii=False, indent=2), encoding="utf-8")

(DATA / "expanded.json").write_text(json.dumps({"skills": records}, ensure_ascii=False, indent=2), encoding="utf-8")
(DATA / "stars.json").write_text(json.dumps(stars, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nexpanded.json: {len(records)} new skills from {len(todo)} repos; stars.json now {len(stars)} repos")
