#!/usr/bin/env python3
"""
Compute skill embeddings. Two backends:
  embed.py            -> sentence-transformers (multilingual, stronger; default)
  embed.py m2v        -> model2vec static (fast, weaker; fallback)

Output: data/embeddings.npy (float32, L2-normalized) + data/embed_meta.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODE = sys.argv[1] if len(sys.argv) > 1 else "st"
ST_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

data = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))
skills = data["skills"]


def skill_text(s):
    parts = [s["name"]]
    if s["description"]:
        parts.append(s["description"])
    parts.append(f"category: {s['category']}")
    return ". ".join(parts)


texts = [skill_text(s) for s in skills]

if MODE == "m2v":
    from model2vec import StaticModel
    name = "minishlab/potion-multilingual-128M"
    backend = "model2vec"
    print(f"loading {name} (model2vec) ...", flush=True)
    model = StaticModel.from_pretrained(name)
    parts = [np.asarray(model.encode(texts[i:i + 1000]), dtype=np.float32)
             for i in range(0, len(texts), 1000)]        # batch: lower peak memory (free host)
    emb = np.vstack(parts) if parts else np.zeros((0, 256), dtype=np.float32)
else:
    from sentence_transformers import SentenceTransformer
    name = ST_MODEL
    backend = "sentence-transformers"
    print(f"loading {name} (sentence-transformers) ...", flush=True)
    model = SentenceTransformer(name)
    print(f"encoding {len(texts)} skills ...", flush=True)
    emb = model.encode(texts, batch_size=64, convert_to_numpy=True,
                       show_progress_bar=True, normalize_embeddings=False).astype(np.float32)

norms = np.linalg.norm(emb, axis=1, keepdims=True)
norms[norms == 0] = 1.0
emb = emb / norms

np.save(DATA / "embeddings.npy", emb)
(DATA / "embed_meta.json").write_text(json.dumps({
    "model": name, "backend": backend, "dim": int(emb.shape[1]),
    "count": int(emb.shape[0]), "ids": [s["id"] for s in skills],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved embeddings.npy shape={emb.shape} backend={backend} model={name}")
