# PIPELINE — Multi-Stage Scraping Engine

## OVERVIEW

Sequential scraping pipeline: URL collect → validate → scrape content → normalize → save. Orchestrated by `PipelineManager`.

## STRUCTURE

```
pipeline/
├── manager.py           # PipelineManager — orchestrates stage execution, tracks metrics
├── data_models.py       # PipelineConfig, PipelineMetrics, StageResult, ValidatedURL, JobPostingData
├── stages/              # Pipeline stages (sequential)
│   ├── base.py          # BaseStage, AsyncBatchStage — abstract stage contracts
│   ├── url_collector.py # Scrolls job listing pages, collects URLs (Playwright)
│   ├── url_validator.py # Validates collected URLs (HTTP HEAD checks)
│   ├── content_scraper.py # Scrapes job details from validated URLs (Playwright)
│   ├── normalizer.py    # JobNormalizerStage — normalizes scraped data
│   ├── database_saver.py # Persists to PostgreSQL via SQLAlchemy
│   └── file_saver.py    # Saves JSON to logs/ directory
├── scrapers/            # Site-specific scraper implementations
│   ├── base.py          # BaseScraper — abstract interface for site scrapers
│   ├── manager.py       # ScraperManager — registry/factory for site scrapers
│   ├── scraper.py       # WantedScraper implementation base
│   └── wanted.py        # Wanted.co.kr specific scraper
└── normalizers/         # Data normalization modules
    ├── base.py          # BaseNormalizer
    ├── job.py           # Job posting field normalizer
    ├── experience.py    # Experience text → structured data
    └── technology.py    # Technology/skill extraction
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new scraper site | `scrapers/` | Extend `BaseScraper`, register in `ScraperManager` |
| Add pipeline stage | `stages/` | Extend `BaseStage` or `AsyncBatchStage` |
| Change pipeline flow | `manager.py` | `PipelineManager.run()` method |
| Add normalizer | `normalizers/` | Extend `BaseNormalizer` |
| Change data models | `data_models.py` | Dataclasses for pipeline data flow |

## CONVENTIONS

- Stages extend `BaseStage` (sync) or `AsyncBatchStage` (async batch processing)
- Each stage has `process()` method returning `StageResult`
- Scrapers extend `BaseScraper` — abstract methods for URL patterns, content extraction
- Currently only `wanted` (Wanted.co.kr) scraper is implemented
- Pipeline uses Playwright for browser automation (headless Chromium)
- `PipelineConfig` controls all runtime behavior (max_scrolls, batch_size, save options)

## ANTI-PATTERNS

- `content_scraper.py` — 5 bare `except Exception: pass` in cleanup code
- `content_scraper.py` — 3 commented-out methods (lines 276-318), dead code
- Multiple type-safety issues flagged by pyright (None checks missing)
