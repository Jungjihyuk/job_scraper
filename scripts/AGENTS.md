# SCRIPTS — Operational & Migration Scripts

## OVERVIEW

Standalone Python scripts for DB migrations, data processing, diagnostics, and analysis. Run with `uv run python scripts/<category>/<script>.py`.

## STRUCTURE

```
scripts/
├── migrations/          # DB schema changes (run once, in order)
├── data_processing/     # Backfill and normalization (run as needed)
├── diagnostics/         # Scraper debugging (dev tools, Playwright-based)
└── analysis/            # Data analysis (ad-hoc, read-only)
```

## MIGRATIONS (run order matters)

| # | Script | Touches | Purpose |
|---|--------|---------|---------|
| 1 | `initialize_db_with_experience.py` | `experience_categories` table check | Verify/prepare ExperienceCategory table exists |
| 2 | `add_experience_column.py` | `job_posting.experience_category_id` + FK + index | Add experience FK to postings |
| 3 | `add_original_url_column.py` | `job_posting.original_url` | Add original URL column |
| 4 | `add_domain_core_technologies_columns.py` | `job_posting.domain` + `core_technologies` (JSONB) + index | Add domain/tech columns |
| 5 | `migrate_deadline_structure.py` | `job_posting.deadline` → DATE + `is_always_recruiting` + indexes | Restructure deadline handling |

## DATA PROCESSING (backfill scripts)

| Script | Reads | Writes | Purpose |
|--------|-------|--------|---------|
| `normalize_existing_experience_data.py` | `JobPosting.experience` | `JobPosting.experience_category_id`, `ExperienceCategory` | Link postings to normalized experience |
| `normalize_existing_domain_technology_data.py` | `JobPosting.main_tasks`, `.requirements` | `JobPosting.domain`, `.core_technologies` | Extract domain/tech via ContentAnalyzer |
| `populate_original_urls.py` | `ScrapedUrl.url` | `JobPosting.original_url` | Backfill URLs from scraped URL records |
| `reconstruct_urls.py` | `JobPosting.posting_id` | `JobPosting.original_url` | Reconstruct URLs from posting ID patterns |

## DIAGNOSTICS (Playwright-based)

| Script | Purpose | External |
|--------|---------|----------|
| `diagnose_scraper.py` | 6-step scraper health check (load, status, content, screenshot, selectors, anti-bot) | Target URL via Playwright |
| `check_selectors.py` | Validate CSS selectors against live page — detects site redesigns | Target URL via Playwright |
| `capture_failure.py` | Capture HAR + screenshot for failure post-mortem → `logs/diagnostics/` | Target URL via Playwright |

## ANALYSIS (read-only, ad-hoc)

| Script | Purpose |
|--------|---------|
| `analyze_posting_ids.py` | Count posting_id patterns by source (wanted/saramin/jobkorea) |
| `analyze_deadline_data.py` | Analyze deadline formats (date vs 상시) |
| `check_experience_data.py` | Verify ExperienceCategory linkage to JobPosting |

## CONVENTIONS

- Each script is standalone — imports `backend.core.database` or `backend.models` directly
- Migration scripts are NOT reversible — no down migration
- All scripts use `if __name__ == "__main__"` entry pattern
- Invocation: `uv run python scripts/migrations/add_experience_column.py`

## NOTES

- No migration framework (Alembic) — manual scripts only
- When adding a new DB column: create migration script here + update ORM model in `backend/models/`
- Diagnostics scripts require Playwright installed (`playwright install chromium`)
