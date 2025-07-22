"""
🌐 사이트별 어댑터 패턴 - 다양한 사이트 지원을 위한 추상화
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.async_api import Page
from job_scraper.pipeline.core.data_models import JobPostingData, PipelineConfig


class Scraper(ABC):
    """스크래핑 로직을 캡슐화하는 기본 클래스"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.base_url = self.get_base_url()
        self.selectors = self.get_selectors()
        self.config = self.get_site_config()
    
    @abstractmethod
    def get_base_url(self) -> str:
        """사이트 기본 URL 반환"""
        pass
    
    @abstractmethod
    def get_selectors(self) -> Dict[str, str]:
        """사이트별 CSS 셀렉터 반환"""
        pass
    
    @abstractmethod
    def get_site_config(self) -> Dict[str, Any]:
        """사이트별 설정 반환"""
        pass
    
    @abstractmethod
    def build_target_url(self, job_category: str) -> str:
        """스크래핑 타겟 URL 생성"""
        pass
    
    @abstractmethod
    async def extract_job_posting_urls(self, page: Page) -> List[JobPostingData]:
        """페이지에서 채용공고 URL 추출"""
        pass
    
    @abstractmethod
    async def scroll_page(self, page: Page, scroll_delay: int) -> bool:
        """페이지 스크롤 실행 (새로운 콘텐츠 로드 여부 반환)"""
        pass
    
    @abstractmethod
    async def wait_for_page_load(self, page: Page):
        """페이지 로드 완료 대기"""
        pass
    
    @abstractmethod
    async def setup_page(self, page: Page):
        """페이지 초기 설정 (리소스 필터링 등)"""
        pass

class WantedScraper(Scraper):
    """Wanted 사이트 스크래퍼"""
    
    def __init__(self):
        super().__init__("wanted")
    
    def get_base_url(self) -> str:
        return "https://www.wanted.co.kr"
    
    def get_selectors(self) -> Dict[str, str]:
        return {
            "post_list": "li.Card_Card__aaatv",
            "job_post_link": 'div[data-cy="job-card"] a',
            "loading_indicator": ".loading",
        }
    
    def get_site_config(self) -> Dict[str, Any]:
        return {
            "job_id_mapping": {
                "파이썬 개발자": 899,
                "머신러닝 엔지니어": 1634,
                "데이터 엔지니어": 655,
                "서버 개발자": 872,
                "빅데이터 엔지니어": 1025,
                "데이터 사이언티스트": 1024,
                ".NET 개발자": 661
            },
            "default_params": {
                "country": "kr",
                "job_sort": "job.recommend_order",
                "years": -1,
                "locations": "all",
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "scroll_delay": 2000,
            "max_retries": 3
        }
    
    def build_target_url(self, job_category: str) -> str:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        job_id = self.config["job_id_mapping"].get(job_category)
        if not job_id:
            raise ValueError(f"Unsupported job category for Wanted: {job_category}")
        
        base_url = os.getenv("WantedScraper").format(job_id=job_id)
        params = self.config["default_params"]
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        return f"{base_url}?{query_string}"
    
    async def extract_job_posting_urls(self, page: Page) -> List[JobPostingData]:
        """Wanted 페이지에서 채용공고 URL 추출"""
        job_posting_urls = []
        
        try:
            job_postings = await page.query_selector_all(self.selectors["post_list"])
            
            for job_post in job_postings:
                try:
                    href_element = await job_post.query_selector(self.selectors["job_post_link"])
                    if not href_element:
                        continue
                    
                    # 속성들 추출 (Wanted 전용)
                    href = await href_element.get_attribute("href")
                    position = await href_element.get_attribute("data-position-name")
                    posting_id = await href_element.get_attribute("data-position-id")
                    company = await href_element.get_attribute("data-company-name")
                    # company_id = await href_element.get_attribute("data-company-id")
                    job_category = await href_element.get_attribute("data-job-category")
                    
                    # job_category_id = await href_element.get_attribute("data-job-category-id")
                    
                    if href and position and company:
                        job_post = JobPostingData(
                            full_url=self.base_url + href,
                            position=position or "Unknown Position",
                            company=company or "Unknown Company",
                            # company_id=company_id or "",
                            posting_id=posting_id or "",
                            job_category=job_category or "",
                            # job_category_id=job_category_id or ""
                        )
                        job_posting_urls.append(job_post)
                        
                except Exception as e:
                    # 개별 job 처리 실패는 무시하고 계속
                    continue
                    
        except Exception as e:
            raise Exception(f"Failed to extract job URLs from Wanted: {e}")
        
        return job_posting_urls
    
    async def scroll_page(self, page: Page, scroll_delay: int) -> bool:
        """Wanted 페이지 스크롤 (새로운 콘텐츠 로드 여부 반환)"""
        # 스크롤 전 job 개수 
        previous_count = len(await page.query_selector_all(self.selectors["post_list"]))
        
        # 스크롤 실행
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(scroll_delay)
        
        # 스크롤 후 job 개수
        current_count = len(await page.query_selector_all(self.selectors["post_list"]))
        
        # 새로운 콘텐츠가 로드되었는지 확인
        return current_count > previous_count
    
    async def wait_for_page_load(self, page: Page):
        """Wanted 페이지 로드 완료 대기"""
        await page.wait_for_timeout(5000)
        await page.wait_for_selector(self.selectors["post_list"], timeout=10000)
    
    async def setup_page(self, page: Page):
        """Wanted 페이지 초기 설정"""
        await page.route("**/*", self._filter_resource)
    
    async def _filter_resource(self, route):
        """리소스 필터링 - 이미지, 폰트 등 차단"""
        request = route.request
        if request.resource_type in ["media", "font", "iframe", "stylesheet"]:
            await route.abort()
        else:
            await route.continue_()


class ScraperFactory:
    """스크래퍼 팩토리"""

    _scrapers = {
        "wanted": WantedScraper,
        # 새로운 사이트 추가 시 여기에 등록
        # "jobkorea": JobKoreaScraper,
        # "saramin": SaraminScraper,
    }
    
    @classmethod
    def create_scraper(cls, site_name: str) -> Scraper:
        """사이트 이름으로 스크래퍼 생성"""
        adapter_class = cls._scrapers.get(site_name.lower())
        if not adapter_class:
            raise ValueError(f"Unsupported site: {site_name}. Supported sites: {list(cls._adapters.keys())}")
        return adapter_class()
    
    @classmethod
    def get_supported_sites(cls) -> List[str]:
        """지원되는 사이트 목록 반환"""
        return list(cls._scrapers.keys())