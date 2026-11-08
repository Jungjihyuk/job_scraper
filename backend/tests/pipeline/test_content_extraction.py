"""상세 추출 실패 표현 테스트

실패를 대체 문자열 대신 None과 success=False로 돌려주는지 검증
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.data_models import PipelineConfig
from app.pipeline.stages.content_scraper import (
    ContentScraperStage,
    missing_required_fields,
    parse_posted_date,
)
from tests.conftest import make_validated_url

FAKE_VALUES = {
    "No title",
    "No location",
    "No experience",
    "No position detail",
    "No due time",
    "No work place",
    "Extraction failed",
    "Unknown",
}


class TestMissingRequiredFields:
    def test_all_present(self):
        fields = {"title": "t", "main_tasks": "m", "requirements": "r"}
        assert missing_required_fields(fields) == []

    @pytest.mark.parametrize("key", ["main_tasks", "requirements"])
    def test_one_body_field_is_enough(self, key):
        assert missing_required_fields({"title": "t", key: "본문"}) == []

    @pytest.mark.parametrize("title", [None, "", "   "])
    def test_missing_title(self, title):
        fields = {"title": title, "main_tasks": "m"}
        assert missing_required_fields(fields) == ["title"]

    def test_missing_body(self):
        fields = {"title": "t", "main_tasks": None, "requirements": " "}
        assert missing_required_fields(fields) == ["main_tasks/requirements"]

    def test_empty_description(self):
        assert missing_required_fields({}) == [
            "title",
            "main_tasks/requirements",
        ]


class TestParsePostedDate:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2026-03-15", datetime(2026, 3, 15)),
            ("2026-03-15T10:30:00", datetime(2026, 3, 15, 10, 30)),
            ("2026-03-15T10:30:00+09:00", datetime(2026, 3, 15, 10, 30)),
            ("2026-03-15T10:30:00Z", datetime(2026, 3, 15, 10, 30)),
        ],
    )
    def test_valid(self, value, expected):
        assert parse_posted_date(value) == expected

    @pytest.mark.parametrize("value", [None, "", "Unknown", "어제", 20260315])
    def test_invalid_is_none(self, value):
        assert parse_posted_date(value) is None


@pytest.fixture
def stage():
    return ContentScraperStage(PipelineConfig(job="서버 개발자"))


def _broken_page() -> MagicMock:
    """모든 셀렉터 대기와 평가가 실패하는 페이지"""
    page = MagicMock()
    page.wait_for_selector = AsyncMock(side_effect=TimeoutError("없음"))
    page.evaluate = AsyncMock(side_effect=RuntimeError("없음"))
    return page


class TestExtractorsOnFailure:
    @pytest.mark.asyncio
    async def test_no_extractor_returns_fake_value(self, stage):
        """AC-2: 칸을 못 읽으면 None이고 가짜 문자열이 없다"""
        page = _broken_page()
        fields = {}
        for extract in (
            stage._extract_title,
            stage._extract_location,
            stage._extract_experience,
            stage._extract_position_detail,
            stage._extract_job_descriptions,
            stage._extract_deadline,
            stage._extract_work_place,
        ):
            fields.update(await extract(page))

        assert not FAKE_VALUES & {v for v in fields.values()}
        assert all(v is None for v in fields.values())
        assert missing_required_fields(fields)

    @pytest.mark.asyncio
    async def test_tags_failure_uses_tags_key(self, stage):
        assert await stage._extract_company_tags(_broken_page()) == {"tags": []}

    @pytest.mark.asyncio
    async def test_posted_date_failure_is_none(self, stage):
        """AC-3: 게시일을 못 읽으면 None이다"""
        assert await stage._extract_posted_date(_broken_page()) is None

    @pytest.mark.asyncio
    async def test_posted_date_without_field_is_none(self, stage):
        """AC-3: LD+JSON에 게시일이 없으면 None이다"""
        page = MagicMock()
        page.evaluate = AsyncMock(return_value='{"title": "t"}')

        assert await stage._extract_posted_date(page) is None


def _patch_browser(stage, fields):
    """브라우저 없이 process_single_item을 돌리도록 바꾼다"""
    pw = MagicMock()
    pw.stop = AsyncMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    context.close = AsyncMock()
    page = MagicMock()
    page.close = AsyncMock()
    page.route = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    browser.new_context = AsyncMock(return_value=context)
    pw.chromium.launch = AsyncMock(return_value=browser)
    starter = MagicMock()
    starter.start = AsyncMock(return_value=pw)
    stage.delay_range = (0, 0)
    stage._scrape_job_details = AsyncMock(return_value=fields)
    stage._extract_posted_date = AsyncMock(return_value=None)
    return patch.multiple(
        "app.pipeline.stages.content_scraper",
        async_playwright=MagicMock(return_value=starter),
        apply_stealth=AsyncMock(),
    )


class TestProcessSingleItem:
    @pytest.mark.asyncio
    async def test_missing_body_is_failure(self, stage):
        """AC-1: 본문을 못 읽으면 실패이고 빠진 칸이 메시지에 남는다"""
        with _patch_browser(stage, {"title": "제목"}):
            details = await stage.process_single_item(make_validated_url())

        assert details.success is False
        assert "main_tasks/requirements" in details.error_message

    @pytest.mark.asyncio
    async def test_missing_optional_field_is_success_with_none(self, stage):
        """AC-2 · AC-3: 부가 칸만 없으면 성공이고 그 칸은 None이다"""
        fields = {"title": "제목", "main_tasks": "업무", "location": None}
        with _patch_browser(stage, fields):
            details = await stage.process_single_item(make_validated_url())

        assert details.success is True
        assert details.error_message is None
        assert details.location is None
        assert details.location_detail is None
        assert details.experience is None
        assert details.posted_date is None
