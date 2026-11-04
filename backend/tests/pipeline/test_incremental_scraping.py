"""FR-066: Incremental Scraping 테스트

scrape_mode별 동작, 조기 종료 로직, full 모드 검증
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.pipeline.manager import PipelineManager
from app.pipeline.data_models import PipelineConfig, StageResult
from tests.conftest import (
    make_job_posting,
    make_stage_result,
    make_validated_url,
    make_job_details,
)


def _make_manager(config: PipelineConfig) -> PipelineManager:
    """테스트용 PipelineManager (모든 Stage mock)"""
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


# ── PipelineConfig scrape_mode ───────────────────────────────


class TestPipelineConfigModes:
    """PipelineConfig의 scrape_mode 기본값 및 설정"""

    def test_default_mode(self):
        config = PipelineConfig(job="서버 개발자")
        assert config.scrape_mode == "default"

    def test_incremental_mode(self):
        config = PipelineConfig(job="서버 개발자", scrape_mode="incremental")
        assert config.scrape_mode == "incremental"

    def test_full_mode(self):
        config = PipelineConfig(job="서버 개발자", scrape_mode="full")
        assert config.scrape_mode == "full"


# ── Incremental 조기 종료 로직 ───────────────────────────────


class TestIncrementalEarlyTermination:
    """Incremental 모드에서 신규 비율 기반 조기 종료"""

    @pytest.mark.asyncio
    async def test_early_termination_after_two_low_yields(
        self, incremental_config
    ):
        """신규 비율 10% 미만이 연속 2회면 조기 종료"""
        mgr = _make_manager(incremental_config)
        mgr._existing_posting_ids = {
            str(i) for i in range(100, 200)
        }

        # 100건 중 5건만 신규 (5%) → low yield
        call_count = 0

        async def mock_collect(self_ignored=None):
            nonlocal call_count
            call_count += 1
            # 모든 posting이 기존 DB에 있는 것 + 약간의 신규
            posts = [
                make_job_posting(posting_id=str(i))
                for i in range(100, 120)  # 100~119, 대부분 기존
            ]
            # 마지막 1개만 신규로 만들기 (5%)
            posts.append(make_job_posting(posting_id=f"new_{call_count}"))
            return make_stage_result(
                stage_name="url_collector",
                data=posts,
                urls_processed=len(posts),
            )

        mgr._collect_urls = AsyncMock(side_effect=mock_collect)
        mgr._validate_urls = AsyncMock(return_value=make_stage_result(
            stage_name="url_validator", data=[], urls_processed=0
        ))
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        # 연속 2회 low yield 후 종료 → 최대 2~3 사이클
        assert call_count <= 3

    @pytest.mark.asyncio
    async def test_low_yield_resets_on_good_batch(
        self, incremental_config
    ):
        """신규 비율이 높은 배치가 오면 low_yield_count 리셋"""
        mgr = _make_manager(incremental_config)
        mgr._existing_posting_ids = set()

        cycle = 0

        async def mock_collect(self_ignored=None):
            nonlocal cycle
            cycle += 1
            if cycle >= 4:
                # 4번째부터 빈 결과 → 루프 종료
                return make_stage_result(
                    stage_name="url_collector",
                    data=[],
                    urls_processed=0,
                )
            return make_stage_result(
                stage_name="url_collector",
                data=[make_job_posting(posting_id=f"new_{cycle}")],
                urls_processed=1,
            )

        mgr._collect_urls = AsyncMock(side_effect=mock_collect)
        mgr._validate_urls = AsyncMock(return_value=make_stage_result(
            stage_name="url_validator",
            data=[make_validated_url(posting_id="new_1")],
            urls_processed=1,
        ))
        mgr._scrape_content = AsyncMock(return_value=make_stage_result(
            stage_name="content_scraper",
            data=[make_job_details(posting_id="new_1")],
            urls_processed=1,
        ))
        mgr._normalize_jobs = AsyncMock(return_value=make_stage_result(
            stage_name="normalizer",
            data=[make_job_details(posting_id="new_1")],
            urls_processed=1,
        ))
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        metrics = await mgr.run()

        # 100% 신규 → low_yield_count는 0으로 유지
        # 4번째에서 빈 결과로 종료
        assert cycle == 4


# ── Full 모드 ────────────────────────────────────────────────


class TestFullMode:
    """Full 모드는 max_scrolls를 무시하고 끝까지 스크롤"""

    @pytest.mark.asyncio
    async def test_full_mode_ignores_max_scrolls(self, full_config):
        """full 모드에서 max_scrolls=50이지만 데이터 없을 때까지 진행"""
        mgr = _make_manager(full_config)
        mgr._existing_posting_ids = set()

        cycle = 0

        async def mock_collect(self_ignored=None):
            nonlocal cycle
            cycle += 1
            if cycle > 55:  # max_scrolls(50)를 넘겨도 진행 가능
                return make_stage_result(
                    stage_name="url_collector",
                    data=[],
                    urls_processed=0,
                )
            return make_stage_result(
                stage_name="url_collector",
                data=[make_job_posting(posting_id=f"p_{cycle}")],
                urls_processed=1,
            )

        mgr._collect_urls = AsyncMock(side_effect=mock_collect)
        mgr._validate_urls = AsyncMock(return_value=make_stage_result(
            stage_name="url_validator",
            data=[make_validated_url()],
            urls_processed=1,
        ))
        mgr._scrape_content = AsyncMock(return_value=make_stage_result(
            stage_name="content_scraper",
            data=[make_job_details()],
            urls_processed=1,
        ))
        mgr._normalize_jobs = AsyncMock(return_value=make_stage_result(
            stage_name="normalizer",
            data=[make_job_details()],
            urls_processed=1,
        ))
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        # max_scrolls=50을 넘어서 56번째까지 실행됨
        assert cycle > full_config.max_scrolls


# ── Default 모드 ─────────────────────────────────────────────


class TestDefaultMode:
    """Default 모드는 max_scrolls 횟수만큼만 실행"""

    @pytest.mark.asyncio
    async def test_default_stops_at_max_scrolls(self, default_config):
        """default 모드에서 max_scrolls 도달 시 종료"""
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = set()

        cycle = 0

        async def mock_collect(self_ignored=None):
            nonlocal cycle
            cycle += 1
            return make_stage_result(
                stage_name="url_collector",
                data=[make_job_posting(posting_id=f"p_{cycle}")],
                urls_processed=1,
            )

        mgr._collect_urls = AsyncMock(side_effect=mock_collect)
        mgr._validate_urls = AsyncMock(return_value=make_stage_result(
            stage_name="url_validator",
            data=[make_validated_url()],
            urls_processed=1,
        ))
        mgr._scrape_content = AsyncMock(return_value=make_stage_result(
            stage_name="content_scraper",
            data=[make_job_details()],
            urls_processed=1,
        ))
        mgr._normalize_jobs = AsyncMock(return_value=make_stage_result(
            stage_name="normalizer",
            data=[make_job_details()],
            urls_processed=1,
        ))
        mgr._load_existing_posting_ids = MagicMock()
        mgr.database_saver = None
        mgr.local_file_saver = None
        mgr.cleanup = AsyncMock()

        await mgr.run()

        assert cycle == default_config.max_scrolls  # 정확히 3
