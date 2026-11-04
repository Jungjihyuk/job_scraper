"""
스크래핑 관련 Pydantic 스키마
"""

from pydantic import BaseModel


class ScrapingRequest(BaseModel):
    """스크래핑 시작 요청 스키마"""
    scraper_type: str = "wanted"
    job: str = "파이썬 개발자"
    scrape_mode: str = "default"  # "default" | "incremental" | "full"


class ScrapingResponse(BaseModel):
    """스크래핑 응답 스키마"""
    message: str
    scraper_type: str
    job: str


class ScrapingStatusResponse(BaseModel):
    """스크래핑 상태 응답 스키마"""
    is_scraping: bool
    has_process: bool