"""Scraping API / Schema 테스트

ScrapingRequest에 scrape_mode 추가, API 엔드포인트 동작 검증
"""

import asyncio
import json
import sys
from unittest.mock import patch

import pytest

from app.api.routes import scraping
from app.api.routes.scraping import parse_pipeline_result, run_pipeline
from app.schemas.scraping import (
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStatusResponse,
)


class TestScrapingRequest:
    """ScrapingRequest 스키마 테스트"""

    def test_defaults(self):
        req = ScrapingRequest()
        assert req.scraper_type == "wanted"
        assert req.job == "파이썬 개발자"
        assert req.scrape_mode == "default"

    def test_incremental_mode(self):
        req = ScrapingRequest(scrape_mode="incremental")
        assert req.scrape_mode == "incremental"

    def test_full_mode(self):
        req = ScrapingRequest(scrape_mode="full")
        assert req.scrape_mode == "full"

    def test_custom_job(self):
        req = ScrapingRequest(
            job="데이터 엔지니어", scrape_mode="incremental"
        )
        assert req.job == "데이터 엔지니어"
        assert req.scrape_mode == "incremental"


class TestScrapingResponse:

    def test_response(self):
        resp = ScrapingResponse(
            message="스크래핑 시작",
            scraper_type="wanted",
            job="서버 개발자",
        )
        assert resp.message == "스크래핑 시작"


class TestScrapingStatusResponse:

    def test_status(self):
        status = ScrapingStatusResponse(
            is_scraping=True, has_process=True
        )
        assert status.is_scraping is True
        assert status.has_process is True

    def test_idle_status(self):
        status = ScrapingStatusResponse(
            is_scraping=False, has_process=False
        )
        assert status.is_scraping is False


async def _run_with_child(script: str) -> list[dict]:
    """파이프라인 대신 주어진 파이썬 코드를 돌리고 보낸 이벤트를 돌려준다"""
    real_exec = asyncio.create_subprocess_exec
    events: list[dict] = []

    async def fake_exec(*_args, **kwargs):
        return await real_exec(sys.executable, "-c", script, **kwargs)

    async def record(message: str) -> None:
        events.append(json.loads(message))

    with (
        patch("asyncio.create_subprocess_exec", fake_exec),
        patch("app.ws.manager.manager.send_message", record),
    ):
        await run_pipeline("wanted", "서버 개발자")
    return events


RESULT = (
    'PIPELINE_RESULT {"status": "%s", "collected": 5, "saved": 3, '
    '"failed": 1, "skipped": 1}'
)


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_partial_result_reaches_complete_event(self):
        """AC-13 · AC-14: 결과가 이벤트에 담기고 결과 줄은 로그에 나오지 않는다"""
        events = await _run_with_child(
            f"print('진행 로그'); print({RESULT % 'partial'!r})"
        )

        logs = [e["message"] for e in events if e["type"] == "log"]
        assert "진행 로그" in logs
        assert not any("PIPELINE_RESULT" in line for line in logs)
        last = events[-1]
        assert last["type"] == "complete"
        assert "부분 실패" in last["message"]
        assert "✅" not in last["message"]
        assert last["result"] == {
            "status": "partial",
            "collected": 5,
            "saved": 3,
            "failed": 1,
            "skipped": 1,
            "job": "서버 개발자",
        }

    @pytest.mark.asyncio
    async def test_failed_result_reaches_error_event(self):
        """AC-5: 실패 결과는 error 이벤트로 간다"""
        events = await _run_with_child(
            f"import sys; print({RESULT % 'failed'!r}); sys.exit(1)"
        )

        assert events[-1]["type"] == "error"
        assert events[-1]["result"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_no_result_line_uses_exit_code(self):
        events = await _run_with_child("print('끝')")

        assert events[-1]["type"] == "complete"
        assert "result" not in events[-1]

    @pytest.mark.asyncio
    async def test_traceback_last_line_is_logged_before_error(self):
        """AC-15: 종료 직전 traceback 마지막 줄까지 로그로 나온다"""
        events = await _run_with_child("raise RuntimeError('마지막 오류')")

        assert events[-1]["type"] == "error"
        logs = [e["message"] for e in events if e["type"] == "log"]
        assert logs[-1] == "RuntimeError: 마지막 오류"

    @pytest.mark.filterwarnings(
        "ignore::pytest.PytestUnraisableExceptionWarning"
    )
    @pytest.mark.asyncio
    async def test_held_pipe_does_not_block_finish(self):
        """자식이 파이프를 쥐고 있어도 제한 시간 뒤 끝난다"""
        script = (
            "import subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(2)'])\n"
        )
        with patch.object(scraping, "OUTPUT_DRAIN_TIMEOUT_SECONDS", 0.2):
            events = await asyncio.wait_for(_run_with_child(script), timeout=10)

        assert events[-1]["type"] == "complete"


class TestParsePipelineResult:
    @pytest.mark.parametrize(
        "line",
        ["일반 로그", "PIPELINE_RESULT {깨짐", "PIPELINE_RESULT [1]"],
    )
    def test_other_lines_are_none(self, line):
        assert parse_pipeline_result(line) is None
