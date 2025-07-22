from typing import List
from playwright.async_api import async_playwright

from job_scraper.pipeline.core.base_stage import BaseStage
from job_scraper.pipeline.core.data_models import JobPostingData, PipelineConfig
from job_scraper.pipeline.core.site_scraper import ScraperFactory


class URLCollectorStage(BaseStage):
    """🌍 URL 수집 Stage - 사이트 어댑터를 통한 확장 가능한 URL 수집"""
    
    def __init__(self):
        super().__init__("URLCollector", enable_duplicate_check=True)
        self.collected_url_set = set()  # 이미 수집한 url 저장
        self.browser = None  # 브라우저 세션 유지
        self.page = None  # 페이지 세션 유지
        self.context = None  # 컨텍스트 세션 유지
        self.scraper = None  # 스크래퍼
    
    async def initialize_browser(self, config: PipelineConfig):
        """브라우저 세션 초기화"""
        if self.browser is not None:
            return  # 이미 초기화됨
        
        self.logger.info(f"🚀 Initializing browser session for site: {config.scraper_type}, job: {config.job}")
        
        # 스크래퍼 생성
        self.scraper = ScraperFactory.create_scraper(config.scraper_type)
        
        # 타겟 URL 생성 (스크래핑 대상 url)
        target_url = self.scraper.build_target_url(config.job)
        
        # 브라우저 세션 시작
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            extra_http_headers={
                "User-Agent": self.scraper.config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            }
        )
        self.page = await self.context.new_page()
        
        # 페이지 초기 설정 (사이트별)
        await self.scraper.setup_page(self.page)
        
        # 타겟 페이지로 이동
        await self.page.goto(target_url)
        
        # 페이지 로드 대기 (사이트별)
        await self.scraper.wait_for_page_load(self.page)
        
        self.logger.info("✅ Browser session initialized")
    
    async def close_browser(self):
        """브라우저 세션 종료"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            self.context = None
            self.logger.info("🔒 Browser session closed")
    
    async def process(self, config: PipelineConfig) -> List[JobPostingData]:
        """무한스크롤로 새로운 URL만 수집 (반복 호출 지원)"""
        # 브라우저 세션이 없으면 초기화
        if self.browser is None:
            await self.initialize_browser(config)
        
        # 단일 스크롤 실행
        new_job_posts = await self._infinite_scroll(self.page, scroll_delay=config.scroll_delay)
        self.logger.info(f"✅ Collected {len(new_job_posts)} new URLs (total: {len(self.collected_url_set)})")
        return new_job_posts

    async def _infinite_scroll(self, page, scroll_delay: int) -> List[JobPostingData]:
        """단일 스크롤 실행 및 새로운 URL만 수집"""
        new_job_posts = []
        
        # 스크롤 전 상태 확인
        previous_count = len(await page.query_selector_all(self.scraper.selectors["post_list"]))
        self.logger.info(f"📊 Current job postings: {previous_count}")
        
        # 사이트별 스크롤 실행
        has_new_content = await self.scraper.scroll_page(page, scroll_delay)
        
        if not has_new_content:
            self.logger.info(f"🚧 No new jobs found after scroll")
            return []  # 새로운 URL이 없으면 빈 리스트 반환
        
        # 현재 페이지에서 새로운 URL만 추출
        job_posting_urls = await self.scraper.extract_job_posting_urls(page)
        for job_post in job_posting_urls:
            if job_post.full_url not in self.collected_url_set:
                new_job_posts.append(job_post)
                self.collected_url_set.add(job_post.full_url)
                self.update_metrics(processed=1)
                self.logger.debug(f"🆕 New URL: {job_post.full_url}")
        current_count = len(await page.query_selector_all(self.scraper.selectors["post_list"]))
        self.logger.info(f"📈 After scroll: {current_count} total jobs, {len(new_job_posts)} new URLs")
        return new_job_posts
    
