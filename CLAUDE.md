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
  카테고리 클릭 시 **비포/애프터 패널**("이걸 쓰면 이렇게 바뀌어요"), 카드별 **"사용법" 펼침**,
  원클릭 **설치 복사**, 안전/신선도/검증/스타 **뱃지**, 라이트/네이비-다크 + 테마 토글, 로고→홈.
- **설명은 원문(영어) 그대로 노출** — 기계번역 표시는 중단(아래 "핵심 결정" 참고).
  `data/desc_ko.json`(8,634개)은 보관만 하고 화면·페이로드에 싣지 않음.
- 남은 일: `TODO.md` 참고.

---

## ⚙️ 어떻게 실행하나 (제일 중요)

**환경 = Windows 네이티브** (WSL 안 씀). 모든 파이썬 스크립트는 **프로젝트 venv**로 실행:
`.venv\Scripts\python.exe` (Python 3.11 · numpy, sentence-transformers, torch(CPU),
sentencepiece, transformers, huggingface_hub 설치됨). 재현은 `docs/ARCHITECTURE.md` §2.

```powershell
cd E:\kwak\dev\claude-skill-search
$VP = ".\.venv\Scripts\python.exe"

# 로컬 의미검색 앱 (한국어 자연어 검색 최상 품질)
& $VP scripts\serve.py          # → http://localhost:8000  (페이지 + /api/*)

# 데이터/UI 바꾼 뒤 공개 사이트 갱신하는 표준 순서:
& $VP scripts\ingest.py             # 원본→data/skills.json (번역·enrich 병합, 정리, 티어링)
& $VP scripts\embed.py              # skills.json→embeddings.npy (ST 384d)  ※스킬 집합 바뀔 때만
& $VP scripts\build_collections.py  # 카테고리/컬렉션 재생성 (랭킹 바꿨을 때)
& $VP scripts\build_site.py         # site/index.html + site/artifact.html + docs/index.html(Pages)
# 그다음: git commit/push (Pages 자동배포) + Artifact 재게시(같은 파일경로)
```

**로컬 serve.py 재기동** (PowerShell — 명령줄로 프로세스 식별해 종료):
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*serve.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "scripts\serve.py","8000" -WindowStyle Hidden
```
(Claude Code 안에서는 `run_in_background: true`로 띄우는 게 로그 보기 편함.)

**GitHub push**: Windows 자격 관리자(`credential.helper=manager`)가 있어 보통 `git push`면 끝.
안 되면 Bash 툴(**Git Bash** — WSL 아님)에서 `.gh_token`(repo 권한)으로:
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
  category_demos.json  카테고리(컬렉션 id)별 비포/애프터 문구 {bi,before,ai,after} — 손으로 큐레이션, UI 전용
site/                  standalone(index.html) + artifact fragment
docs/                  GitHub Pages 소스(index.html+.nojekyll) + 설계문서(*.md)
README.md TODO.md CLAUDE.md
```

## 🔑 환경 · 토큰
- OS: **Windows 네이티브** (PowerShell / Git Bash). WSL은 더 이상 쓰지 않음.
- venv: `.venv` (프로젝트 안, gitignore됨 · 재현: `docs/ARCHITECTURE.md` §2)
- 모델 캐시: `%USERPROFILE%\.cache\huggingface`
- `.gh_token` — GitHub **repo** 권한 토큰(push용). **gitignore됨.**
- `.hf_token` — Hugging Face 토큰. **지금은 안 씀 → revoke 권장.** gitignore됨.
- 토큰은 채팅에 붙여넣지 말고 `! echo '토큰' > .gh_token` 처럼 넣기.

## 🧭 핵심 결정 (왜)
- **임베딩 = sentence-transformers MiniLM-L12 다국어(384d)** — 순수 한국어 질의 품질 때문(model2vec 정적보다 나음).
  검색은 원문(영어) 임베딩 → **한국어 질의는 번역 없이도 그대로 통함**.
- **기계번역 표시 중단 (2026-07-23)** — 배보다 배꼽. 근거:
  1) **비용**: 정적 사이트가 전 데이터를 임베드하는 구조라 번역을 실으면 `docs/index.html` 3.45MB→5.2MB.
     빼니 **2.53MB**(-27%).
  2) **효용 0(검색)**: 검색은 원문 임베딩이라 번역은 순수 표시용. 한국어 검색 품질과 무관.
  3) **품질**: m2m100_418M 결과가 기계번역체("실수가 실행에서 깊이 발생할 때 사용 하 고 원래의 발사기를…").
     한글 미생성 82개. 신뢰 신호가 셀링포인트인 서비스에서 오히려 신뢰를 깎음.
  4) **치명적 표시 버그**: `desc_ko`가 **URL 키**라 모노레포(스킬 여러 개가 URL 하나 공유)에서
     228개 스킬(28 URL)이 남의 번역을 물려받음. 하필 obra/superpowers(★258k) 같은 최상위 노출 카드라 즉시 눈에 띔.
  - 되살릴 거면: 키를 `id`로 바꾸고(위 4번), 노출되는 상위 구간만, 더 나은 모델(API급)로. `desc_ko.json`은 보관 중.
- **공개 배포 보류 → 로컬 전용** — 다국어 임베딩 모델이 **~1.65GB RAM** 필요. 무료 호스트(512MB)·무료 HF Docker(이제 PRO)
  모두 불가. 유료(HF PRO $9/월 또는 2GB 인스턴스)면 `serve.py` 그대로 5분이면 올림.
- **카테고리 랭킹** — 수동 앵커(유명 스킬 포함 보장) + **모노레포(스타>55k) 자동채움 제외**(anthropics/skills가 엉뚱한 카테고리 잠식 방지)
  + 관련성 게이트 + **스타(인기)순**. 앵커도 스타순에 섞임(억지로 맨 위 X). `build_collections.py`의 `ANCHORS`로 조정.
- **디자인 = 모던 애플풍**(흰 배경 / 네이비 다크 / Claude 코랄 포인트). cobalt·필드가이드 시안은 "AI 티" 사유로 폐기.
  근거·공식: `docs/FRIENDLY-HOMEPAGE.md`, `docs/VISUAL-DESIGN-PLAYBOOK.md`.

## ⚠️ 주의 (gotchas)
- **`embed.py m2v`를 로컬에서 돌리지 말 것** — embeddings.npy를 model2vec(256d)로 덮어써 로컬 ST 품질이 깨짐.
  m2v는 폐기된 배포 실험용이었음. 로컬은 항상 `embed.py`(=st).
- **`translate.py`는 이제 파이프라인에서 빠짐** — 돌려도 화면에 안 나옴(표시 경로 제거됨: `ui.py`·`build_site.py`·`core.py`).
  `ingest.py`는 여전히 `desc_ko`를 skills.json에 병합하지만 소비처가 없음.
- **스킬 집합이 안 바뀌면 embed 재실행 불필요** (임베딩 순서=skills.json 순서, ids 일치).
- Pages는 `main:/docs`. `build_site.py`가 docs/index.html+.nojekyll을 씀 (docs/의 다른 .md는 안 건드림).

## ▶️ 다음에 할 만한 것 (상세는 TODO.md)
- 카드 "사용법" **진한 버전**: SKILL.md에서 실제 사용예시 발췌(재수집).
- Option B 안전 스캔을 curated/chat2anyllm 카탈로그로 확장, 오탐↓.
- (원하면) 유료로 의미검색 백엔드 공개 배포.
- Housekeeping: HF 토큰 revoke, 실패한 Render 서비스 삭제.
