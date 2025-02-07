import asyncio as asyc
from typing import Any, List, Type

import httpx

from job_scraper.config.logging_config import setup_logger
from job_scraper.scrapers.scraper import WebScraper

logger = setup_logger(__name__)


class ScraperManager:
    def __init__(
        self, scraper_classes: List[Type[WebScraper]], jobs: List[Any]
    ):
        """
        Initialize the ScraperManager with a list of scraper instance.

        Args:
            scrapers (List[Type[WebScraper]]): List of scraper instance to manage.
        """
        if len(scraper_classes) != len(jobs):
            raise ValueError(
                "The number of scrapers must match the number of parameter sets."
            )

        self.scraper_classes = scraper_classes
        self.task_queue = asyc.Queue()
        self.jobs = jobs

        self.logger = setup_logger(__name__)

    async def run(self):
        """
        Orchestrates the scraping process for all scrapers in the manager.
        """

        for Scraper, job in zip(self.scraper_classes, self.jobs):
            try:
                self.logger.info(f"Starting scraper: {Scraper.__name__}")
                # Create a new instance of the scraper
                wscraper = await Scraper.create(job)

                async with httpx.AsyncClient() as session:
                    await wscraper.fetch(session, wscraper.url)

            except Exception as e:
                self.logger.error(
                    f"Error in {Scraper.__name__}: {e}", exc_info=True
                )
