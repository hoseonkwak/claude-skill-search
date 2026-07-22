#!/usr/bin/env python3
"""Showcase: batch KO/EN queries through the hybrid index; plus the Best list."""
import core

QUERIES = [
    "pdf에서 표를 뽑아서 정리하고 싶어",
    "코드 리뷰 자동화",
    "웹사이트 보안 취약점 점검",
    "깃 커밋 메시지 잘 쓰기",
    "슬라이드 발표자료 만들기",
    "make presentation slide decks",
    "데이터베이스 스키마 마이그레이션",
    "react frontend UI components",
]

print(f"model={core.META['model']}  skills={len(core.SKILLS)}  hybrid=semantic+BM25+glossary\n")
for q in QUERIES:
    print(f'🔎  "{q}"   →  expand: "{core.expand(q)}"')
    for r in core.search(q, "all", 4):
        tier = "🟢" if r["tier"] == "curated" else "⚠ "
        star = f"⭐{r['stars']}" if r["stars"] is not None else ""
        print(f"    {r['score']:.3f} {tier} {r['name'][:34]:34s} {(r['desc'] or '(no desc)')[:52]} {star}")
    print()

print("🔥 인기 Best (top 8, GitHub 스타순)")
for i, r in enumerate(core.best("all", 8), 1):
    print(f"  {i:2d}. ⭐{r['stars']:>7,}  {r['name'][:34]:34s} {(r['desc'] or '')[:46]}")
