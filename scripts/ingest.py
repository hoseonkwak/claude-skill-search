#!/usr/bin/env python3
"""
Phase 0 ingestion: parse seed sources (official marketplace + awesome-lists)
into one normalized skills dataset.

Input : data/raw/*.md , data/raw/official-marketplace.json
Output: data/skills.json , data/skills.csv , prints a summary
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

# markdown link:  [text](url)
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
HEADER = re.compile(r"^(#{2,4})\s+(.*?)\s*#*$")
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⌀-⏿]"
)

# section titles that are NOT skill listings -> skip their entries
SKIP_SECTION = re.compile(
    r"resourc|contribut|licen|table of contents|related|acknowledg|star history|"
    r"directori|marketplace|install|getting started|how to|about|community|"
    r"credit|sponsor|disclaimer|faq|what (is|are)|why |sources?$",
    re.I,
)


def clean(text: str) -> str:
    text = re.sub(r"[�\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "")  # U+FFFD + control chars
    text = EMOJI.sub("", text)
    text = re.sub(r"[*_`]+", "", text)          # markdown emphasis
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" -–—:|")


def strip_desc(text: str) -> str:
    # remove a leading markdown link, then leading separators
    text = LINK.sub("", text, count=0)
    text = re.sub(r"^[\s\-–—:•|]+", "", clean(text))
    return text.strip()


def norm_url(url: str) -> str:
    url = url.rstrip("/").split("#")[0].split("?")[0]
    return re.sub(r"^https?://(www\.)?", "", url).lower()


def repo_of(url: str):
    m = re.search(r"github\.com/([^/#?]+)/([^/#?]+)", url or "", re.I)
    return f"{m.group(1)}/{m.group(2).replace('.git', '')}" if m else None


def dedup_key(name: str, url: str) -> str:
    return f"{re.sub(r'[^a-z0-9]', '', name.lower())}|{norm_url(url)}"


# curated = human-maintained lists; catalog = bulk auto-scraped dumps
CURATED = {"official", "karanb192", "travisvn", "composio", "mingrath"}
# descriptions that are actually a git ref / generic dir name, not a description
JUNK_DESC = {"main", "master", "skills", "skill", "dev", "develop", "src",
             "plugins", "plugin", "root", "readme"}

# generic/unfilled SKILL.md templates that aren't a real description
_PLACEHOLDER_TEXT = {"description", "skill description", "your description here",
                     "your skill description", "tbd", "todo", "n/a", "na", "..."}


def is_placeholder(d):
    if not d:
        return True
    if "{{" in d or "}}" in d:                       # unfilled {{...}} template
        return True
    dl = d.strip().lower()
    if dl.startswith("<") and dl.endswith(">"):       # <placeholder>
        return True
    return dl in _PLACEHOLDER_TEXT or len(dl) < 4


records = []

# non-installable reference links (docs/news/marketing) that lists mix in — not skills
BLOCK_HOST = (
    "docs.claude.com", "docs.anthropic.com", "support.anthropic.com",
    "anthropic.com/news", "claude.ai", "code.claude.com", "youtube.com",
    "youtu.be", "twitter.com", "x.com", "reddit.com", "medium.com",
)


def add(name, url, desc, category, source_list, author=None, verified=None):
    name, desc, category = clean(name), clean(desc), clean(category)
    if not name or not url or len(name) > 80:
        return
    if url.rstrip("/") == name.rstrip("/"):      # bare url as name -> skip
        return
    if any(norm_url(url).startswith(h) for h in BLOCK_HOST):   # reference link, not a skill
        return
    if desc.lower() in JUNK_DESC or len(desc) < 4:   # ref/branch masquerading as desc
        desc = ""
    tier = "curated" if source_list in CURATED else "catalog"
    records.append(
        dict(name=name, url=url, description=desc, category=category or "Uncategorized",
             author=author, verified=verified, source_list=source_list, tier=tier)
    )


# chat2anyllm "Source Catalog" table: Repository | Skills | Branch | Path | Status | Note
CAT_ROW = re.compile(
    r"\|\s*\[([^\]]+)\]\((https://github\.com/[^)\s]+)\)\s*\|\s*(\d+)\s*\|\s*`([^`]*)`\s*\|\s*`([^`]*)`")


def parse_catalog(md_path):
    for ln in md_path.read_text(encoding="utf-8").splitlines():
        m = CAT_ROW.match(ln.strip())
        if not m:
            continue
        n = int(m.group(3))
        if n < 1:                       # 0 skills -> not an actual skill, drop
            continue
        records.append(dict(
            name=clean(m.group(1)), url=m.group(2), description="",
            category="Source Catalog", author=None, verified=None,
            source_list="chat2anyllm", tier="catalog",
            branch=m.group(4) or "main", path=m.group(5) or ".", n_skills=n))


# ---------- 1. official marketplace.json ----------
data = json.loads((RAW / "official-marketplace.json").read_text(encoding="utf-8"))
for p in data.get("plugins", []):
    src = p.get("source")
    src_url = src.get("url") if isinstance(src, dict) else (src if isinstance(src, str) else "")
    url = p.get("homepage") or src_url or ""
    add(p.get("name", ""), url, p.get("description", ""), p.get("category", ""),
        "official", author=(p.get("author") or {}).get("name"), verified=True)

# ---------- 2. awesome-list markdown ----------
for md in sorted(RAW.glob("*.md")):
    source = md.stem
    if source == "chat2anyllm":         # dedicated catalog-table parser (branch/path/skills)
        parse_catalog(md)
        continue
    section = "Uncategorized"
    for line in md.read_text(encoding="utf-8").splitlines():
        h = HEADER.match(line)
        if h:
            section = clean(h.group(2))
            continue
        if SKIP_SECTION.search(section):
            continue

        stripped = line.strip()
        # table row: | [name](url) | description | ... |
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 2 or set("".join(cells)) <= set("-: "):
                continue
            if cells[0].lower() in ("skill", "name", "plugin"):
                continue
            m = LINK.search(cells[0])
            if not m:
                continue
            # description = longest non-link cell after the first
            rest = [strip_desc(c) for c in cells[1:]]
            desc = max(rest, key=len) if rest else ""
            verified = "✅" in line or "✓" in line
            add(m.group(1), m.group(2), desc, section, source, verified=verified or None)
            continue

        # bullet row: - [name](url) - description
        if re.match(r"^[-*] ", stripped):
            m = LINK.search(stripped)
            if not m:
                continue
            after = stripped[m.end():]
            add(m.group(1), m.group(2), strip_desc(after), section, source)

# ---------- 2b. GitHub expansion (expand_github.py) ----------
exp_path = OUT / "expanded.json"
if exp_path.exists():
    for r in json.loads(exp_path.read_text(encoding="utf-8")).get("skills", []):
        nm, url = clean(r.get("name", "")), r.get("url", "")
        if not nm or not url or len(nm) > 80:
            continue
        records.append(dict(
            name=nm, url=url, description=clean(r.get("description", "")),
            category=r.get("category") or "Source Catalog", author=None, verified=None,
            source_list="github-expand", tier="catalog",
            branch=r.get("branch"), path=r.get("path"), n_skills=None))


# ---------- 3. merge / dedup ----------
merged = {}
for r in records:
    k = dedup_key(r["name"], r["url"])
    if k not in merged:
        merged[k] = dict(r, sources=[r["source_list"]])
        merged[k].pop("source_list")
    else:
        m = merged[k]
        if r["source_list"] not in m["sources"]:
            m["sources"].append(r["source_list"])
        if len(r["description"]) > len(m["description"]):
            m["description"] = r["description"]
        if r.get("verified") and not m.get("verified"):
            m["verified"] = True
        if not m.get("author") and r.get("author"):
            m["author"] = r["author"]
        if r["tier"] == "curated":               # any curated source upgrades tier
            m["tier"] = "curated"

skills = sorted(merged.values(),
                key=lambda s: (s["tier"] != "curated", -len(s["sources"]), s["name"].lower()))

# apply SKILL.md descriptions harvested by enrich_skillmd.py (if present)
enrich = json.loads((OUT / "enrich.json").read_text(encoding="utf-8")) \
    if (OUT / "enrich.json").exists() else {}
dko = json.loads((OUT / "desc_ko.json").read_text(encoding="utf-8")) \
    if (OUT / "desc_ko.json").exists() else {}          # 한글 번역본(display용)
n_enriched = 0
for s in skills:
    s.pop("source_list", None)
    if is_placeholder(s["description"]):             # drop template/placeholder descriptions
        s["description"] = ""
    e = enrich.get(repo_of(s["url"]) or "")
    if e and e.get("desc") and not is_placeholder(e["desc"]) and not s["description"]:
        s["description"] = e["desc"]
        s["enriched"] = True
        n_enriched += 1
    s["description"] = re.sub(r"[�\x00-\x08\x0b\x0c\x0e-\x1f]", "", s["description"])  # sanitize
    c = s["category"]                                # normalize casing (official uses lowercase)
    if c and c.islower():
        s["category"] = c[0].upper() + c[1:]
    s["needs_enrichment"] = not bool(s["description"])
    s["desc_ko"] = dko.get(s["url"], "")                # 한글 번역(없으면 원문 표시)

for i, s in enumerate(skills, 1):              # stable id
    s["id"] = i

# ---------- 4. write ----------
OUT.mkdir(exist_ok=True)
(OUT / "skills.json").write_text(
    json.dumps({"generated": "2026-07-22", "count": len(skills), "skills": skills},
               ensure_ascii=False, indent=2), encoding="utf-8")

with (OUT / "skills.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "tier", "category", "description", "url", "author",
                "verified", "needs_enrichment", "sources"])
    for s in skills:
        w.writerow([s["id"], s["name"], s["tier"], s["category"], s["description"], s["url"],
                    s.get("author") or "", s.get("verified") or "",
                    s["needs_enrichment"], ";".join(s["sources"])])

# ---------- 5. summary ----------
curated = [s for s in skills if s["tier"] == "curated"]
catalog = [s for s in skills if s["tier"] == "catalog"]
print(f"raw entries parsed : {len(records)}")
print(f"unique skills      : {len(skills)}")
print(f"  curated (gold)   : {len(curated)}   (real descriptions, human-maintained)")
print(f"  catalog (bulk)   : {len(catalog)}   (needs enrichment)")
print(f"enriched via SKILL.md: {n_enriched}")
print(f"needs enrichment   : {sum(1 for s in skills if s['needs_enrichment'])}  "
      f"(missing/junk description)")
print(f"multi-source skills: {sum(1 for s in skills if len(s['sources']) > 1)}")

per_source = Counter()
for s in skills:
    for src in s["sources"]:
        per_source[src] += 1
print("\nby source list:")
for k, v in per_source.most_common():
    print(f"  {k:14s} {v}")

print("\ntop categories (curated tier only):")
for k, v in Counter(s["category"] for s in curated).most_common(12):
    print(f"  {v:4d}  {k[:40]}")

print("\nsample CURATED skills:")
for s in curated[:10]:
    d = s["description"][:58] or "(no desc)"
    print(f"  [{','.join(s['sources'])}] {s['name']} — {d}")
