# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-27
**Branch:** feature/v2-data-normalization

## OVERVIEW

Job posting scraper + analytics platform. Python FastAPI backend (scraping pipeline, REST API, WebSocket), React/TS frontend (Vite, FSD architecture), PostgreSQL. Managed via `uv` (Python) and `pnpm` workspaces (frontend).

## STRUCTURE

```
job_scraper/
├── backend/              # Python project root (pyproject.toml, alembic.ini, uv.lock)
│   └── app/              # Python package — FastAPI app + scraping pipeline
│       ├── main.py       # FastAPI entrypoint (uvicorn)
│       ├── cli.py        # CLI pipeline runner (argparse + inquirer)
│       ├── api/routes/   # REST endpoints (dashboard, postings, scraping, stats, companies)
│       ├── core/         # Config, DB connection, logging
│       ├── models/       # SQLAlchemy ORM (job, scraping, base)
│       ├── schemas/      # Pydantic request/response schemas
│       ├── pipeline/     # Multi-stage scraping pipeline
│       │   └── diagnostics/  # Scraper debugging tools (selector check, failure capture)
│       ├── ws/           # WebSocket connection manager
│       └── utils/        # DB helpers, HTTP client, text processing
├── frontend/             # pnpm workspace
│   └── apps/web/src/     # React/TS dashboard
├── label_studio/         # Label Studio integration
│   ├── datasets/         # Labeling input CSV data
│   ├── exports/          # Reviewed annotation exports
│   └── scripts/          # LS project setup, import/export, webhook registration
├── analysis/             # Jupyter notebooks + ML analysis (separate pyproject.toml)
│   ├── notebooks/        # Jupyter notebooks
│   ├── scripts/          # Data analysis & processing scripts
│   ├── outputs/          # Analysis output CSVs
│   └── utils/            # DB utilities for analysis
├── docs/                 # Obsidian-based project docs (정의서, 명세서, 설계서)
└── tests/                # pytest (empty — only __init__.py)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/routes/` | Add router, register in `main.py` |
| Add scraper for new site | `backend/app/pipeline/scrapers/` | Extend `BaseScraper` |
| Add pipeline stage | `backend/app/pipeline/stages/` | Extend `BaseStage` |
| Modify DB schema | `backend/app/models/` | ORM model, migrate via Alembic |
| Add frontend page | `frontend/apps/web/src/pages/` | Lazy-loaded in `app/router/` |
| Add shared UI component | `frontend/apps/web/src/shared/ui/` | Exported via barrel |
| Add entity (FSD) | `frontend/apps/web/src/entities/` | model/ + api/ per entity |
| Run scraping | `cd backend && uv run app/cli.py` | Interactive job selector |
| Run web dashboard | `cd backend && uv run uvicorn app.main:app --reload` | Port 8000 |
| Run frontend dev | `cd frontend/apps/web && pnpm dev` | Port 5173 |
| Diagnose scraper | `backend/app/pipeline/diagnostics/` | Selector check, failure capture |
| Label Studio scripts | `label_studio/scripts/` | Import, export, webhook setup |
| Data processing | `analysis/scripts/` | Normalization, domain review |

## CONVENTIONS

- **Python imports**: Absolute from package root (`from app.core.database import ...`)
- **Python formatting**: Black (80 chars), isort (Google profile), flake8 (90 chars, E203 ignored, flake8_mutable plugin)
- **TS imports**: Relative paths only (no tsconfig aliases)
- **TS module resolution**: Bundler mode (`tsconfig.json`)
- **Frontend architecture**: Feature-Sliced Design (app → pages → entities → shared)
- **DB config**: Environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- **Docker postgres port**: 5433:5432 (not default 5432)
- **Package manager**: `uv` for Python (run from `backend/`), `pnpm` for frontend

## COMMANDS

```bash
# Backend
cd backend && uv run uvicorn app.main:app --reload    # API server (port 8000)
cd backend && uv run app/cli.py                        # CLI scraping pipeline
cd backend && uv run app/cli.py --max-scrolls 5 --debug  # Debug mode

# Frontend
cd frontend/apps/web && pnpm dev                       # Dev server (port 5173)
cd frontend/apps/web && pnpm build                     # Production build

# Full stack (Docker)
docker compose up -d                                   # Start all services
docker compose down                                    # Stop all services

# Diagnostics
cd backend && uv run python app/pipeline/diagnostics/diagnose_scraper.py
cd backend && uv run python app/pipeline/diagnostics/check_selectors.py

# Label Studio
cd backend && uv run ../label_studio/scripts/import_from_db.py
cd backend && uv run ../label_studio/scripts/export_annotations.py

# Code quality
cd backend && black app/                               # Format Python
cd backend && isort app/                               # Sort imports
cd backend && flake8 app/                              # Lint

# Tests (when added)
cd backend && pytest tests/                            # Run tests
```

## NOTES

- WebSocket at `/ws` for real-time scraping progress
- CORS allows `localhost:5173` only (frontend dev server)
- Vite proxies both `/api` and `/ws` to backend — see `frontend/apps/web/vite.config.ts`
- Pipeline stages: URL collect → validate → scrape content → normalize → save (DB + local JSON)
- `JOB_CONFIG` in `backend/app/core/config.py` maps Korean job titles to Wanted.co.kr job IDs
- `analysis/` is a separate Python project with own `pyproject.toml` and `.venv` — includes optional AI deps (torch, transformers)
- `docs/` uses Korean (한국어) — Obsidian vault with numbered doc categories (1-8)

<!-- lanternspec:start -->
## LanternSpec — 이 프로젝트에서 AI가 일하는 방식

> 사람은 팀장, AI는 팀원, 문서는 업무 보고서다. 아이디어 → 기획 → 설계 → 할 일 → 구현이 익숙한 개발 문서로 이어지고,
> 모르는 기술이 나오면 지식 저장소와 비교해 복습할 것과 새로 공부할 것을 알려 준다.

### 문서 지도 (`docs/`)
| 폴더 | 무엇 | 누가 고치나 |
|---|---|---|
| `개발문서 MOC.md` | 지도. 읽는 순서: MOC → 3. 현재 상태 → (필요한 작업만) 2. 작업 | `lantern map` (표시 안쪽) |
| `0. 템플릿/` | 글 구조 (양식) · `_meta/enums.yaml` = 선택지의 유일한 출처 | `/l-template` |
| `1. 아이디어/` | `IDEA-001 …md` | `/l-idea` |
| `2. 작업/W-012 …/` | 기획 · 설계 · 할 일 · 기록. **일하는 동안 고치는 곳은 여기뿐** | `/l-plan` → `/l-design` → `/l-task` → `/l-build` |
| `3. 현재 상태/` | 지금 시스템의 모습. **작업이 끝날 때만** 승인 후 갱신 | `/l-build` 마무리 · `/l-sync` |
| `4. 운영 기록/` | 보고 (`보고/현황.md`) · 회의록 | `/l-report` |

### 지킬 것
1. **형식은 스크립트가, 내용은 AI가.** 번호 · 파일 · 폴더 · 검사 · 상태 바꾸기는 `lantern …` 명령으로 한다. 손으로 ID를 짓거나 파일을 만들지 않는다.
2. **문서는 템플릿에서만 태어난다.** `lantern scaffold …`로 만들고 `{{빈칸}}`만 채운다. 칸 · 제목 구조를 바꾸지 않는다. 쓰고 나면 `> [!guide]` 안내는 지워도 된다.
3. **모르면 추측하지 않는다.** `❓ 확인 필요`로 적고 사람에게 묻는다.
4. **끝날 때 공통 마무리.** 문서를 바꾼 스킬은 `lantern close <스킬> [--work W-012]` (검사 → 지도 → 실행 기록).
5. **쓰기 전에 보여 준다.** `3. 현재 상태` · 설계 승인 · 큰 변경은 요약을 보여 주고 승인받는다 (예외: `/l-idea`는 바로 기록).
6. **남의 저장소는 읽기만.** 지식 저장소는 `lantern knowledge`로만 읽고, 쓰기는 승인 후에만.
7. **기존 문서는 고치지 않는다.** `5. 기존 문서/`의 관련 문서를 만나면 우리 양식으로 옮길지 묻는다 (`/l-template migrate "5. 기존 문서/…"`).
8. **한 사실은 한 곳에만.** 다른 문서의 내용은 복사하지 말고 `[[링크]]`로 가져온다. 생성되는 칸(ERD · 보고 · MOC 블록)은 손으로 고치지 않는다.
9. **사용자에게는 한국어로 말한다.** 질문 · 설명 · 마무리 보고와 문서 내용 모두 (`lantern.yaml`의 `project.language`: `ko`). 명령 · 파일 이름 · 코드는 그대로 둔다.
10. **묻는 법.** 고를 수 있는 질문은 실제 후보만 선택지로 낸다 — 직접 입력 칸은 질문 도구가 맨 아래에 따로 주므로 "직접 입력" · "Other를 골라 주세요" 같은 빈 선택지를 만들지 않는다. 후보를 만들 수 없는 자유 답(소개 · 이름 등)은 선택지 없이 평범한 메시지로 묻는다.
11. **보호 칸은 사람이 정한다.** lantern이 읽고 쓰는 칸(`0. 템플릿/_meta/보호 칸.md`에 목록)을 스스로 지우거나 제목을 바꾸지 않는다. 검사나 마무리에서 "… 칸이 없습니다. … 일부러 바꾸셨나요?"가 나오면 **칸을 되살리지 말고** 사용자에게 셋 중 하나로 묻는다 — 제목을 바꿨다 → `lantern sections rename <키> "새 제목"` · 이 기능을 안 쓴다 → `lantern sections off <키>` · 실수다 → 템플릿대로 칸을 되살린다.

### 커밋
- 할 일 하나 = 커밋 하나. 메시지 끝에 ID: `feat: 로그인 버튼 추가 [W-012-T02]` (여러 할 일을 섞지 않는다)
- 문서(`할 일.md` 체크 · `기록.md` 증거)는 코드와 **같은 커밋**에 넣는다

### 명령 한눈에
| 하고 싶은 것 | 명령 |
|---|---|
| 프로젝트 준비 · 성격 바꾸기 | `/l-init` |
| 생각 기록 | `/l-idea` |
| 무엇을 · 왜 → 어떻게 → 할 일 → 구현 | `/l-plan` → `/l-design` → `/l-task` → `/l-build` |
| 모르는 기술 | `/l-learn` |
| 현황 | `/l-report` |
| 양식 만들기 · 다듬기 · 옮기기 | `/l-template` |
| 양식 검사 · 문서↔코드 맞추기 · 지도 · 결정 기록 | `/l-check` · `/l-sync` · `/l-map` · `/l-adr` |
| 작업 방식 (하네스 · 루프 · 그래프) · AI 작업 평가 | `lantern harness suggest` · `lantern eval` |

Codex에서는 `$l-init`처럼 `$`로 부른다. 지금 상황이 궁금하면 `lantern status`, 전체 명령은 `lantern --help`.
<!-- lanternspec:end -->
