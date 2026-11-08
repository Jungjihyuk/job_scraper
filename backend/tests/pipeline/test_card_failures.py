"""목록 카드 실패 집계 테스트"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.scrapers.base import WantedScraper
from app.pipeline.stages.url_collector import URLCollectorStage
from tests.conftest import make_job_posting


def _card(href: str | None, position: str = "개발자", company: str = "회사"):
    """주어진 href와 텍스트를 가진 카드 요소"""
    link = MagicMock()
    link.get_attribute = AsyncMock(
        side_effect=lambda name: href if name == "href" else "개발"
    )

    def text_element(value: str) -> MagicMock:
        element = MagicMock()
        element.text_content = AsyncMock(return_value=value)
        return element

    async def query(selector: str) -> MagicMock:
        if "position" in selector:
            return text_element(position)
        if "company" in selector:
            return text_element(company)
        return link

    card = MagicMock()
    card.query_selector = AsyncMock(side_effect=query)
    return card


def _page(*cards: MagicMock) -> MagicMock:
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=list(cards))
    return page


class TestExtractJobPostingData:
    @pytest.mark.asyncio
    async def test_card_without_posting_id_is_failure(self):
        """AC-8: posting_id를 얻지 못한 카드는 공고가 되지 않고 실패로 세어진다"""
        scraper = WantedScraper()
        page = _page(_card("/wd/123"), _card("/company/9"), _card(None))

        postings = await scraper.extract_job_posting_data(page)

        assert [p.posting_id for p in postings] == ["123"]
        assert scraper.last_failed_cards == 2

    @pytest.mark.asyncio
    async def test_card_exception_is_failure(self):
        """AC-8: 카드 처리 중 예외가 나도 다른 카드는 계속 읽는다"""
        broken = MagicMock()
        broken.query_selector = AsyncMock(side_effect=RuntimeError("detached"))
        scraper = WantedScraper()

        postings = await scraper.extract_job_posting_data(
            _page(broken, _card("/wd/1"))
        )

        assert len(postings) == 1
        assert scraper.last_failed_cards == 1


class TestCollectorCounting:
    @pytest.mark.asyncio
    async def test_failed_cards_are_not_counted_twice(self):
        """AC-8 · AC-11: 같은 실패 카드를 사이클마다 다시 세지 않는다"""
        stage = URLCollectorStage()
        stage.scraper = MagicMock()
        stage.scraper.extract_job_posting_data = AsyncMock(
            return_value=[make_job_posting(posting_id="1")]
        )

        stage.scraper.last_failed_cards = 2
        await stage._collect_new_job_posting_data(MagicMock())
        assert stage.metrics["items_failed"] == 2

        stage._reset_metrics()
        await stage._collect_new_job_posting_data(MagicMock())
        assert stage.metrics["items_failed"] == 0

        stage._reset_metrics()
        stage.scraper.last_failed_cards = 3
        await stage._collect_new_job_posting_data(MagicMock())
        assert stage.metrics["items_failed"] == 1
