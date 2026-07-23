#!/usr/bin/env python3
"""
Translate skill descriptions to Korean (DISPLAY only) -> data/desc_ko.json.
Offline via m2m100_418M. Skips already-Korean. Resumable. Shown skills first
(curated + high-star). Embeddings/search still use the ORIGINAL description.

Usage: translate.py [LIMIT]   (0 = all remaining)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
MODEL = "facebook/m2m100_418M"
BATCH = 16

skills = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))["skills"]
stars_json = json.loads((DATA / "stars.json").read_text(encoding="utf-8")) \
    if (DATA / "stars.json").exists() else {}
cache_path = DATA / "desc_ko.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

HAN = re.compile(r"[가-힣]")
CJK = re.compile(r"[一-鿿]")
JA = re.compile(r"[぀-ヿ]")


def is_korean(t):
    return len(HAN.findall(t)) >= max(3, int(len(t) * 0.15))


def src_lang(t):
    if JA.search(t):
        return "ja"
    if CJK.search(t):
        return "zh"
    return "en"


def stars(s):
    m = re.search(r"github\.com/([^/#?]+)/([^/#?]+)", s["url"] or "")
    return (stars_json.get(f"{m.group(1)}/{m.group(2)}", {}) or {}).get("stars") or 0 if m else 0


todo = [s for s in skills
        if s["description"] and not is_korean(s["description"]) and s["url"] not in cache]
todo.sort(key=lambda s: (s["tier"] == "curated", stars(s)), reverse=True)   # 보이는 것 먼저
if LIMIT:
    todo = todo[:LIMIT]
print(f"to translate: {len(todo)}  (cached {len(cache)})", flush=True)
if not todo:
    sys.exit(0)

print(f"loading {MODEL} ...", flush=True)
tok = M2M100Tokenizer.from_pretrained(MODEL)
model = M2M100ForConditionalGeneration.from_pretrained(MODEL)
model.eval()
torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
ko_id = tok.get_lang_id("ko")

def _save():
    tmp = cache_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(cache_path)   # atomic: ingest never reads a half-written file


groups = defaultdict(list)
for s in todo:
    groups[src_lang(s["description"])].append(s)

done = 0
for lang, items in groups.items():
    tok.src_lang = lang
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        enc = tok([s["description"][:400] for s in batch], return_tensors="pt",
                  padding=True, truncation=True, max_length=128)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=ko_id, max_length=160, num_beams=1)
        for s, o in zip(batch, tok.batch_decode(gen, skip_special_tokens=True)):
            cache[s["url"]] = o.strip()
        done += len(batch)
        if done % 192 < BATCH:
            _save()
            print(f"  {done}/{len(todo)}", flush=True)

_save()
print(f"done: {len([v for v in cache.values() if v])} translations cached", flush=True)
