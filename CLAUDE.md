# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job posting scraper + analytics platform targeting Korean job sites (Wanted.co.kr). FastAPI backend with a multi-stage scraping pipeline, React/TS frontend (FSD architecture), PostgreSQL, managed via `uv` (Python) and `pnpm` (frontend).

## Commands

```bash
# Backend API (port 8000)
uv run uvicorn backend.main:app --reload

# CLI scraping pipeline
uv run backend/cli.py
uv run backend/cli.py --max-scrolls 5 --debug

# Frontend dev server (port 5173)
cd frontend/apps/web && pnpm dev
cd frontend/apps/web && pnpm build

# Full stack
docker compose up -d

# Code quality
black backend/ && isort backend/ && flake8 backend/

# Tests
pytest tests/

# Analysis environment (separate venv)
cd analysis && uv run jupyter lab
```

## Architecture

**Backend** (`backend/`): FastAPI app + scraping pipeline. Pipeline stages: URL collect → validate → scrape content → normalize → save (DB + local JSON). WebSocket at `/ws` for real-time progress.

**Frontend** (`frontend/apps/web/src/`): Feature-Sliced Design — `app → pages → entities → shared`. Vite proxies `/api` and `/ws` to backend. Pages are lazy-loaded.

**Analysis** (`analysis/`): Separate Python project with its own `pyproject.toml` and `.venv`. Includes optional AI deps (torch, transformers, sentence-transformers). Used for domain/technology normalization ML work.

**Database**: PostgreSQL on port 5433 (Docker maps 5433→5432). Key models: `JobPosting`, `Company`, `JobCategory`, `Location`, `ExperienceCategory` (in `backend/models/job.py`), `ScrapingBatch/Task/URL` (in `backend/models/scraping.py`).

**Label Studio** (`label_studio/`): Annotation pipeline for domain/tech labeling. Scripts for import, export, and webhook registration.

## Key Conventions

- **Python imports**: Absolute from package root — `from backend.core.database import ...` (never relative)
- **Python style**: Black 80 chars, isort Google profile, flake8 90 chars (E203 ignored, `flake8_mutable` plugin)
- **TypeScript imports**: Relative paths only (no tsconfig path aliases)
- **TS module resolution**: Bundler mode (`tsconfig.json`)
- **DB env vars**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_POOL_SIZE`
- **Router pattern**: `APIRouter(prefix="/api/{resource}", tags=["{Resource}"])`
- **Statistics routes** return raw dicts — no Pydantic `response_model`
- `JOB_CONFIG` in `backend/core/config.py` maps Korean job titles to Wanted.co.kr job IDs
- `backend/migrations_legacy/` is legacy — Alembic is the target migration tool
- `backend/static/` and `backend/templates/` are legacy — frontend is now the React SPA

## Detailed AGENTS.md Files

More granular guidance (code maps, anti-patterns, per-subsystem conventions) lives in:
- `AGENTS.md` — project-wide structure and task routing
- `backend/AGENTS.md` — API routes table, ORM model map, backend anti-patterns
- `backend/pipeline/AGENTS.md` — pipeline stage details
- `frontend/apps/web/src/AGENTS.md` — FSD layer rules, component patterns
