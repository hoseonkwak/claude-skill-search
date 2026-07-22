#!/usr/bin/env python3
"""
Catalog enrichment (token mode): for each catalog repo, use the GitHub trees API
to locate its SKILL.md, fetch it from raw.githubusercontent, and parse the
frontmatter `description`.

Auth: reads a token from  <project>/.gh_token  or  $GITHUB_TOKEN / $GH_TOKEN.
A public-repo-read token (classic token with NO scopes) is enough -> 5000 req/hr.

Output: data/enrich.json  { "owner/repo": {"name":..., "desc":..., "via":url} }
Resumable: repos with a settled result are skipped; only rate-limited ones retry.
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
RAW = DATA / "raw"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0     # 0 = all


def get_token():
    f = ROOT / ".gh_token"
    if f.exists() and f.read_text(encoding="utf-8").strip():
        return f.read_text(encoding="utf-8").strip()
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


TOKEN = get_token()
API_H = {"User-Agent": "skill-finder", "Accept": "application/vnd.github+json"}
if TOKEN:
    API_H["Authorization"] = f"Bearer {TOKEN}"
else:
    sys.exit("no token found — put a GitHub token in .gh_token or $GITHUB_TOKEN "
             "(unauthenticated API is only 60/hr, too low). See README.")

ROW = re.compile(
    r"\|\s*\[([^\]]+)\]\((https://github\.com/[^)\s]+)\)\s*\|\s*(\d+)\s*\|\s*`([^`]*)`\s*\|\s*`([^`]*)`")
rows = []
for ln in (RAW / "chat2anyllm.md").read_text(encoding="utf-8").splitlines():
    m = ROW.match(ln)
    if m and int(m.group(3)) >= 1:
        rows.append({"repo": m.group(1), "branch": m.group(4) or "main", "path": m.group(5) or "."})

cache_path = DATA / "enrich.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
todo = [r for r in rows if r["repo"] not in cache or cache[r["repo"]].get("_rl")]
if LIMIT:
    todo = todo[:LIMIT]
print(f"catalog repos: {len(rows)}  cached: {len(cache)}  to-fetch: {len(todo)}  (token: yes)",
      flush=True)

JUNK = {"tests", "test", "fixtures", "fixture", "examples", "example",
        "node_modules", ".git", "dist", "build", "vendor", ".github"}


def parse_frontmatter(text):
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
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+", ""):
            block = []
            for l2 in lines[i + 1:]:
                if re.match(r"\s+\S", l2):
                    block.append(l2.strip())
                elif l2.strip() == "":
                    block.append("")
                else:
                    break
            val = " ".join(block).strip()
        val = val.strip().strip("\"'").strip()
        if key == "name" and not name:
            name = val
        elif key == "description" and not desc:
            desc = val
    return name, desc


def pick_skillmd(paths, declared):
    cands = [p for p in paths if p.lower().endswith("skill.md")]
    if not cands:
        return None
    clean = [p for p in cands if not (set(p.lower().split("/")[:-1]) & JUNK)] or cands

    def score(p):
        under = 0 if (declared not in (".", "") and p.startswith(declared + "/")) else 1
        return (under, p.count("/"), len(p))
    return min(clean, key=score)


def _get(url, headers, timeout, tries=3):
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):                     # secondary/primary rate limit
                ra = e.headers.get("Retry-After")
                time.sleep(min(30, int(ra) if ra and ra.isdigit() else 3 * (a + 1)))
                if a == tries - 1:
                    raise
                continue
            raise
    raise urllib.error.URLError("retries exhausted")


def tree_paths(repo, branch):
    for ref in (branch, "HEAD", "main", "master"):
        try:
            d = json.loads(_get(f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1",
                                API_H, 25))
            return [t["path"] for t in d.get("tree", []) if t.get("type") == "blob"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    return None


def enrich_one(row):
    repo, branch, path = row["repo"], row["branch"], row["path"]
    try:
        paths = tree_paths(repo, branch)
    except urllib.error.HTTPError as e:
        return repo, {"_rl": True} if e.code in (403, 429) else {"desc": None, "err": e.code}
    except Exception:  # noqa: BLE001
        return repo, {"desc": None}
    if paths is None:
        return repo, {"desc": None, "err": 404}
    sp = pick_skillmd(paths, path)
    if not sp:
        return repo, {"desc": None, "nofile": True}
    try:
        text = _get(f"https://raw.githubusercontent.com/{repo}/{branch}/{sp}",
                    {"User-Agent": "skill-finder"}, 15).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return repo, {"desc": None}
    name, desc = parse_frontmatter(text)
    return repo, ({"name": name, "desc": desc, "via": sp} if desc else {"desc": None, "at": sp})


hit = rl = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for i, (repo, val) in enumerate(ex.map(enrich_one, todo), 1):
        cache[repo] = val
        hit += bool(val.get("desc"))
        rl += bool(val.get("_rl"))
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}  desc={hit}  ratelimited={rl}", flush=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
have = sum(1 for v in cache.values() if v.get("desc"))
print(f"\nsaved {cache_path.name}: {len(cache)} probed, {have} with descriptions "
      f"({hit} new, {rl} rate-limited — rerun to continue)")
