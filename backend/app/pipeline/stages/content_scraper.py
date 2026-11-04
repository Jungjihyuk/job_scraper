import asyncio
import json
import random
import time
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page

from app.pipeline.stages.base import AsyncBatchStage
from app.pipeline.data_models import (
    ValidatedURL,
    JobDetails,
    PipelineConfig,
)
from app.utils.stealth import (
    MODERN_USER_AGENT,
    STEALTH_LAUNCH_ARGS,
    apply_stealth,
)


class WantedSelectors:
    """🎯 Wanted 사이트 셀렉터 상수"""

    CONTENT_WRAPPER = "section.JobContent_descriptionWrapper__RMlfm"
    TITLE = "h1"
    POSITION_DETAIL = "div[class*='JobDescription__paragraph__wrapper__'] span"
    JOBDESCRIPTION = "div.JobDescription_JobDescription__paragraph__87w8I"
    COMPANY_TAGS = "ul.CompanyTags_CompanyTags__list__XmzkW li"
    DEADLINE = "article[class*='JobDueTime_JobDueTime__'] span"
    WORK_PLACE = "div[class*='JobWorkPlace__map__location__'] span"
    EXPAND_BUTTON = "button:has(span:text('상세 정보 더 보기'))"
    LOCATION = "div.JobHeader_JobHeader__Tools__lyxqQ span.JobHeader_JobHeader__Tools__Company__Info__b9P4Y"
    EXPERIENCE = "div.JobHeader_JobHeader__Tools__lyxqQ span.JobHeader_JobHeader__Tools__Company__Info__b9P4Y"


class ContentScraperStage(AsyncBatchStage):
    """컨텐츠 스크래핑 Stage - 상세 정보 수집"""

    def __init__(
        self, config: PipelineConfig, batch_size: int = 6, expand_wait: int = 7000
    ):
        super().__init__("ContentScraper", batch_size=batch_size)
        self.delay_range = (1.0, 3.0)  # 요청 간격 증가 (초)
        self.playwright = None
        self.selectors = WantedSelectors()
        self.config = config
        self.expand_wait = expand_wait

    async def process_single_item(self, validated_url: ValidatedURL) -> JobDetails:
        """단일 URL 상세 정보 스크래핑"""
        start_time = time.time()

        # 유효하지 않은 URL은 스킵
        if not validated_url.is_valid:
            self.logger.debug(
                f"🚫 Skipping invalid URL: {validated_url.job_url.full_url}"
            )
            return JobDetails(
                job_url=validated_url.job_url,
                job_description={},
                success=False,
                error_message="URL is not valid",
                scraping_duration=time.time() - start_time,
            )

        browser = None
        context = None
        page = None
        try:
            # 랜덤 딜레이 (서버 부하 방지)
            await asyncio.sleep(random.uniform(*self.delay_range))

            self.logger.info(
                f"🔍 Scraping job details: {validated_url.job_url.full_url}"
            )

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=STEALTH_LAUNCH_ARGS,
            )

            context = await browser.new_context(
                user_agent=MODERN_USER_AGENT,
            )
            await apply_stealth(context)
            page = await context.new_page()

            # 리소스 필터링 설정
            await page.route("**/*", self._filter_resource)

            await page.goto(validated_url.job_url.full_url, timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)

            # 사이트별 상세 정보 스크래핑
            job_description = await self._scrape_job_details(page)

            # 게시일 추출 (사이트별)
            posted_date = await self._extract_posted_date(page)

            scraping_duration = time.time() - start_time

            job_details = JobDetails(
                job_url=validated_url.job_url,
                job_field=self.config.job,
                job_description=job_description,
                posted_date=posted_date,
                success=True,
                scraping_duration=scraping_duration,
                experience=job_description.get("experience", ""),
                location=job_description.get("location", ""),
                location_detail=job_description.get("location_details", ""),
            )

            self.logger.info(
                f"✅ Successfully scraped: {validated_url.job_url.position} at {validated_url.job_url.company}"
            )
            return job_details

        except Exception as e:
            scraping_duration = time.time() - start_time
            error_msg = str(e)

            self.logger.error(
                f"❌ Failed to scrape {validated_url.job_url.full_url}: {e}"
            )

            return JobDetails(
                job_url=validated_url.job_url,
                job_description={},
                success=False,
                error_message=error_msg,
                scraping_duration=scraping_duration,
            )

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

            if context:
                try:
                    await context.close()
                except Exception:
                    pass

            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

            # Playwright 정리
            if "playwright" in locals():
                try:
                    await playwright.stop()
                except Exception:
                    pass

    async def _scrape_job_details(self, page: Page) -> Dict[str, str]:
        """📋 Wanted 사이트 상세 정보 스크래핑 - 메인 메소드"""
        try:
            # 페이지 로딩 대기 (더 긴 타임아웃)
            await page.wait_for_selector(self.selectors.CONTENT_WRAPPER, timeout=45000)
            # 추가 안정화 대기
            await page.wait_for_timeout(1000)

            # "상세 정보 더 보기" 버튼 클릭
            await self._click_expand_button(page)

            job_details = {}

            # 📝 각 요소별 개별 추출 (실패해도 다른 데이터는 수집 가능)
            job_details.update(await self._extract_title(page))
            job_details.update(await self._extract_position_detail(page))
            job_details.update(await self._extract_job_descriptions(page))
            job_details.update(await self._extract_company_tags(page))
            job_details.update(await self._extract_deadline(page))
            job_details.update(await self._extract_work_place(page))
            job_details.update(await self._extract_experience(page))
            job_details.update(await self._extract_location(page))

            return job_details

        except Exception as e:
            self.logger.error(f"❌ Error scraping job details: {e}")
            return {}

    async def _click_expand_button(self, page: Page) -> None:
        """🔽 '상세 정보 더 보기' 버튼 클릭 with retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 버튼 존재 확인 후 클릭
                expand_button = page.locator(self.selectors.EXPAND_BUTTON)
                if await expand_button.is_visible():
                    await expand_button.click()
                    await page.wait_for_timeout(
                        self.expand_wait
                    )  # 로딩 대기 (headless 모드 최적화)
                    # 네트워크 유휴 상태 확인 (더 긴 대기)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    self.logger.debug("✅ '상세 정보 더 보기' 버튼 클릭 성공")
                    return
                else:
                    self.logger.debug(
                        "⚠️ '상세 정보 더 보기' 버튼이 보이지 않음 (이미 확장되어 있을 수 있음)"
                    )
                    return
            except Exception as e:
                self.logger.debug(
                    f"⚠️ '상세 정보 더 보기' 버튼 클릭 시도 {attempt + 1}/{max_retries} 실패: {e}"
                )
                if attempt < max_retries - 1:
                    await page.wait_for_timeout(2000)  # 재시도 전 대기
                else:
                    self.logger.debug(
                        "⚠️ '상세 정보 더 보기' 버튼 클릭 최종 실패 - 계속 진행"
                    )

    async def _extract_title(self, page: Page) -> Dict[str, str]:
        """📌 제목 추출"""
        try:
            await page.wait_for_selector(self.selectors.TITLE, timeout=10000)
            title_elem = await page.query_selector(self.selectors.TITLE)
            title = await title_elem.text_content() if title_elem else "No title"
            self.logger.debug(f"📌 title: {title}")
            return {"title": title}
        except Exception as e:
            self.logger.warning(f"⚠️ 제목 추출 실패: {e}")
            return {"title": "No title"}

    async def _extract_location(self, page: Page) -> Dict[str, str]:
        """📍 위치 추출"""
        try:
            await page.wait_for_selector(self.selectors.LOCATION, timeout=10000)

            location_elem = await page.query_selector_all(self.selectors.LOCATION)
            location = (
                await location_elem[0].text_content()
                if location_elem
                else "No location"
            )
            self.logger.debug(f"📍 location: {location}")
            return {"location": location}

        except Exception as e:
            self.logger.warning(f"⚠️ 위치 추출 실패: {e}")
            return {"location": "No location"}

    async def _extract_experience(self, page: Page) -> Dict[str, str]:
        """⭐️ 경력 추출"""
        try:
            await page.wait_for_selector(self.selectors.EXPERIENCE, timeout=10000)
            experience_elem = await page.query_selector_all(self.selectors.EXPERIENCE)
            experience = (
                await experience_elem[1].text_content()
                if experience_elem
                else "No experience"
            )
            self.logger.debug(f"⭐️ experience: {experience}")
            return {"experience": experience}

        except Exception as e:
            self.logger.warning(f"⚠️ 경력 추출 실패: {e}")
            return {"experience": "No experience"}

    # async def _extract_preferred(self, page: Page) -> Dict[str, str]:
    #     """👍 우대 사항 추출"""
    #     try:
    #         await page.wait_for_selector(self.selectors.PREFERRED, timeout=10000)
    #         preferred_elem = await page.query_selector(self.selectors.PREFERRED)
    #         preferred = await preferred_elem.text_content() if preferred_elem else "No preferred"
    #         self.logger.debug(f"⭐️ experience: {preferred}")
    #         return {"experience": preferred}

    #     except Exception as e:
    #         self.logger.warning(f"⚠️ 우대 사항 추출 실패: {e}")
    #         return {"preferred": "No preferred"}

    # async def _extract_benefits(self, page: Page) -> Dict[str, str]:
    #     """🎁 혜택 및 복지 사항 추출"""
    #     try:
    #         await page.wait_for_selector(self.selectors.BENEFITS, timeout=10000)
    #         benefits_elem = await page.query_selector(self.selectors.BENEFITS)
    #         benefits = await benefits_elem.text_content() if benefits_elem else "No benefits"
    #         self.logger.debug(f"⭐️ benefits: {benefits}")
    #         return {"benefits": benefits}

    #     except Exception as e:
    #         self.logger.warning(f"⚠️ 혜택 및 복지 사항 추출 실패: {e}")
    #         return {"benefits": "No benefits"}

    async def _extract_position_detail(self, page: Page) -> Dict[str, str]:
        """🎯 포지션 상세 추출"""
        try:
            await page.wait_for_selector(self.selectors.POSITION_DETAIL, timeout=10000)
            detail_position = await page.query_selector(self.selectors.POSITION_DETAIL)
            position_text = (
                await detail_position.text_content()
                if detail_position
                else "No position detail"
            )
            self.logger.debug(f"🎯 포지션 상세: {position_text}")
            return {"position_detail": position_text}
        except Exception as e:
            self.logger.warning(f"⚠️ 포지션 상세 추출 실패: {e}")
            return {"position_detail": "No position detail"}

    # async def _extract_tasks_qualification(self, page: Page) -> Dict[str, str]:
    #     """💼 주요 업무 추출"""
    #     try:
    #         # h3 요소들을 모두 찾아서 "주요 업무" 제목 찾기
    #         await page.wait_for_selector(self.selectors.WORK_QUALIFY, timeout=10000)
    #         task_qualification = await page.query_selector_all(self.selectors.WORK_QUALIFY)

    #         details = dict()
    #         for title, text in zip(['main_tasks', 'requirements'], task_qualification):
    #             content = await text.text_content()
    #             details[title] = content
    #             self.logger.debug(f"💼 주요업무/자격요건: {content}")

    #         return details

    #     except Exception as e:
    #         self.logger.warning(f"⚠️ 주요 업무 추출 실패: {e}")
    #         return {"main_tasks": "No major tasks",
    #                 "requirements": "No qualifications"}

    async def _extract_job_descriptions(self, page: Page) -> Dict[str, str]:
        """💼 구조화된 섹션별 데이터 추출"""
        try:
            await page.wait_for_selector(self.selectors.JOBDESCRIPTION, timeout=10000)

            job_descriptions = await page.query_selector_all(
                self.selectors.JOBDESCRIPTION
            )
            jds = {}

            for jd in job_descriptions:
                content = await jd.text_content()
                if "우대사항" in content:
                    jds["preferred"] = content.replace("우대사항", "")
                if "주요업무" in content:
                    jds["main_tasks"] = content.replace("주요업무", "")
                if "자격요건" in content:
                    jds["requirements"] = content.replace("자격요건", "")
                if "혜택 및 복지" in content:
                    jds["benefits"] = content.replace("혜택 및 복지", "")
                if "채용 전형" in content:
                    jds["hiring_process"] = content.replace("채용 전형", "")

            return jds

        except Exception as e:
            self.logger.error(f"❌ 구조화된 추출 실패: {e}")
            return {
                "main_tasks": "Extraction failed",
                "requirements": "Extraction failed",
                "preferred": "Extraction failed",
                "benefits": "Extraction failed",
                "hiring_process": "Extraction failed",
            }

    async def _extract_company_tags(self, page: Page) -> Dict[str, List[str]]:
        """🏷️ 회사 태그 추출"""
        try:
            await page.wait_for_selector(self.selectors.COMPANY_TAGS, timeout=10000)
            company_tags_elements = await page.query_selector_all(
                self.selectors.COMPANY_TAGS
            )
            if company_tags_elements:
                company_tags = []
                for tag_elem in company_tags_elements:
                    tag_text = await tag_elem.text_content()
                    if tag_text and tag_text.strip():
                        company_tags.append(tag_text.strip())

                self.logger.debug(f"🏷️ 회사 태그: {company_tags}")
                return {"tags": company_tags}

            return {"tags": []}

        except Exception as e:
            self.logger.warning(f"⚠️ 회사 태그 추출 실패: {e}")
            return {"회사 태그": []}

    async def _extract_deadline(self, page: Page) -> Dict[str, str]:
        """📅 마감일 추출"""
        try:
            await page.wait_for_selector(self.selectors.DEADLINE, timeout=10000)
            due_time_elem = await page.query_selector(self.selectors.DEADLINE)
            due_time = (
                await due_time_elem.text_content() if due_time_elem else "No due time"
            )
            self.logger.debug(f"📅 마감일: {due_time}")
            return {"deadline": due_time}
        except Exception as e:
            self.logger.warning(f"⚠️ 마감일 추출 실패: {e}")
            return {"deadline": "No due time"}

    async def _extract_work_place(self, page: Page) -> Dict[str, str]:
        """🌍 근무 지역 추출"""
        try:
            await page.wait_for_selector(self.selectors.WORK_PLACE, timeout=10000)
            work_place_elem = await page.query_selector(self.selectors.WORK_PLACE)
            work_place = (
                await work_place_elem.text_content()
                if work_place_elem
                else "No work place"
            )
            self.logger.debug(f"🌍 근무 지역: {work_place}")
            return {"location_details": work_place}
        except Exception as e:
            self.logger.warning(f"⚠️ 근무 지역 추출 실패: {e}")
            return {"location_details": "No work place"}

    async def _extract_posted_date(self, page: Page) -> str:
        """📆 게시일 추출 (LD+JSON에서)"""
        try:
            ld_json = await page.evaluate(
                """
                () => {
                    const script = document.querySelector(
                        'script[type="application/ld+json"]'
                    );
                    return script ? script.innerText : null;
                }
                """
            )

            if ld_json:
                ld_data = json.loads(ld_json)
                posted_date = ld_data.get("datePosted", "Unknown")
                self.logger.debug(f"📆 게시일: {posted_date}")
                return posted_date

            return "Unknown"

        except Exception as e:
            self.logger.warning(f"⚠️ 게시일 추출 실패: {e}")
            return "Unknown"

    async def _filter_resource(self, route):
        """🚫 리소스 필터링 - 이미지, 폰트 등 차단 (일부 허용)"""
        request = route.request
        if request.resource_type in ["media", "font", "iframe"]:
            await route.abort()
        else:
            await route.continue_()

    async def process(self, validated_urls: List[ValidatedURL]) -> List[JobDetails]:
        """📋 검증된 URL 목록에서 상세 정보 스크래핑"""
        self.logger.info(f"📄 Starting content scraping for {len(validated_urls)} URLs")

        try:
            # 부모 클래스의 배치 처리 실행
            job_details_list = await super().process(validated_urls)

            # 통계 출력
            successful_count = sum(1 for details in job_details_list if details.success)
            failed_count = len(job_details_list) - successful_count

            self.logger.info(
                f"📊 Content scraping completed: "
                f"{successful_count} successful, {failed_count} failed"
            )

            return job_details_list

        except Exception as e:
            self.logger.error(f"❌ Content scraping process failed: {e}")
            raise

        finally:
            # Playwright 세션 정리
            await self._cleanup_playwright()

    async def _cleanup_playwright(self):
        """🔒 Playwright 세션 정리"""
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            self.logger.info("🔒 Playwright session cleaned up")

    async def cleanup(self):
        """🧹 Stage 정리 작업"""
        await self._cleanup_playwright()
        await super().cleanup()
