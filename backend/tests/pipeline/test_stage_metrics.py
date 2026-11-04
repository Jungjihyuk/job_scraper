"""스테이지 메트릭 단위 테스트

사이클마다 실행해도 건수가 쌓이지 않는지, 실행 시간이 0으로 잘리지 않는지 검증
"""

import pytest

from app.pipeline.data_models import PipelineMetrics
from app.pipeline.stages.base import AsyncBatchStage, BaseStage
from tests.conftest import make_job_details


class CountingStage(BaseStage):
    """받은 수만큼 처리 건수를 세는 스테이지"""

    async def process(self, data: int) -> int:
        self.update_metrics(processed=data)
        return data


class FailingStage(BaseStage):
    """예외를 내는 스테이지"""

    async def process(self, data: int) -> int:
        raise RuntimeError("boom")


class DetailStage(AsyncBatchStage):
    """받은 JobDetails를 그대로 돌려주는 배치 스테이지"""

    async def process_single_item(self, item):
        return item


class TestStageMetrics:
    @pytest.mark.asyncio
    async def test_repeated_execute_does_not_accumulate(self):
        """AC-11: 두 번째 실행 결과에 첫 번째 건수가 섞이지 않는다"""
        stage = CountingStage("counting")

        first = await stage.execute(3)
        second = await stage.execute(2)

        assert first.urls_processed == 3
        assert second.urls_processed == 2

    @pytest.mark.asyncio
    async def test_sub_second_execution_time_is_not_zero(self):
        """AC-12: 1초 미만 실행도 0이 아닌 시간으로 남는다"""
        result = await CountingStage("counting").execute(1)

        assert 0 < result.execution_time < 1

    @pytest.mark.asyncio
    async def test_failed_stage_keeps_execution_time(self):
        """예외로 끝난 스테이지도 시간과 오류를 남긴다"""
        result = await FailingStage("failing").execute(1)

        assert result.success is False
        assert result.execution_time > 0
        assert "boom" in result.error_message

    @pytest.mark.asyncio
    async def test_batch_stage_counts_failed_results(self):
        """AC-12: success=False로 돌아온 항목은 실패로 센다"""
        items = [
            make_job_details(posting_id="1"),
            make_job_details(posting_id="2", success=False),
        ]

        result = await DetailStage("detail").execute(items)

        assert result.urls_processed == 1
        assert result.urls_failed == 1
        assert len(result.data) == 2

    def test_success_rate_uses_real_counts(self):
        """AC-12: 성공률은 성공 건수를 처리 건수로 나눈 값이다"""
        metrics = PipelineMetrics(successful_scrapes=3, failed_scrapes=1)

        assert metrics.get_success_rate() == 75.0
