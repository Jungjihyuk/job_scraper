import asyncio
from asyncio import Queue
import json
import os
import random
from typing import Dict, List, Union

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx
from lxml import etree
from playwright.async_api import async_playwright

from job_scraper.config.logging_config import setup_logger
from job_scraper.config.settings import JOB_CONFIG
from job_scraper.scrapers.scraper import HTMLContent
from job_scraper.scrapers.scraper import ParsedContent
from job_scraper.scrapers.scraper import WebScraper

logger = setup_logger(__name__)
load_dotenv()


class WantedScraper(WebScraper):

    def __init__(self, job_id, url):
        super().__init__()
        self.job_id = job_id
        self.params = JOB_CONFIG["params"]
        self.base_url = "https://www.wanted.co.kr"
        self.url = url
        self.work_queue = Queue()

    @classmethod
    async def create(cls, job):
        """
        Factory method for creating an instance with a validated URL property.

        """
        job_id = JOB_CONFIG["job_id"].get(job, None)
        if not job_id:
            logger.error(f"Job ID not found for job: {job}")
            raise ValueError(f"Invalid job: {job}")

        url = cls.get_url(cls.__name__, job_id)
        logger.info(f"Get url: {url}")

        try:
            # URL 검증
            if await WebScraper.validate_url(url):
                logger.info(f"URL validation successful {url}")
                return cls(job_id, url)  # if url is valid, create instance
        except Exception as e:
            logger.exception(f"Error during URL validation {e}")

    @classmethod
    def get_url(cls, url_key, job_id) -> str:  
        url = os.getenv(url_key).format(job_id=job_id)
        if url:
            return url
        raise ValueError("URL is empty")

    async def fetch(
        self, session: Union[httpx.AsyncClient, httpx.Client], url: str
    ) -> str:
        try:
            logger.info(f"Fetching URL: {url}")
            response = await session.get(url, params=self.params, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                if (
                    "window.__INITIAL_STATE__" in response.text
                    or "<script>" in response.text
                ):
                    logger.info(
                        "Dynamic page characteristics have been detected."
                    )
                    return await self._fetch_dynamic(self.url, True)
                logger.info("Static page characteristics have been detected.")
                return response.text
            else:
                logger.warning(
                    f"Unexpected status code: {response.status_code}"
                )

        except httpx.RequestError as e:
            logger.exception(f"HTTPX request failed: {e}", exc_info=True)
            raise ValueError(f"HTTPX request failed: {e}")

    async def fetch_all(self, urls: Queue) -> List[str]:
        async with httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            max_redirects=5,
            headers=getattr(self, "headers", {}),  # self.headers
        ) as session:
            tasks = [
                self.fetch(session, await urls.get())
                for _ in range(urls.qsize())
            ]  # 세션을 fetch 메소드에 넘김
            results = await asyncio.gather(*tasks)
            return results

    async def _fetch_dynamic(self, url: str, block_resource=False) -> str:
        browser = None
        try:
            logger.info("🚀 Dynamic page Fetch start...")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=True
                )  # create a browser instance

                # Set the user agent to bypass bot detection
                context = await browser.new_context(
                    extra_http_headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)  \
                                AppleWebKit/537.36 (KHTML, like Gecko) \
                                Chrome/58.0.3029.110 Safari/537.3"
                    }
                )  # create a new context
                page = await context.new_page()  # create a new page

                # Browser request filter
                await page.route(
                    "**/*", self.filter_resource
                )  # block images, media, fonts ,and ads

                await page.goto(url)  # go to the target page
                await page.wait_for_timeout(5000)  # wait for 5 second
                await page.wait_for_selector(
                    "li.Card_Card__WdaEk", timeout=5000
                )  # wait for the job postings to load

                previous_count = len(
                    await page.query_selector_all("li.Card_Card__WdaEk")
                )
                logger.info(f"previous_count: {previous_count}")

                # 스크롤 실행 (스크롤할 때마다 scrape_job_postings 실행)
                await self.auto_scroll(
                    page,
                    max_scrolls=50,
                    scroll_delay=2000,
                    callback=self.scrape_job_postings,
                )

                await self.fetch_job_details()

        except Exception as e:
            logger.info(f"Dynamic page Fetch failed... {e}")
        finally:
            await browser.close()

    async def fetch_job_details(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                extra_http_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)  \
                                AppleWebKit/537.36 (KHTML, like Gecko) \
                                Chrome/58.0.3029.110 Safari/537.3"
                }
            )  # create a new context
            page = await context.new_page()  # create a new page

            while not self.work_queue.empty():
                job_data = await self.work_queue.get()

                for href, metadata in job_data.items():
                    job_url = self.base_url + href
                    logger.info(f"Fetching job details: {job_url}")

                    try:
                        await asyncio.sleep(random.uniform(1, 3))

                        # Browser request filter
                        await page.route(
                            "**/*", self.filter_resource
                        )  # block images, media, fonts ,and ads
                        await page.goto(
                            job_url, timeout=10000
                        )  # delay for 10 seconds

                        await page.locator(
                            "button:has(span:text('상세 정보 더 보기'))"
                        ).click()
                        job_details = await self.scrape_job_details(page)

                        # Extract posted date
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
                        ld_json = json.loads(ld_json)
                        posted_date = ld_json["datePosted"]
                        job_details["게시일"] = posted_date
                        metadata["job_details"] = job_details
                        logger.info(f"Job details fetched: {metadata}")
                    except Exception as e:
                        logger.exception(
                            f"Failed to fetch job details: {job_url}: {e}"
                        )

            await browser.close()

    async def auto_scroll(
        self, page, max_scrolls=50, scroll_delay=2000, callback=None
    ):
        previous_count = len(
            await page.query_selector_all("li.Card_Card__WdaEk")
        )
        logger.info(f"🔢 Initial job postings count: {previous_count}")

        previous_height = await page.evaluate("document.body.scrollHeight")

        for _ in range(max_scrolls):
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            await page.wait_for_timeout(scroll_delay)

            if callback:
                await callback(page)

            current_count = len(
                await page.query_selector_all("li.Card_Card__WdaEk")
            )
            logger.info(f"🐳 Updated job postings count: {current_count}")

            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                logger.info("🚧 No new job postings found. Stopping scroll.")
                break
            previous_height = new_height

    async def scrape_job_postings(self, page):
        try:
            jobs = await page.query_selector_all("li.Card_Card__WdaEk")

            for job in jobs:
                try:
                    href_element = await job.query_selector(
                        'div[data-cy="job-card"] a'
                    )
                    href = await href_element.get_attribute("href")
                    position = await href_element.get_attribute(
                        "data-position-name"
                    )
                    posting_id = await href_element.get_attribute(
                        "data-position-id"
                    )
                    company = await href_element.get_attribute(
                        "data-company-name"
                    )
                    company_id = await href_element.get_attribute(
                        "data-company-id"
                    )
                    job_category = await href_element.get_attribute(
                        "data-job-category"
                    )
                    job_category_id = await href_element.get_attribute(
                        "data-job-category-id"
                    )

                    data = {
                        href: {
                            "position": position,
                            "company": company,
                            "company_id": company_id,
                            "posting_id": posting_id,
                            "job_category": job_category,
                            "job_category_id": job_category_id,
                        }
                    }
                    logger.info(f"Scraped: {href} - {position} at {company}")

                    await self.work_queue.put(data)
                except Exception as e:
                    logger.error(f"Error scraping job postings: {e}")
        except Exception as e:
            logger.error(f"Error scraping job postings: {e}")

    async def scrape_job_details(self, page) -> Dict[str, str]:
        try:
            job_details_divs = await page.query_selector_all(
                "div.JobDescription_JobDescription__paragraph__wrapper__G4CNd > div"
            )
            logger.info(f"Found {len(job_details_divs)} div elements.")

            job_details = dict()

            for div in job_details_divs:
                title_elem = await div.query_selector("h3")
                description_elem = await div.query_selector_all("span")

                title = (
                    await title_elem.text_content()
                    if title_elem
                    else "No title"
                )
                description = (
                    "\n".join(
                        [await span.text_content() for span in description_elem]
                    )
                    if description_elem
                    else "No description"
                )

                job_details[title] = description
                logger.info(f"Scraped job details: {title} - {description}")

            return job_details
        except Exception as e:
            logger.error(f"Error scraping job details: {e}")

    async def filter_resource(self, route):
        request = route.request
        if request.resource_type in ["media", "font", "iframe", "stylesheet"]:
            await route.abort()
        else:
            await route.continue_()

    async def parse(
        self, content: HTMLContent, incremental: bool = False
    ) -> ParsedContent:
        if incremental:
            parser = etree.HTMLParser()
            tree = etree.iterparse(
                content, parser=parser, html=True, encoding="utf-8"
            )
            return tree
        else:
            soup = BeautifulSoup(content, "html.parser")
            return soup

    def set_headers(self, headers):
        return super().set_headers(headers)

    def set_user_agent(self, user_agent):
        return super().set_user_agent(user_agent)

    async def bypass_protection(self):
        return await super().bypass_protection()

    def clean_data(self, data):
        return super().clean_data(data)

    def manipulate_dom(self, dom_tree):
        return super().manipulate_dom(dom_tree)

    def save(self, data, file_format):
        return super().save(data, file_format)

    def handle_error(self, error):
        return super().handle_error(error)
