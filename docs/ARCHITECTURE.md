# ARCHITECTURE — 심화 기술 문서

> 개요·실행법은 루트 `CLAUDE.md`. 이 문서는 파이프라인 내부·재현·알고리즘·스키마.

## 1. 데이터 파이프라인 (빌드 순서)
```
data/raw/*  (씨앗: 공식 marketplace.json + awesome-list README 5개)
   │  + enrich.json (SKILL.md 설명)  + expanded.json (GitHub 확장)  + desc_ko.json (번역)
   ▼ ingest.py
data/skills.json  (11,965 · 티어링 curated/catalog · junk/참고링크·플레이스홀더 필터 · dedup · 카테고리 casing)
   ▼ embed.py (기본 st)
data/embeddings.npy (11965×384, L2정규화)  + embed_meta.json (backend·dim·ids)
   ▼ build_collections.py (core.search 사용)
data/collections.json  (목적 10 + 분야 12, 각 ~18개 url)
   ▼ build_site.py                      ▼ serve.py (임포트: core.py)
site/*, docs/index.html (정적·키워드)     로컬 웹앱 (하이브리드 의미검색 API)
```
보조 수집기(토큰 필요): `enrich_stars.py`(stars.json) · `enrich_skillmd.py`(enrich.json) ·
`expand_github.py`(expanded.json) · `scan_safety.py`(safety.json) · `translate.py`(desc_ko.json).

## 2. venv 재현 (시스템 pip 없을 때)
```bash
python3 -m venv --without-pip ~/skillsearch-venv
curl -sSL https://bootstrap.pypa.io/get-pip.py | ~/skillsearch-venv/bin/python -
~/skillsearch-venv/bin/pip install numpy model2vec sentence-transformers sentencepiece huggingface_hub
~/skillsearch-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## 3. 검색 랭킹 (`core.py`)
- **하이브리드**: `final = 0.78·norm(semantic) + 0.22·norm(lexical) [+ pop 부스트]`
  - semantic: **원문 질의**를 ST로 인코딩 → 임베딩 코사인 (다국어라 한국어 직접 이해)
  - lexical: **KO→EN 글로서리로 확장한 질의** 토큰의 BM25 (라틴 키워드 매칭 보강)
  - pop(사용자 검색만, `pop=True`): `+0.035·log10(min(stars,80k)+1)` — 관련 있는 인기 스킬을 위로
- **best**: 설명+스타 있는 것 중 스타순, 레포당 1개, 메타레포(cookbooks 등) 제외
- **collection** (`build_collections.py`): 카테고리별로
  1) `ANCHORS`(유명 스킬 키워드) → `find_anchor`로 전체 데이터에서 최고스타 매치 포함 보장
  2) 관련성 게이트: 의미검색 상위 35(부족하면 70) & score≥top·0.80(부족하면 0.62) & **stars≤55k(모노레포 제외)**
  3) 앵커+게이트를 **스타순** 정렬 → 레포당1·오너당≤2 dedup → 18개
  - 스타 상한 없이 실제 스타순이라 259k가 89k 앵커보다 위. 모노레포 제외가 wireframe-to-code 같은 오침투 차단.

## 4. 안전 스캔 (`scan_safety.py`)
- 각 스킬 SKILL.md(raw)에서 휴리스틱:
  - **risk**: 쉘 파이프 실행(`curl|sh`), `rm -rf /`, base64 실행, 프롬프트 인젝션, 원격 eval
  - **caution**: 네트워크 호출, 시크릿 접근, sudo, chmod 777, 쉘 실행
  - 등급은 flags에서 재계산(risk 세트 포함 여부). secret+network 조합은 오탐 많아 caution으로.
- 현재 확장분 9,691개만 스캔(정확 경로 보유). curated·chat2anyllm은 미스캔(risk=null).
- **참고용**(오탐/미탐 가능) — 푸터에 명시.

## 5. 번역 (`translate.py`)
- 오프라인 **m2m100_418M**(sentencepiece 필요). 한글 아님(hangul 비율<15%)만 대상, 소스언어 감지(zh/ja/en).
- 우선순위: curated + 고스타(=보이는 것) 먼저. 재개 가능, 원자적 저장. CPU ~1개/초.
- **표시용만** — 임베딩/검색은 원문. UI는 `desc_ko` 있으면 한글 + "원문" 토글.

## 6. 주요 데이터 스키마
`skills.json.skills[]`: `id,name,url,description,desc_ko,category,tier(curated|catalog),
author,verified,sources[],needs_enrichment,(branch,path,n_skills for catalog)`
`stars.json`: `{ "owner/repo": {stars,pushed,archived} }`
`safety.json`: `{ url: {level, flags[]} }`
`collections.json.collections[]`: `{id,emoji,name,query,group(goal|field),urls[]}`
`desc_ko.json`: `{ url: "한글설명" }`

## 7. 재배포 체크리스트
1. 데이터 바꿈 → `ingest.py` (→ 스킬집합 바뀌면 `embed.py`, 랭킹 바뀌면 `build_collections.py`)
2. `build_site.py`
3. `git add -A` → **시크릿 스테이징 확인**(`.gh_token/.hf_token` 안 들어갔는지) → commit → push (Pages 자동)
4. Artifact 재게시(같은 file_path → 같은 URL)
5. 로컬 `serve.py` 재기동(위 gotcha)
