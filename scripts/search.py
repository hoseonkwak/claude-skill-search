#!/usr/bin/env python3
"""CLI hybrid search.  python scripts/search.py [--tier curated] [--k 8] "질의" """
import argparse

import core

ap = argparse.ArgumentParser()
ap.add_argument("query", nargs="+")
ap.add_argument("--k", type=int, default=10)
ap.add_argument("--tier", choices=["all", "curated", "catalog"], default="all")
args = ap.parse_args()
query = " ".join(args.query)

print(f'\n🔎  "{query}"   (expanded: "{core.expand(query)}", tier={args.tier})\n' + "─" * 70)
for r in core.search(query, args.tier, args.k):
    tier = "🟢" if r["tier"] == "curated" else "⚠ "
    star = f"⭐{r['stars']}" if r["stars"] is not None else ""
    print(f"{r['score']:.3f} {tier} {r['name'][:36]:36s} {star}")
    print(f"        {(r['desc'] or '(no description — needs enrichment)')[:92]}")
print("─" * 70)
