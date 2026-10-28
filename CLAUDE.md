@AGENTS.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job posting scraper + analytics platform targeting Korean job sites (Wanted.co.kr). FastAPI backend with a multi-stage scraping pipeline, React/TS frontend (FSD architecture), PostgreSQL, managed via `uv` (Python) and `pnpm` (frontend).

## Commands

```bash
# Backend API (port 8000)
cd backend && uv run uvicorn app.main:app --reload

# CLI scraping pipeline
cd backend && uv run app/cli.py
cd backend && uv run app/cli.py --max-scrolls 5 --debug

# Frontend dev server (port 5173)
cd frontend/apps/web && pnpm dev
cd frontend/apps/web && pnpm build

# Full stack
docker compose up -d

# Code quality
cd backend && black app/ && isort app/ && flake8 app/

# Tests
cd backend && pytest tests/
cd backend && pytest tests/test_foo.py -k "test_name"  # Single test

# DB migrations (Alembic)
cd backend && uv run alembic revision --autogenerate -m "description"
cd backend && uv run alembic upgrade head
cd backend && uv run alembic downgrade -1
cd backend && uv run alembic current

# Scraper diagnostics
cd backend && uv run python app/pipeline/diagnostics/diagnose_scraper.py
cd backend && uv run python app/pipeline/diagnostics/check_selectors.py

# Label Studio scripts
cd backend && uv run ../label_studio/scripts/import_from_db.py
cd backend && uv run ../label_studio/scripts/export_annotations.py

# Analysis environment (separate venv)
cd analysis && uv run jupyter lab
```

## Architecture

**Backend** (`backend/`): Contains `pyproject.toml`, `alembic.ini`, `uv.lock`. Source code lives in `backend/app/` — FastAPI app + scraping pipeline. Pipeline stages: URL collect → validate → scrape content → normalize → save (DB + local JSON). WebSocket at `/ws` for real-time progress.

**Frontend** (`frontend/apps/web/src/`): Feature-Sliced Design — `app → pages → entities → shared`. Vite proxies `/api` and `/ws` to backend. Pages are lazy-loaded.

**Analysis** (`analysis/`): Separate Python project with its own `pyproject.toml` and `.venv`. Includes optional AI deps (torch, transformers, sentence-transformers). Used for domain/technology normalization ML work.

**Database**: PostgreSQL on port 5433 (Docker maps 5433→5432). Key models: `JobPosting`, `Company`, `JobCategory`, `Location`, `ExperienceCategory` (in `backend/app/models/job.py`), `ScrapingBatch/Task/URL` (in `backend/app/models/scraping.py`).

**Label Studio** (`label_studio/`): Annotation pipeline for domain/tech labeling. Scripts for import, export, and webhook registration. Runs on port 8080 in Docker, uses a separate `label_studio_db` in the same PostgreSQL instance.

**Environment**: Requires `.env` file at project root with `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`. Docker Compose reads this file for all services.

## Key Conventions

- **Python imports**: Absolute from package root — `from app.core.database import ...` (never relative)
- **Python style**: Black 80 chars, isort Google profile, flake8 90 chars (E203 ignored, `flake8_mutable` plugin)
- **TypeScript imports**: Relative paths only (no tsconfig path aliases)
- **TS module resolution**: Bundler mode (`tsconfig.json`)
- **DB env vars**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_POOL_SIZE`
- **Router pattern**: `APIRouter(prefix="/api/{resource}", tags=["{Resource}"])`
- **Statistics routes** return raw dicts — no Pydantic `response_model`
- **New routers** must be registered in `backend/app/main.py` via `app.include_router()`
- **Frontend styling**: Tailwind CSS 3 + PostCSS; charts use recharts
- **No frontend state management library** — custom hooks + prop drilling
- **FSD import rule**: app → pages → entities → shared (import only downward, never upward)
- `JOB_CONFIG` in `backend/app/core/config.py` maps Korean job titles to Wanted.co.kr job IDs
- `backend/app/` is the Python package root — all `uv` commands run from `backend/`

## Detailed AGENTS.md Files

More granular guidance (code maps, anti-patterns, per-subsystem conventions) lives in:
- `AGENTS.md` — project-wide structure and task routing
- `backend/app/AGENTS.md` — API routes table, ORM model map, backend anti-patterns
- `backend/app/pipeline/AGENTS.md` — pipeline stage details
- `frontend/apps/web/src/AGENTS.md` — FSD layer rules, component patterns
