#!/usr/bin/env python3
"""
Popularity + freshness signal: fetch GitHub stars & last-push for skill repos.
Token mode (5000/hr, concurrent) so it covers ALL repos, not just a shortlist.

Auth: <project>/.gh_token or $GITHUB_TOKEN/$GH_TOKEN (public-read is enough).
Output: data/stars.json  { "owner/repo": {"stars":int,"pushed":iso,"archived":bool} }
Resumable: repos already cached are skipped.  Usage: enrich_stars.py [CAP]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 0     # 0 = all uncached


def get_token():
    f = ROOT / ".gh_token"
    if f.exists() and f.read_text(encoding="utf-8").strip():
        return f.read_text(encoding="utf-8").strip()
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


TOKEN = get_token()
H = {"User-Agent": "skill-finder", "Accept": "application/vnd.github+json"}
if TOKEN:
    H["Authorization"] = f"Bearer {TOKEN}"

skills = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))["skills"]
cache_path = DATA / "stars.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

REPO = re.compile(r"github\.com/([^/#?]+)/([^/#?]+)", re.I)
def repo_of(url):
    m = REPO.search(url or "")
    if not m:
        return None
    owner, name = m.group(1), m.group(2).replace(".git", "")
    if owner.lower() in ("sponsors", "orgs", "topics", "features", "about"):
        return None
    return f"{owner}/{name}"


def prio(s):
    return (bool(s["description"]), s["tier"] == "curated", len(s["sources"]))


seen, todo = set(), []
for s in sorted(skills, key=prio, reverse=True):
    r = repo_of(s["url"])
    if r and r not in seen and r not in cache:
        seen.add(r)
        todo.append(r)
if CAP:
    todo = todo[:CAP]
print(f"cached: {len(cache)}  to-fetch: {len(todo)}  token: {'yes' if TOKEN else 'NO (60/hr!)'}",
      flush=True)


def fetch(repo):
    for a in range(3):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers=H)
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            return repo, {"stars": d.get("stargazers_count", 0), "pushed": d.get("pushed_at"),
                          "archived": d.get("archived", False)}
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                ra = e.headers.get("Retry-After")
                time.sleep(min(30, int(ra) if ra and ra.isdigit() else 3 * (a + 1)))
                if a == 2:
                    return repo, {"_rl": True}
                continue
            return repo, {"stars": None, "error": e.code}      # 404 etc.
        except Exception:  # noqa: BLE001
            return repo, {"stars": None}
    return repo, {"_rl": True}


got = rl = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, (repo, val) in enumerate(ex.map(fetch, todo), 1):
        cache[repo] = val
        got += bool(val.get("stars"))
        rl += bool(val.get("_rl"))
        if i % 200 == 0:
            print(f"  {i}/{len(todo)}  stars={got}  ratelimited={rl}", flush=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
have = [v["stars"] for v in cache.values() if v.get("stars")]
print(f"\nsaved {cache_path.name}: {len(cache)} repos, {len(have)} with stars"
      f"{f', {rl} rate-limited' if rl else ''}. max={max(have):,}" if have else "no stars")
