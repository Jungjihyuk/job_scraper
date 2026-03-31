# BACKEND — Python FastAPI + Scraping Pipeline

## OVERVIEW

FastAPI web API + multi-stage scraping pipeline for Korean job posting sites. SQLAlchemy ORM with PostgreSQL.

## STRUCTURE

```
backend/app/
├── main.py              # FastAPI app creation, CORS, router registration, WebSocket
├── cli.py               # CLI entry: argparse + inquirer job selector → PipelineManager
├── api/routes/          # REST endpoints (dashboard, job_postings, scraping, statistics, companies)
├── core/                # Config (env-based), DB connection (SQLAlchemy), logging
├── models/              # ORM: job.py (Company, JobPosting, etc.), scraping.py (Batch, Task, URL)
├── schemas/             # Pydantic request/response DTOs
├── pipeline/            # Scraping pipeline (see pipeline/AGENTS.md)
├── ws/manager.py        # WebSocket ConnectionManager — broadcasts scraping progress
└── utils/               # DB helpers (load_job_postings), HTTP client, text processing
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add REST endpoint | `api/routes/` | Create router, register in `main.py` via `app.include_router()` |
| Add ORM model | `models/` | Inherit `Base` from `models/base.py`, add to `__init__.py` |
| Add Pydantic schema | `schemas/` | Match naming: `{entity}_schemas.py` |
| Modify DB config | `core/config.py` | `DatabaseConfig` reads from env vars |
| Change logging | `core/logging.py` | `create_development_logger()` is the factory |
| WebSocket changes | `ws/manager.py` | Singleton `manager` instance, imported in `main.py` |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `JobPosting` | ORM model | `models/job.py` | Core posting entity — company, category, location, experience FKs |
| `Company` | ORM model | `models/job.py` | Company metadata + Blind ratings |
| `JobCategory` | ORM model | `models/job.py` | Job taxonomy (category/field/specialty) |
| `Location` | ORM model | `models/job.py` | Location taxonomy (location/detail) |
| `ExperienceCategory` | ORM model | `models/job.py` | Normalized experience (raw → standardized, min/max years) |
| `ScrapingBatch` | ORM model | `models/scraping.py` | Batch container — status, URL counts, timestamps |
| `ScrapingTask` | ORM model | `models/scraping.py` | Per-stage task progress within batch |
| `ScrapedUrl` | ORM model | `models/scraping.py` | Per-URL scrape state + hash dedup |
| `DatabaseConfig` | class | `core/config.py` | Reads env vars → DB URLs + pool settings |
| `db_config` | singleton | `core/config.py` | Global config instance |
| `JOB_CONFIG` | dict | `core/config.py` | Wanted.co.kr job_id mapping (직무 → ID) |
| `DatabaseManager` | class | `core/database.py` | Engine, session factory, lifecycle (init/create/drop) |
| `db_manager` | singleton | `core/database.py` | Global DB access point |
| `get_db_session` | function | `core/database.py` | FastAPI dependency injection for DB sessions |
| `JobPostingSchema` | Pydantic | `schemas/common.py` | API response DTO for job postings |
| `CompanySchema` | Pydantic | `schemas/common.py` | API response DTO for companies |
| `DashboardStatsResponse` | Pydantic | `schemas/dashboard.py` | Dashboard stats (total_jobs, total_companies, recent_batches) |
| `ConnectionManager` | class | `ws/manager.py` | WebSocket broadcast + scraping process control |

## API ROUTES

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/api/dashboard/stats` | `get_dashboard_stats` | Dashboard summary stats |
| GET | `/api/dashboard/companies` | `get_companies` | Company list with posting counts |
| GET | `/api/job_postings/deadline` | `get_job_postings` | Near-deadline postings (filtered) |
| GET | `/api/job_postings/recent` | `get_recent_job_postings` | Recently posted jobs |
| GET | `/api/job_postings/job` | `get_job_categories` | All job specialties |
| GET | `/api/job_postings/experience` | `get_experience` | Standardized experiences |
| GET | `/api/job_postings/location` | `get_location` | All locations |
| GET | `/api/job_postings/domain` | `get_domains` | All domains |
| GET | `/api/job_postings/technology` | `get_technologies` | Core technologies (raw SQL, JSONB unnest) |
| GET | `/api/scraping/status` | `get_scraping_status` | Current scraping state |
| POST | `/api/scraping/start` | `start_scraping` | Launch pipeline (background task) |
| POST | `/api/scraping/stop` | `stop_scraping` | Stop running pipeline |
| GET | `/api/statistics/specialty_by_location` | `get_specialty_by_location` | Region × specialty distribution |
| GET | `/api/statistics/experience_by_specialty` | `get_experience_by_specialty` | Specialty × experience distribution |
| GET | `/api/statistics/posting_trends` | `get_posting_trends` | Posting time series |
| GET | `/api/statistics/domain_distribution` | `get_domain_distribution` | Domain distribution |
| GET | `/api/statistics/technology_trends` | `get_technology_trends` | Monthly tech trends (raw SQL) |
| GET | `/api/companies` | `get_companies` | All registered companies |

## CONVENTIONS

- All imports absolute from `app.` root — never relative
- Router pattern: `router = APIRouter(prefix="/api/{resource}", tags=["{Resource}"])`
- DB sessions via `DatabaseManager.get_session()` context manager
- Statistics routes return raw dicts (no Pydantic response_model)
- Some routes use raw SQL (`text()`) for JSONB array operations

## ANTI-PATTERNS

- `core/config.py:25` — hardcoded fallback password `"1234"`
- `ws/manager.py` — 2 bare `except Exception: pass` blocks (lines 26-27, 46-47)
- `content_scraper.py` — 5 bare `except Exception: pass` + 3 commented-out methods
- Statistics routes lack Pydantic response models — return untyped dicts
