# CLAUDE.md — Skill Finder 프로젝트 설명서

> 이 파일은 세션마다 자동 로드됩니다. **다시 열어도 여기부터 이어서** 작업하세요.
> 상세 설계/근거는 `docs/` 참고.

## 한 줄 소개
흩어진 **Claude Skills**(공식 마켓 + 커뮤니티 + GitHub 확장)를 한데 모아 **용도 기반 의미검색**하는
디렉토리/검색 서비스. 신뢰도(티어·안전·신선도·스타)를 함께 보여주는 게 차별점.

## 라이브 / 링크
- **공개(정적, 키워드검색)**: https://hoseonkwak.github.io/claude-skill-search/ (GitHub Pages, `main:/docs`)
- **아티팩트(같은 정적본)**: https://claude.ai/code/artifact/d64365ec-3a10-483a-9b11-08869b21f62d
- **GitHub**: https://github.com/hoseonkwak/claude-skill-search (branch `main`)
- **의미검색(최상 품질)**: 로컬 `serve.py` → http://localhost:8000 *(공개 배포는 아래 "결정" 참고로 보류)*

## 현재 상태 (2026-07-23)
- 스킬 **11,965개** (6개 소스 집계·중복제거). 스타 있는 것 ~11.8k, 안전 스캔 9,691개.
- 기능: 하이브리드 의미검색(로컬), 정적 키워드검색(공개), 인기 Best, **분야 카드 그리드 + 목적 컬렉션**,
  카드별 **"사용법" 펼침**, 원클릭 **설치 복사**, 안전/신선도/검증/스타 **뱃지**, **한글 번역**(+원문 토글),
  라이트/네이비-다크 + 테마 토글, 로고→홈.
- **한글 번역 진행 중**: `translate.py`가 백그라운드로 채우는 중 (~4.4k/11,965, CPU라 ~1개/초).
  더 채우려면 재수집+재빌드(아래).
- 남은 일: `TODO.md` 참고.

---

## ⚙️ 어떻게 실행하나 (제일 중요)

**모든 파이썬 스크립트는 전용 venv로 실행**: `~/skillsearch-venv/bin/python`
(이 환경엔 시스템 pip이 없어 get-pip로 부트스트랩함. venv엔 numpy, model2vec,
sentence-transformers, torch(CPU), sentencepiece, huggingface_hub 설치됨.)

```bash
cd /mnt/e/kwak/dev/claude-skill-search
VP=~/skillsearch-venv/bin/python

# 로컬 의미검색 앱 (한국어 자연어 검색 최상 품질)
$VP scripts/serve.py            # → http://localhost:8000  (페이지 + /api/*)

# 데이터/UI 바꾼 뒤 공개 사이트 갱신하는 표준 순서:
python3 scripts/ingest.py           # 원본→data/skills.json (번역·enrich 병합, 정리, 티어링)
$VP    scripts/embed.py             # skills.json→embeddings.npy (ST 384d)  ※스킬 집합 바뀔 때만
$VP    scripts/build_collections.py # 카테고리/컬렉션 재생성 (랭킹 바꿨을 때)
python3 scripts/build_site.py       # site/index.html + site/artifact.html + docs/index.html(Pages)
# 그다음: git commit/push (Pages 자동배포) + Artifact 재게시(같은 파일경로)
```

**로컬 serve.py 재기동** (셸 자기매칭 주의 — `pkill -f serve.py`는 셸까지 죽여 exit 143):
```bash
VP=~/skillsearch-venv/bin/python
for p in /proc/[0-9]*; do c=$(tr '\0' ' ' </$p/cmdline 2>/dev/null)||continue; case "$c" in "$VP "*serve.py*) kill ${p#/proc/};; esac; done
sleep 1; $VP scripts/serve.py 8000 >/tmp/skillsrv.log 2>&1 & disown
```

**GitHub push**: 자격 헬퍼가 없어 `.gh_token`(repo 권한)으로 인증:
```bash
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!f(){ echo username=hoseonkwak; echo "password=$(cat .gh_token)"; }; f' push
```

## 📁 구조
```
scripts/
  ingest.py            원본(data/raw/*) → skills.json (티어링·junk/참고링크 필터·dedup·enrich/번역 병합)
  embed.py [st|m2v]    skills.json → embeddings.npy (+meta). 기본 st(=sentence-transformers 384d)
  core.py              공용 검색 코어: 하이브리드(의미+BM25+KO→EN 용어확장+인기가산) / best / collection
  ui.py                공용 프론트 디자인시스템(HTML/CSS/JS) — serve.py·build_site.py 공유
  serve.py             로컬 웹앱: 페이지 + /api/search|best|collection (PORT env, CORS)
  build_site.py        정적 사이트 생성 (site/ + docs/index.html for Pages)
  build_collections.py 분야(field)·목적(goal) 컬렉션 자동 구성 → collections.json
  enrich_stars.py      GitHub 스타/최근커밋 수집 → stars.json (토큰)
  enrich_skillmd.py    카탈로그 SKILL.md 설명 수집 → enrich.json (토큰, 트리 API)
  expand_github.py     GitHub 레포 검색으로 스킬 대량 확장 → expanded.json (토큰)
  scan_safety.py       SKILL.md 위험 휴리스틱 스캔 → safety.json
  translate.py         설명 중/영→한글 (오프라인 m2m100) → desc_ko.json (표시용, 백그라운드)
  search.py/demo_search.py  CLI 검색/데모
data/
  raw/                 씨앗 원본 (marketplace.json + awesome-list *.md)
  skills.json          정규화 통합 데이터셋(11,965)  ★ 소스오브트루스
  embeddings.npy       ST 임베딩 (11965×384)  ※embed.py로 재생성
  embed_meta.json      backend/dim/count/ids
  stars.json safety.json enrich.json expanded.json collections.json desc_ko.json
site/                  standalone(index.html) + artifact fragment
docs/                  GitHub Pages 소스(index.html+.nojekyll) + 설계문서(*.md)
README.md TODO.md CLAUDE.md
```

## 🔑 환경 · 토큰
- venv: `~/skillsearch-venv` (재현: `docs/ARCHITECTURE.md` 참고)
- `.gh_token` — GitHub **repo** 권한 토큰(push용). **gitignore됨.**
- `.hf_token` — Hugging Face 토큰. **지금은 안 씀 → revoke 권장.** gitignore됨.
- 토큰은 채팅에 붙여넣지 말고 `! echo '토큰' > .gh_token` 처럼 넣기.

## 🧭 핵심 결정 (왜)
- **임베딩 = sentence-transformers MiniLM-L12 다국어(384d)** — 순수 한국어 질의 품질 때문(model2vec 정적보다 나음).
  검색은 원문(영어) 임베딩, 번역은 표시용.
- **공개 배포 보류 → 로컬 전용** — 다국어 임베딩 모델이 **~1.65GB RAM** 필요. 무료 호스트(512MB)·무료 HF Docker(이제 PRO)
  모두 불가. 유료(HF PRO $9/월 또는 2GB 인스턴스)면 `serve.py` 그대로 5분이면 올림.
- **카테고리 랭킹** — 수동 앵커(유명 스킬 포함 보장) + **모노레포(스타>55k) 자동채움 제외**(anthropics/skills가 엉뚱한 카테고리 잠식 방지)
  + 관련성 게이트 + **스타(인기)순**. 앵커도 스타순에 섞임(억지로 맨 위 X). `build_collections.py`의 `ANCHORS`로 조정.
- **디자인 = 모던 애플풍**(흰 배경 / 네이비 다크 / Claude 코랄 포인트). cobalt·필드가이드 시안은 "AI 티" 사유로 폐기.
  근거·공식: `docs/FRIENDLY-HOMEPAGE.md`, `docs/VISUAL-DESIGN-PLAYBOOK.md`.

## ⚠️ 주의 (gotchas)
- **`embed.py m2v`를 로컬에서 돌리지 말 것** — embeddings.npy를 model2vec(256d)로 덮어써 로컬 ST 품질이 깨짐.
  m2v는 폐기된 배포 실험용이었음. 로컬은 항상 `embed.py`(=st).
- **desc_ko는 표시용** — 번역이 바뀌어도 재임베딩 불필요. `ingest.py` 재실행으로 skills.json에 반영 → `build_site.py`로 노출.
- **translate.py는 원자적 저장** — 백그라운드로 desc_ko.json 갱신 중 재수집해도 안전.
- **스킬 집합이 안 바뀌면 embed 재실행 불필요** (임베딩 순서=skills.json 순서, ids 일치).
- Pages는 `main:/docs`. `build_site.py`가 docs/index.html+.nojekyll을 씀 (docs/의 다른 .md는 안 건드림).

## ▶️ 다음에 할 만한 것 (상세는 TODO.md)
- 번역 완주 후 재빌드(공개 사이트 한글 더 채움).
- 카드 "사용법" **진한 버전**: SKILL.md에서 실제 사용예시 발췌(재수집+번역).
- Option B 안전 스캔을 curated/chat2anyllm 카탈로그로 확장, 오탐↓.
- (원하면) 유료로 의미검색 백엔드 공개 배포.
- Housekeeping: HF 토큰 revoke, 실패한 Render 서비스 삭제.
