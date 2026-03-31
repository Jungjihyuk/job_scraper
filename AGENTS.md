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
