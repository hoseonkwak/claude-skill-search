#!/usr/bin/env python3
"""
Option B — trust & safety scan. Fetches each skill's SKILL.md (raw, no API limit)
and flags risk signals via heuristics: shell-pipe execution, secret exfiltration,
prompt injection, destructive commands, obfuscation. Produces a risk level.

Scope (first pass): skills from expand_github.py (they carry exact repo/branch/path).
Output: data/safety.json  { skill_url: {"level": ok|caution|risk, "flags":[...]} }
Resumable: skills already scanned are skipped.  Usage: scan_safety.py [LIMIT]
"""
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# ---- heuristic risk patterns (case-insensitive) ----
HIGH = [
    ("pipe-to-shell", re.compile(r"(?:curl|wget)\b[^\n|]{0,200}\|\s*(?:sudo\s+)?(?:ba)?sh", re.I)),
    ("base64-exec", re.compile(r"base64\s+(?:-d|--decode)\b[^\n|]{0,80}\|\s*(?:ba)?sh", re.I)),
    ("rm-rf-root", re.compile(r"rm\s+-rf?\s+(?:/|~|\$HOME|\*)(?:\s|$|/)", re.I)),
    ("prompt-injection", re.compile(
        r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+instructions"
        r"|disregard\s+(?:the\s+)?(?:above|previous|prior)"
        r"|do\s+not\s+(?:tell|inform|notify|reveal\s+to)\s+the\s+user"
        r"|exfiltrat", re.I)),
    ("curl-eval", re.compile(r"eval\s*\(\s*(?:atob|base64|require\(['\"]child_process)", re.I)),
]
SECRET = re.compile(r"(?:id_rsa|\.ssh/|\.env\b|aws_secret|secret_access_key|private_key|"
                    r"OPENAI_API_KEY|ANTHROPIC_API_KEY|password\s*=)", re.I)
NET = re.compile(r"\b(?:curl|wget|fetch\(|requests\.(?:get|post|put)|urllib\.request|"
                 r"axios|https?://[^\s'\")]+)", re.I)
CAUTION = [
    ("shell-exec", re.compile(r"\bos\.system\(|subprocess[^\n]{0,60}shell\s*=\s*True|"
                              r"child_process|\bexecSync\(|shelljs", re.I)),
    ("sudo", re.compile(r"(?<![\w-])sudo\s", re.I)),
    ("chmod-777", re.compile(r"chmod\s+(?:-R\s+)?777", re.I)),
    ("network-call", NET),
    ("reads-secrets", SECRET),
]


def assess(text):
    flags, level = [], "ok"
    for name, rx in HIGH:
        if rx.search(text):
            flags.append(name)
            level = "risk"
    if level != "risk":
        for name, rx in CAUTION:
            if rx.search(text):
                flags.append(name)
                level = "caution"
    return {"level": level, "flags": flags}


def raw_url(repo, branch, path):
    p = "SKILL.md" if path in (".", "", None) else f"{path.rstrip('/')}/SKILL.md"
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{p}"


def scan(item):
    url, repo, branch, path = item
    try:
        req = urllib.request.Request(raw_url(repo, branch, path), headers={"User-Agent": "skill-finder"})
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read(40000).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return url, None
    return url, assess(text)


exp = json.loads((DATA / "expanded.json").read_text(encoding="utf-8")).get("skills", []) \
    if (DATA / "expanded.json").exists() else []
cache_path = DATA / "safety.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

todo = [(s["url"], s["repo"], s.get("branch") or "main", s.get("path") or ".")
        for s in exp if s.get("repo") and s["url"] not in cache]
if LIMIT:
    todo = todo[:LIMIT]
print(f"scannable: {len(exp)}  cached: {len(cache)}  to-scan: {len(todo)}", flush=True)

done = 0
with ThreadPoolExecutor(max_workers=12) as ex:
    for url, res in ex.map(scan, todo):
        if res is not None:
            cache[url] = res
        done += 1
        if done % 500 == 0:
            print(f"  {done}/{len(todo)}", flush=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
from collections import Counter
lv = Counter(v["level"] for v in cache.values())
print(f"\nsaved {cache_path.name}: {len(cache)} scanned. levels: {dict(lv)}")
top = Counter(f for v in cache.values() for f in v["flags"])
print("top flags:", dict(top.most_common(10)))
