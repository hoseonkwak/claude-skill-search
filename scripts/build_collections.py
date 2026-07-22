#!/usr/bin/env python3
"""
Build use-case collections by auto-populating each theme via semantic search.
Output: data/collections.json  { "collections": [{id,emoji,name,query,urls:[...]}] }
(Module NOT named 'collections' to avoid shadowing stdlib in core.py.)
"""
import json
import re

import core

COLLECTIONS = [
    {"id": "cardnews", "emoji": "🎨", "name": "카드뉴스·SNS 콘텐츠",
     "query": "카드뉴스 SNS 소셜미디어 콘텐츠 이미지 생성 그래픽 브랜드 디자인 카피라이팅"},
    {"id": "landing", "emoji": "🌐", "name": "랜딩페이지 하루 완성",
     "query": "랜딩페이지 웹사이트 프론트엔드 UI 컴포넌트 디자인 시스템 wireframe html css"},
    {"id": "fullstack", "emoji": "💻", "name": "풀스택 앱 스타터",
     "query": "풀스택 웹앱 개발 backend database schema API authentication 배포"},
    {"id": "office", "emoji": "📄", "name": "오피스 문서 자동화",
     "query": "문서 자동화 PDF Word Excel PowerPoint docx xlsx pptx 요약 번역"},
    {"id": "deck", "emoji": "🎤", "name": "발표·피치덱",
     "query": "발표자료 슬라이드 프레젠테이션 피치덱 presentation slides pptx"},
    {"id": "review", "emoji": "🔍", "name": "코드리뷰·품질",
     "query": "코드 리뷰 품질 pull request 정적분석 테스트 code review quality lint"},
    {"id": "security", "emoji": "🛡️", "name": "보안 점검",
     "query": "보안 취약점 스캔 의존성 시크릿 security vulnerability scan OWASP semgrep"},
    {"id": "data", "emoji": "📊", "name": "데이터 분석·리서치",
     "query": "데이터 분석 시각화 차트 스프레드시트 SQL 리서치 data analysis visualization"},
    {"id": "devops", "emoji": "🚀", "name": "DevOps·배포",
     "query": "DevOps 배포 CI CD docker container kubernetes cloud AWS 모니터링 deployment"},
    {"id": "vibe", "emoji": "🐣", "name": "바이브코딩 입문",
     "query": "코딩 입문 초보 디버깅 git 워크플로우 커밋 테스트 TDD debugging beginner"},
]

_REPO = re.compile(r"github\.com/([^/#?]+)/([^/#?]+)", re.I)


def repo_of(url):
    m = _REPO.search(url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else url


out = []
for c in COLLECTIONS:
    res = core.search(c["query"], tier="all", k=80)
    seen, urls = set(), []
    for r in res:
        if not r["desc"]:
            continue
        rp = repo_of(r["url"])
        if rp in seen:
            continue
        seen.add(rp)
        urls.append(r["url"])
        if len(urls) >= 15:
            break
    out.append({"id": c["id"], "emoji": c["emoji"], "name": c["name"],
                "query": c["query"], "urls": urls})
    print(f"  {c['emoji']} {c['name']}: {len(urls)} skills", flush=True)

(core.DATA / "collections.json").write_text(
    json.dumps({"collections": out}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved collections.json ({len(out)} collections)")
