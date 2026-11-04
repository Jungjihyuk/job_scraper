"""DatabaseSaverStage를 실제 PostgreSQL에 돌리는 테스트

ON CONFLICT 동작은 다른 DB로 확인할 수 없어 Postgres가 필요하다. 임시 DB를
DB_* 환경변수로 가리키고 RUN_DB_TESTS=1을 줄 때만 실행하며, 프로젝트 DB에는
쓰지 않는다.
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.core.config import db_config
from app.core.database import db_manager
from app.models import JobPosting, Location, ScrapedUrl, ScrapingBatch
from app.models.base import Base
from app.pipeline.data_models import (
    JobDetails,
    JobSaveResult,
    PipelineConfig,
)
from app.pipeline.manager import PipelineManager
from app.pipeline.stages.database_saver import DatabaseSaverStage, url_hash
from tests.conftest import make_job_posting, make_validated_url

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="RUN_DB_TESTS=1일 때만 실행"
)


def _details(posting_id: str, **fields: object) -> JobDetails:
    description = {"title": "제목", "main_tasks": "업무", "tags": ["식대"]}
    description.update(fields)
    return JobDetails(
        job_url=make_job_posting(posting_id=posting_id),
        job_description=description,
        job_field="서버 개발자",
        location=description.get("location"),
        location_detail=description.get("location_details"),
        posted_date=datetime(2026, 1, 1),
    )


def _count(session, model) -> int:
    return session.query(model).count()


@pytest.fixture
def saver():
    assert db_config.database != "job_scraper_db"
    db_manager.initialize()
    Base.metadata.create_all(db_manager.engine)
    with db_manager.get_session() as session:
        session.execute(
            text(
                "TRUNCATE job_posting, scraped_urls, scraping_tasks, "
                "scraping_batches, locations RESTART IDENTITY CASCADE"
            )
        )
        session.commit()
    stage = DatabaseSaverStage()
    stage.create_batch("test", "wanted")
    return stage


class TestSaveValidatedUrls:
    @pytest.mark.asyncio
    async def test_conflict_skips_only_existing_rows(self, saver):
        """AC-6: 충돌한 URL만 건너뛰고 건수가 실제 삽입 수와 같다"""
        first = await saver.execute([make_validated_url("1")])
        second = await saver.execute(
            [
                make_validated_url("1"),
                make_validated_url("2"),
                make_validated_url("3"),
            ]
        )

        assert first.urls_processed == 1
        assert second.success is True
        assert second.urls_processed == 2
        with db_manager.get_session() as session:
            assert _count(session, ScrapedUrl) == 3

    @pytest.mark.asyncio
    async def test_conflict_keeps_failure_count(self, saver):
        """다시 나온 URL이 쌓인 실패 횟수를 지우지 않는다"""
        await saver.execute([make_validated_url("1")])
        details = _details("1")
        details.error_message = "실패"
        saver.record_failures([details])

        await saver.execute([make_validated_url("1")])

        with db_manager.get_session() as session:
            row = session.query(ScrapedUrl).one()
            assert row.retry_count == 1
            assert row.status == "failed"


class TestSaveJobDetails:
    @pytest.mark.asyncio
    async def test_saved_failed_and_duplicates_are_separate(self, saver):
        """AC-4: 저장, 실패, 중복이 나뉘어 돌아오고 저장 건수에 섞이지 않는다"""
        await saver.execute([_details("1")])
        too_long = _details("3", experience="x" * 51)

        stage_result = await saver.execute(
            [_details("1"), _details("2"), too_long]
        )

        result = stage_result.data
        assert isinstance(result, JobSaveResult)
        assert [d.job_url.posting_id for d in result.saved] == ["2"]
        assert [d.job_url.posting_id for d in result.failed] == ["3"]
        assert result.duplicates == 1
        assert "DB 저장 실패" in too_long.error_message
        with db_manager.get_session() as session:
            assert _count(session, JobPosting) == 2

    @pytest.mark.asyncio
    async def test_missing_optional_fields_are_null(self, saver):
        """AC-2 · AC-3: 부가 칸은 NULL이고 근무지는 미상 지역에 연결된다"""
        details = _details("1")
        details.posted_date = None

        await saver.execute([details])

        with db_manager.get_session() as session:
            posting = session.query(JobPosting).one()
            assert posting.position == "제목"
            assert posting.experience is None
            assert posting.position_detail is None
            assert posting.requirements is None
            assert posting.deadline is None
            assert posting.posted_date is None
            location = session.get(Location, posting.location_id)
            assert location.location == "미상"
            assert location.location_detail is None

    @pytest.mark.asyncio
    async def test_normalization_failed_is_written(self, saver):
        """AC-7: 표시한 공고만 조회된다"""
        marked = _details("1")
        marked.normalization_failed = True

        await saver.execute([marked, _details("2")])

        with db_manager.get_session() as session:
            rows = (
                session.query(JobPosting.posting_id)
                .filter(JobPosting.normalization_failed.is_(True))
                .all()
            )
            assert [row.posting_id for row in rows] == ["1"]

    @pytest.mark.asyncio
    async def test_success_clears_failure_record(self, saver):
        """다시 수집해 성공하면 실패 기록이 지워진다"""
        await saver.execute([make_validated_url("1")])
        failed = _details("1")
        failed.error_message = "실패"
        saver.record_failures([failed])

        await saver.execute([_details("1")])

        with db_manager.get_session() as session:
            row = session.query(ScrapedUrl).one()
            assert row.retry_count == 0
            assert row.status == "success"
            assert row.error_message is None


class TestRecordFailures:
    @pytest.mark.asyncio
    async def test_counts_up_and_keeps_reason(self, saver):
        """AC-18: 실패할 때마다 횟수가 늘고 원인이 남는다"""
        await saver.execute([make_validated_url("1")])
        details = _details("1")
        details.error_message = "필수 칸 추출 실패"

        saver.record_failures([details])
        saver.record_failures([details])

        with db_manager.get_session() as session:
            row = (
                session.query(ScrapedUrl)
                .filter_by(url_hash=url_hash(details.job_url.full_url))
                .one()
            )
            assert row.retry_count == 2
            assert row.status == "failed"
            assert row.error_message == "필수 칸 추출 실패"


class TestUpdateBatchStatus:
    @pytest.mark.parametrize("status", ["completed", "partial", "failed"])
    def test_writes_counts_and_completed_at(self, saver, status):
        """AC-4 · AC-11: 건수와 끝난 시각이 배치에 남는다"""
        saver.update_batch_status(
            status, 10, collected=12, saved=7, failed=2, skipped=1
        )

        with db_manager.get_session() as session:
            batch = session.get(ScrapingBatch, saver.batch_id)
            assert batch.status == status
            assert batch.total_urls == 10
            assert batch.collected_count == 12
            assert batch.saved_count == 7
            assert batch.failed_count == 2
            assert batch.skipped_count == 1
            assert batch.completed_at is not None


class TestExhaustedUrls:
    @pytest.mark.asyncio
    async def test_three_failures_load_as_exhausted(self, saver):
        """AC-18: 3회 실패한 URL만 제한 목록에 오른다"""
        await saver.execute([make_validated_url("1"), make_validated_url("2")])
        three = _details("1")
        three.error_message = "실패"
        two = _details("2")
        two.error_message = "실패"
        for _ in range(3):
            saver.record_failures([three])
        for _ in range(2):
            saver.record_failures([two])

        with patch("app.pipeline.manager.URLCollectorStage"), patch(
            "app.pipeline.manager.URLValidatorStage"
        ), patch("app.pipeline.manager.ContentScraperStage"), patch(
            "app.pipeline.manager.JobNormalizerStage"
        ):
            manager = PipelineManager(PipelineConfig(job="서버 개발자"))
        manager._load_existing_posting_ids()

        assert manager._exhausted_urls == {three.job_url.full_url}
