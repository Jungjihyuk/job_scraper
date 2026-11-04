"""CLI의 실행 결과 줄과 성공 판단 테스트"""

import json
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cli import RESULT_PREFIX, main, print_pipeline_result
from app.pipeline.data_models import PipelineMetrics


def _opt() -> Namespace:
    return Namespace(
        job="서버 개발자",
        max_scrolls=1,
        scroll_delay=0,
        incremental=False,
        full=False,
    )


def _result_line(capsys) -> dict:
    lines = capsys.readouterr().out.splitlines()
    result = [line for line in lines if line.startswith(RESULT_PREFIX)]
    assert len(result) == 1
    return json.loads(result[0].removeprefix(RESULT_PREFIX))


def test_result_line_has_counts(capsys):
    print_pipeline_result(
        PipelineMetrics(
            batch_status="partial",
            total_urls_collected=12,
            saved_count=7,
            failed_count=2,
            skipped_count=1,
        )
    )

    assert _result_line(capsys) == {
        "status": "partial",
        "collected": 12,
        "saved": 7,
        "failed": 2,
        "skipped": 1,
    }


@pytest.mark.parametrize(
    ("status", "success"),
    [
        ("completed", True),  # AC-10: 신규 0건도 여기로 온다
        ("partial", True),
        ("failed", False),  # AC-5
    ],
)
@pytest.mark.asyncio
async def test_main_success_follows_batch_status(status, success, capsys):
    metrics = PipelineMetrics(batch_status=status)
    manager = MagicMock()
    manager.run = AsyncMock(return_value=metrics)

    with patch("app.cli.PipelineManager", return_value=manager):
        assert await main(_opt()) is success

    assert _result_line(capsys)["status"] == status


@pytest.mark.asyncio
async def test_exception_prints_failed_result_and_reraises(capsys):
    manager = MagicMock()
    manager.metrics = PipelineMetrics(saved_count=3)
    manager.run = AsyncMock(side_effect=RuntimeError("boom"))

    with (
        patch("app.cli.PipelineManager", return_value=manager),
        pytest.raises(RuntimeError),
    ):
        await main(_opt())

    result = _result_line(capsys)
    assert result["status"] == "failed"
    assert result["saved"] == 3
