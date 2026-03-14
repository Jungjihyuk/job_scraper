from typing import List
from playwright.async_api import async_playwright

from job_scraper.pipeline.core.base_stage import BaseStage
from job_scraper.pipeline.core.data_models import JobPostingData, PipelineConfig
from job_scraper.pipeline.core.site_scraper import ScraperFactory
from job_scraper.utils.stealth import (
    MODERN_USER_AGENT,
    STEALTH_LAUNCH_ARGS,
    apply_stealth,
)


class URLCollectorStage(BaseStage):
    """🌍 채용공고 기본정보 수집 Stage

    실제 역할:
    - 채용공고 목록 페이지를 스크롤하며 새로운 공고 발견
    - 각 공고의 URL + 기본 메타데이터 수집 (company, position, posting_id, job_category)
    - 상세 스크래핑 전 필요한 최소한의 정보만 추출하여 효율성 확보

    수집 데이터 (JobPostingData):
    - full_url: 상세 페이지 URL
    - position: 직무명 (리스트에서 미리 확인 가능)
    - company: 회사명
    - posting_id: 공고 고유 ID
    - job_category: 직무 카테고리

    참고: Stage 이름은 파이프라인 흐름의 직관성을 위해 'URLCollector'로 유지
    """

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

        self.logger.info(
            f"🚀 Initializing browser session for site: {config.scraper_type}, job: {config.job}"
        )

        # 스크래퍼 생성
        self.scraper = ScraperFactory.create_scraper(config.scraper_type)

        # 타겟 URL 생성 (스크래핑 대상 url)
        target_url = self.scraper.build_target_url(config.job)

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=STEALTH_LAUNCH_ARGS,
        )
        self.context = await self.browser.new_context(
            user_agent=MODERN_USER_AGENT,
        )
        await apply_stealth(self.context)
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
        """단일 스크롤로 새로운 URL만 수집 (반복 호출 지원)"""
        # 브라우저 세션이 없으면 초기화
        if self.browser is None:
            await self.initialize_browser(config)

        # 단일 스크롤 실행
        has_new_content = await self._single_scroll(
            self.page, scroll_delay=config.scroll_delay
        )
        if not has_new_content:
            self.logger.info(f"🚧 No new jobs found after scroll")
            return []

        # 새로운 JobPostingData 객체들 수집
        new_job_posting_data = await self._collect_new_job_posting_data(self.page)
        self.logger.info(
            f"✅ Collected {len(new_job_posting_data)} new job postings (total: {len(self.collected_url_set)})"
        )
        return new_job_posting_data

    async def _single_scroll(self, page, scroll_delay: int) -> bool:
        """단일 스크롤 수행하여 새 컨텐츠 로드 여부 반환"""
        # 스크롤 전 상태 확인
        previous_count = len(
            await page.query_selector_all(self.scraper.selectors["post_list"])
        )
        self.logger.info(f"📊 Current job postings: {previous_count}")

        # 사이트별 스크롤 실행
        has_new_content = await self.scraper.scroll_page(page, scroll_delay)

        # 스크롤 후 상태 확인
        current_count = len(
            await page.query_selector_all(self.scraper.selectors["post_list"])
        )
        self.logger.info(f"📈 After scroll: {current_count} total jobs")

        return has_new_content

    async def _collect_new_job_posting_data(self, page) -> List[JobPostingData]:
        """현재 페이지에서 새로운 JobPostingData만 추출 및 중복 제거"""
        new_job_posting_data = []

        # 현재 페이지에서 모든 JobPostingData 객체 추출
        all_job_posting_data = await self.scraper.extract_job_posting_data(page)

        # 새로운 URL만 필터링하여 JobPostingData 수집
        for job_posting in all_job_posting_data:
            if job_posting.full_url not in self.collected_url_set:
                new_job_posting_data.append(job_posting)
                self.collected_url_set.add(job_posting.full_url)
                self.update_metrics(processed=1)
                self.logger.debug(
                    f"🆕 New job posting: {job_posting.position} at {job_posting.company}"
                )

        return new_job_posting_data
