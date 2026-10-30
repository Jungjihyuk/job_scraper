"""Scraping API / Schema 테스트

ScrapingRequest에 scrape_mode 추가, API 엔드포인트 동작 검증
"""

import pytest

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
