# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-18
**Commit:** 65ccc4d2
**Branch:** feature/v2-data-normalization

## OVERVIEW

Job posting scraper + analytics platform. Python FastAPI backend (scraping pipeline, REST API, WebSocket), React/TS frontend (Vite, FSD architecture), PostgreSQL. Managed via `uv` (Python) and `pnpm` workspaces (frontend).

## STRUCTURE

```
job_scraper/
├── backend/              # Python package — FastAPI app + scraping pipeline
│   ├── main.py           # FastAPI entrypoint (uvicorn)
│   ├── cli.py            # CLI pipeline runner (argparse + inquirer)
│   ├── api/routes/       # REST endpoints (dashboard, postings, scraping, stats, companies)
│   ├── core/             # Config, DB connection, logging
│   ├── models/           # SQLAlchemy ORM (job, scraping, base)
│   ├── schemas/          # Pydantic request/response schemas
│   ├── pipeline/         # Multi-stage scraping pipeline (see backend/pipeline/AGENTS.md)
│   ├── ws/               # WebSocket connection manager
│   └── utils/            # DB helpers, HTTP client, text processing
├── frontend/             # pnpm workspace
│   └── apps/web/src/     # React/TS dashboard (see frontend/apps/web/src/AGENTS.md)
├── scripts/              # Operational scripts (see scripts/AGENTS.md)
│   ├── migrations/       # DB schema migration scripts
│   ├── data_processing/  # Normalization, URL reconstruction
│   ├── diagnostics/      # Scraper debugging tools
│   └── analysis/         # Data analysis utilities
├── analysis/             # Jupyter notebooks + ML analysis (separate pyproject.toml)
├── docs/                 # Obsidian-based project docs (정의서, 명세서, 설계서)
├── tests/                # pytest (empty — only __init__.py)
└── logs/                 # Scraping output logs (JSON)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/api/routes/` | Add router, register in `main.py` |
| Add scraper for new site | `backend/pipeline/scrapers/` | Extend `BaseScraper` |
| Add pipeline stage | `backend/pipeline/stages/` | Extend `BaseStage` |
| Modify DB schema | `backend/models/` + `scripts/migrations/` | ORM model + migration script |
| Add frontend page | `frontend/apps/web/src/pages/` | Lazy-loaded in `app/router/` |
| Add shared UI component | `frontend/apps/web/src/shared/ui/` | Exported via barrel |
| Add entity (FSD) | `frontend/apps/web/src/entities/` | model/ + api/ per entity |
| Run scraping | `uv run backend/cli.py` | Interactive job selector |
| Run web dashboard | `uv run uvicorn backend.main:app --reload` | Port 8000 |
| Run frontend dev | `cd frontend/apps/web && pnpm dev` | Port 5173 |
| DB migrations | `scripts/migrations/` | Standalone scripts, run with `uv run python` |

## CONVENTIONS

- **Python imports**: Absolute from package root (`from backend.core.database import ...`)
- **Python formatting**: Black (80 chars), isort (Google profile), flake8 (90 chars, E203 ignored, flake8_mutable plugin)
- **TS imports**: Relative paths only (no tsconfig aliases)
- **TS module resolution**: Bundler mode (`tsconfig.json`)
- **Frontend architecture**: Feature-Sliced Design (app → pages → entities → shared)
- **DB config**: Environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- **Docker postgres port**: 5433:5432 (not default 5432)
- **Package manager**: `uv` for Python, `pnpm` for frontend

## ANTI-PATTERNS (THIS PROJECT)

- **7 bare `except Exception: pass`** in `content_scraper.py` and `ws/manager.py` — silent error swallowing, needs proper logging
- **Hardcoded fallback password** `"1234"` in `backend/core/config.py:25` — weak default when `DB_PASSWORD` env var missing
- **3 commented-out async methods** in `content_scraper.py` (lines 276-318) — dead code, remove or restore
- **No tests exist** — `tests/` has only `__init__.py`; pytest is a dependency but unused
- **No CI/CD** — no GitHub Actions workflows, no pre-commit hooks
- **No Dockerfile** — only docker-compose.yml with pre-built images

## COMMANDS

```bash
# Backend
uv run uvicorn backend.main:app --reload          # API server (port 8000)
uv run backend/cli.py                              # CLI scraping pipeline
uv run backend/cli.py --max-scrolls 5 --debug      # Debug mode

# Frontend
cd frontend/apps/web && pnpm dev                   # Dev server (port 5173)
cd frontend/apps/web && pnpm build                 # Production build

# Full stack (Docker)
docker compose up -d                               # Start all services
docker compose down                                # Stop all services

# Code quality
black backend/                                     # Format Python
isort backend/                                     # Sort imports
flake8 backend/                                    # Lint

# Tests (when added)
pytest tests/                                      # Run tests

# DB setup
psql postgres -f grant_permissions.sql
psql -U <user> -d <db> -f job_scraper_db.sql
```

## NOTES

- WebSocket at `/ws` for real-time scraping progress
- CORS allows `localhost:5173` only (frontend dev server)
- Vite proxies both `/api` and `/ws` to backend — see `frontend/apps/web/vite.config.ts`
- Pipeline stages: URL collect → validate → scrape content → normalize → save (DB + local JSON)
- `JOB_CONFIG` in `backend/core/config.py` maps Korean job titles to Wanted.co.kr job IDs
- `analysis/` is a separate Python project with own `pyproject.toml` and `.venv` — includes optional AI deps (torch, transformers)
- `docs/` uses Korean (한국어) — Obsidian vault with numbered doc categories (1-8)
- `.claude/worktrees/` contains old worktree artifacts — ignore
