"""PipelineManager 통합 테스트

전체 파이프라인 흐름(run), 캐시 업데이트, 에러 핸들링 검증
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.pipeline.manager import PipelineManager
from app.pipeline.data_models import PipelineConfig
from tests.conftest import (
    make_job_posting,
    make_stage_result,
    make_validated_url,
    make_job_details,
)


def _make_manager(config: PipelineConfig) -> PipelineManager:
    with patch(
        "app.pipeline.manager.URLCollectorStage"
    ), patch(
        "app.pipeline.manager.URLValidatorStage"
    ), patch(
        "app.pipeline.manager.ContentScraperStage"
    ), patch(
        "app.pipeline.manager.JobNormalizerStage"
    ), patch(
        "app.pipeline.manager.DatabaseSaverStage"
    ):
        return PipelineManager(config)


class TestPipelineRun:
    """PipelineManager.run() 통합 테스트"""

    @pytest.mark.asyncio
    async def test_successful_single_cycle(self, default_config):
        """1 사이클 정상 완료 (수집→필터→검증→스크래핑→정규화)"""
        default_config.max_scrolls = 1
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        posting = make_job_posting(posting_id="new_1")
        validated = make_validated_url(posting_id="new_1")
        details = make_job_details(posting_id="new_1")

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                data=[posting],
                urls_processed=1,
            )
        )
        mgr._validate_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_validator",
                data=[validated],
                urls_processed=1,
            )
        )
        mgr._scrape_content = AsyncMock(
            return_value=make_stage_result(
                stage_name="content_scraper",
                data=[details],
                urls_processed=1,
            )
        )
        mgr._normalize_jobs = AsyncMock(
            return_value=make_stage_result(
                stage_name="normalizer",
                data=[details],
                urls_processed=1,
            )
        )
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        metrics = await mgr.run()

        assert metrics.total_execution_time > 0
        assert mgr.total_collected_count == 1
        assert mgr.total_job_details_count == 1

    @pytest.mark.asyncio
    async def test_collect_failure_breaks_loop(self, default_config):
        """URL 수집 실패 시 루프 중단"""
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                success=False,
                data=[],
                urls_processed=0,
                urls_failed=1,
            )
        )
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        metrics = await mgr.run()

        assert mgr.total_collected_count == 0
        mgr._collect_urls.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_collect_breaks_loop(self, default_config):
        """수집 결과가 빈 리스트면 루프 종료"""
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                data=[],
                urls_processed=0,
            )
        )
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        mgr._collect_urls.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_updated_after_save(self, default_config):
        """DB 저장 후 _existing_posting_ids 캐시 업데이트"""
        default_config.max_scrolls = 1
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        posting = make_job_posting(posting_id="new_1")
        validated = make_validated_url(posting_id="new_1")
        details = make_job_details(posting_id="new_1")

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                data=[posting],
                urls_processed=1,
            )
        )
        mgr._validate_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_validator",
                data=[validated],
                urls_processed=1,
            )
        )
        mgr._scrape_content = AsyncMock(
            return_value=make_stage_result(
                stage_name="content_scraper",
                data=[details],
                urls_processed=1,
            )
        )
        mgr._normalize_jobs = AsyncMock(
            return_value=make_stage_result(
                stage_name="normalizer",
                data=[details],
                urls_processed=1,
            )
        )
        mgr._load_existing_posting_ids = MagicMock()

        # DB saver mock
        mock_db_saver = MagicMock()
        mock_db_saver.batch_id = 1
        mock_db_saver.create_task.return_value = 1
        mock_db_saver.update_task_status = MagicMock()
        mock_db_saver.execute = AsyncMock()
        mock_db_saver.update_batch_status = MagicMock()
        mgr.database_saver = mock_db_saver
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        # 저장 후 캐시에 posting_id 추가됨
        assert "new_1" in mgr._existing_posting_ids

    @pytest.mark.asyncio
    async def test_all_filtered_skips_scraping(self, default_config):
        """필터링 후 신규 0건이면 content scraping 건너뜀"""
        default_config.max_scrolls = 1
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = {"100", "101"}

        posts = [
            make_job_posting(posting_id="100"),
            make_job_posting(posting_id="101"),
        ]

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                data=posts,
                urls_processed=2,
            )
        )
        mgr._validate_urls = AsyncMock()
        mgr._scrape_content = AsyncMock()
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        # 전부 필터링 → validate/scrape 호출 안 됨
        mgr._validate_urls.assert_not_called()
        mgr._scrape_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_called_on_success(self, default_config):
        """정상 종료 시 cleanup 호출"""
        default_config.max_scrolls = 1
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(
                stage_name="url_collector",
                data=[],
                urls_processed=0,
            )
        )
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        mgr.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_called_on_exception(self, default_config):
        """예외 발생 시에도 cleanup 호출"""
        default_config.max_scrolls = 1
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        mgr._collect_urls = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        with pytest.raises(RuntimeError):
            await mgr.run()

        mgr.cleanup.assert_called_once()
