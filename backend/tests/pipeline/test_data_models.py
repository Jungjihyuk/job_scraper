"""Data Models 단위 테스트

PipelineConfig, StageResult, PipelineMetrics, JobPostingData 등
"""

import pytest
from datetime import datetime

from app.pipeline.data_models import (
    JobPostingData,
    ValidatedURL,
    JobDetails,
    PipelineConfig,
    StageResult,
    PipelineMetrics,
)


class TestJobPostingData:

    def test_creation(self):
        post = JobPostingData(
            full_url="https://www.wanted.co.kr/wd/12345",
            position="백엔드 개발자",
            company="테스트",
            posting_id="12345",
            job_category="서버 개발자",
        )
        assert post.posting_id == "12345"
        assert isinstance(post.collected_at, datetime)

    def test_str(self):
        post = JobPostingData(
            full_url="https://www.wanted.co.kr/wd/12345",
            position="백엔드",
            company="회사A",
            posting_id="12345",
            job_category="서버 개발자",
        )
        assert "백엔드" in str(post)
        assert "회사A" in str(post)


class TestValidatedURL:

    def test_valid_url(self):
        post = JobPostingData(
            full_url="https://www.wanted.co.kr/wd/1",
            position="p",
            company="c",
            posting_id="1",
            job_category="j",
        )
        vu = ValidatedURL(
            job_url=post,
            is_valid=True,
            status_code=200,
            response_time=0.5,
        )
        assert vu.is_valid is True
        assert vu.status_code == 200

    def test_invalid_url(self):
        post = JobPostingData(
            full_url="https://www.wanted.co.kr/wd/1",
            position="p",
            company="c",
            posting_id="1",
            job_category="j",
        )
        vu = ValidatedURL(
            job_url=post,
            is_valid=False,
            status_code=404,
            error_message="Not Found",
        )
        assert vu.is_valid is False
        assert vu.error_message == "Not Found"


class TestJobDetails:

    def test_success(self):
        post = JobPostingData(
            full_url="u",
            position="p",
            company="c",
            posting_id="1",
            job_category="j",
        )
        jd = JobDetails(
            job_url=post,
            job_description={"주요업무": "개발"},
            success=True,
        )
        assert jd.success is True
        assert jd.job_description["주요업무"] == "개발"

    def test_failure(self):
        post = JobPostingData(
            full_url="u",
            position="p",
            company="c",
            posting_id="1",
            job_category="j",
        )
        jd = JobDetails(
            job_url=post,
            job_description={},
            success=False,
            error_message="timeout",
        )
        assert jd.success is False


class TestPipelineConfig:

    def test_defaults(self):
        config = PipelineConfig(job="서버 개발자")
        assert config.scraper_type == "wanted"
        assert config.max_scrolls == 50
        assert config.scrape_mode == "default"
        assert config.save_to_database is True
        assert config.save_to_local is False
        assert config.batch_size == 5

    def test_incremental_mode(self):
        config = PipelineConfig(
            job="서버 개발자", scrape_mode="incremental"
        )
        assert config.scrape_mode == "incremental"

    def test_full_mode(self):
        config = PipelineConfig(
            job="서버 개발자", scrape_mode="full"
        )
        assert config.scrape_mode == "full"

    def test_local_save_options(self):
        config = PipelineConfig(
            job="서버 개발자",
            save_to_local=True,
            local_output_format="csv",
            local_output_path="/tmp/out/",
        )
        assert config.save_to_local is True
        assert config.local_output_format == "csv"


class TestStageResult:

    def test_creation(self):
        result = StageResult(
            stage_name="url_collector",
            success=True,
            data=["a", "b"],
            execution_time=5,
            urls_processed=2,
        )
        assert result.success is True
        assert result.urls_processed == 2
        assert result.urls_failed == 0

    def test_failure(self):
        result = StageResult(
            stage_name="content_scraper",
            success=False,
            data=[],
            execution_time=3,
            urls_processed=0,
            urls_failed=5,
            error_message="Network error",
        )
        assert result.success is False
        assert result.error_message == "Network error"


class TestPipelineMetrics:

    def test_initial_state(self):
        m = PipelineMetrics()
        assert m.total_urls_collected == 0
        assert m.get_success_rate() == 0.0
        assert m.stage_results == []

    def test_add_stage_result(self):
        m = PipelineMetrics()
        sr = StageResult(
            stage_name="test",
            success=True,
            data=[],
            execution_time=2,
            urls_processed=10,
        )
        m.add_stage_result(sr)
        assert len(m.stage_results) == 1
        assert m.total_execution_time == 2

    def test_success_rate(self):
        m = PipelineMetrics(successful_scrapes=7, failed_scrapes=3)
        assert m.get_success_rate() == 70.0
