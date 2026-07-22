# Claude Skill Search

**🌐 라이브: https://hoseonkwak.github.io/claude-skill-search/** (GitHub Pages · 정적 키워드 버전)
자연어 **의미검색**은 로컬 앱(`serve.py`) — 백엔드 호스팅은 별도 단계.

흩어진 Claude Skills(공식 마켓플레이스 + 커뮤니티 awesome-리스트)를 한 곳에서
**용도 기반으로 검색**하는 서비스. 경쟁 서비스 대부분이 "리스트 + 키워드"에서 멈춰
있는 반면, 이 프로젝트는 **AI 매칭 + 신뢰(티어) 신호**를 차별점으로 삼는다.

포지셔닝/경쟁분석은 기획 브리프 참고. 현재 **Phase 1 진행 중** —
자연어(의미) 검색이 로컬 앱으로 동작한다.

## 바로 실행 (의미 검색 앱)

```bash
~/skillsearch-venv/bin/python scripts/serve.py     # http://localhost:8000
```

한국어/영어로 하고 싶은 작업을 입력하면 뜻이 통하는 스킬을 유사도순으로 보여준다.
(임베딩 venv 부트스트랩은 아래 "재현" 참고)

## 현황 (Phase 0 — 2026-07-22)

씨앗 소스를 집계해 **2,520개 고유 스킬** 데이터셋 구축:

| 티어 | 수 | 설명 |
|------|----|------|
| `curated` (골드) | 544 | 공식 + 사람이 관리하는 awesome-리스트. 실제 설명 있음 |
| `catalog` (대량) | 1,976 | GitHub 대량 수집본. 설명 없음 → **enrichment 필요** |

> 발견: catalog 소스(chat2anyllm)는 GitHub에서 'skill' 레포를 긁은 덤프라
> 설명이 대부분 브랜치명(`main`/`master`)이다. 이는 "대량 덤프엔 품질 신호가
> 없다 → 우리의 강화 레이어가 가치"라는 논지를 데이터로 뒷받침한다.

## 씨앗 소스

- `anthropics/claude-plugins-official` (marketplace.json, 271개)
- awesome-claude-skills: `karanb192`, `travisvn`, `ComposioHQ`, `mingrath`, `Chat2AnyLLM`

## 구조

```
data/raw/           내려받은 원본 (marketplace.json, *.md)
data/skills.json    정규화·중복제거된 통합 데이터셋 (2,512개)
data/skills.csv     같은 데이터의 CSV
data/embeddings.npy 스킬 임베딩 (2512 x 256, L2 정규화)  [Phase 1]
data/embed_meta.json 모델·차원·id 순서                    [Phase 1]
data/stars.json     GitHub 스타/최근커밋 캐시 (상위 55 레포)  [Phase 1.5]
scripts/ingest.py      원본 → 정규화 데이터셋 (티어링, junk-desc/참고링크 필터, dedup)
scripts/build_site.py  데이터셋 → 자체완결 정적 키워드 검색 사이트
scripts/embed.py       데이터셋 → 임베딩 (model2vec 다국어 정적, torch 불필요)
scripts/enrich_stars.py GitHub 스타 수집(캐시, 레이트리밋 안전) → data/stars.json
scripts/enrich_skillmd.py 카탈로그 SKILL.md 설명 수집(트리 API+raw) → data/enrich.json
scripts/core.py        공용 검색 코어: 하이브리드(의미+BM25+용어확장) + 인기 Best (+카테고리 필터)
scripts/ui.py          공용 프론트 디자인 시스템(라이트/다크, 히어로+리더보드) — serve/build 공유
scripts/search.py      CLI 하이브리드 검색 (단건 질의)
scripts/demo_search.py KO/EN 배치 데모 + Best
scripts/serve.py       로컬 웹앱 (stdlib http, /api/search + /api/best, 첫 화면 Best)
site/index.html     standalone 키워드 검색 (브라우저로 바로 열기)
site/artifact.html  body-only fragment (claude.ai 아티팩트 배포용)
```

## 재현

```bash
# 0) 임베딩용 venv 부트스트랩 (이 환경엔 pip이 없어 get-pip 사용) — 최초 1회
python3 -m venv --without-pip ~/skillsearch-venv
curl -sSL https://bootstrap.pypa.io/get-pip.py | ~/skillsearch-venv/bin/python -
~/skillsearch-venv/bin/pip install numpy model2vec
VP=~/skillsearch-venv/bin/python

# 1) 씨앗 소스는 data/raw/ 에 이미 포함 (marketplace.json + awesome-list README 5개)
# 2) 정규화 데이터셋
$VP scripts/ingest.py
# 3) 정적 키워드 사이트
$VP scripts/build_site.py
# 4) 임베딩 계산 (다국어 모델 최초 1회 다운로드)
$VP scripts/embed.py
# 5) 의미 검색 앱 실행
$VP scripts/serve.py      # http://localhost:8000
```

## 로드맵

- [x] **Phase 0** — 씨앗 수집 + 정적 키워드 검색
- [x] **Phase 1** — 자연어(의미) 검색: 다국어 정적 임베딩 + 로컬 앱 (**Option A**)
- [x] **Phase 1.5** — 하이브리드 재랭킹 + 인기 Best + catalog enrichment(98%) **완료**
- [ ] **Phase 2** — SKILL.md 위험 스캔 · 유지보수 상태 뱃지 (**Option B**)
- [ ] **Phase 3** — GitHub 대량 확장 · MCP 통합 · 커뮤니티 (**Option C**)

### Phase 1.5 완료
- **하이브리드 검색** (`core.py`): 의미(임베딩 코사인) + 어휘(BM25) + KO→EN 용어확장.
  `깃 커밋 메시지`→commit-commands/commit-message, `슬라이드 발표자료`→presentation-builder
  등 이전 오답 교정됨.
- **인기 Best** (`enrich_stars.py`→`data/stars.json`): 실제 GitHub 스타순, 레포당 1개.
  첫 화면 기본 노출. 카드에 ⭐ 뱃지.
- **catalog enrichment** (`enrich_skillmd.py`→`data/enrich.json`): GitHub 트리 API로
  각 레포의 SKILL.md 위치를 찾아 raw로 `description` 파싱. **1,606개 중 1,568개(98%) 설명 확보**,
  `needs_enrichment` 1,609→41. (토큰 필요: `.gh_token`, 공개 읽기전용)

### 남은 일
- **더 강한 임베딩**: 다국어 sentence-transformer(mpnet) 또는 Voyage API (순수 한국어 질의)
- **스타 확장**: 현재 상위 55개 레포만 수집 → 토큰으로 전체 확대 (한도 5000/hr)
- **데이터 정리**: 남은 41개 무설명 처리, 템플릿 플레이스홀더(`{{...}}`) 설명 필터, 카테고리 정규화
- **신선도 뱃지**: 최근 커밋일(pushed_at) 노출 (stars.json에 이미 수집됨)
