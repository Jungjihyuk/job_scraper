"""Phase 1.5 테스트용 공통 fixture"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from app.pipeline.data_models import (
    JobPostingData,
    PipelineConfig,
    PipelineMetrics,
    StageResult,
    ValidatedURL,
    JobDetails,
)


# ── Factory helpers ──────────────────────────────────────────


def make_job_posting(
    posting_id: str = "12345",
    position: str = "백엔드 개발자",
    company: str = "테스트컴퍼니",
    job_category: str = "서버 개발자",
) -> JobPostingData:
    return JobPostingData(
        full_url=f"https://www.wanted.co.kr/wd/{posting_id}",
        position=position,
        company=company,
        posting_id=posting_id,
        job_category=job_category,
    )


def make_validated_url(
    posting_id: str = "12345",
    is_valid: bool = True,
) -> ValidatedURL:
    return ValidatedURL(
        job_url=make_job_posting(posting_id=posting_id),
        is_valid=is_valid,
        status_code=200 if is_valid else 404,
        response_time=0.1,
    )


def make_job_details(
    posting_id: str = "12345",
    success: bool = True,
) -> JobDetails:
    return JobDetails(
        job_url=make_job_posting(posting_id=posting_id),
        job_description={"주요업무": "API 개발", "자격요건": "Python 3년"},
        posted_date="2026-01-01",
        success=success,
    )


def make_stage_result(
    stage_name: str = "test_stage",
    success: bool = True,
    data=None,
    urls_processed: int = 5,
    urls_failed: int = 0,
) -> StageResult:
    return StageResult(
        stage_name=stage_name,
        success=success,
        data=data or [],
        execution_time=1,
        urls_processed=urls_processed,
        urls_failed=urls_failed,
    )


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def default_config():
    """기본 PipelineConfig (default 모드)"""
    return PipelineConfig(
        job="서버 개발자",
        scraper_type="wanted",
        max_scrolls=3,
        batch_size=5,
        scrape_mode="default",
        save_to_database=True,
        save_to_local=False,
    )


@pytest.fixture
def incremental_config():
    """Incremental 모드 PipelineConfig"""
    return PipelineConfig(
        job="서버 개발자",
        scraper_type="wanted",
        max_scrolls=10,
        batch_size=5,
        scrape_mode="incremental",
        save_to_database=True,
        save_to_local=False,
    )


@pytest.fixture
def full_config():
    """Full 모드 PipelineConfig"""
    return PipelineConfig(
        job="서버 개발자",
        scraper_type="wanted",
        max_scrolls=50,
        batch_size=5,
        scrape_mode="full",
        save_to_database=True,
        save_to_local=False,
    )


@pytest.fixture
def sample_postings():
    """테스트용 JobPostingData 리스트"""
    return [
        make_job_posting(posting_id=str(i), position=f"포지션_{i}")
        for i in range(100, 110)
    ]


@pytest.fixture
def sample_validated_urls():
    """테스트용 ValidatedURL 리스트"""
    return [
        make_validated_url(posting_id=str(i))
        for i in range(100, 105)
    ]
