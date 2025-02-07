from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from bs4 import BeautifulSoup
from lxml.etree import _ElementTree
from playwright.async_api import ElementHandle
from selenium.webdriver.remote.webelement import WebElement

from job_scraper.config.settings import HEADERS, USER_AGENTS
from job_scraper.utils.url_validator import is_valid_url
from job_scraper.config.logging_config import setup_logger

logger= setup_logger(__name__)

# Type alias definition
HTMLContent = Union[str, ElementHandle, WebElement]
ParsedContent = Union[_ElementTree, BeautifulSoup, Dict[str, Any]]


class WebScraper(ABC):

    def __init__(self):
        self.headers = HEADERS
        self.user_agents = USER_AGENTS

    @abstractmethod
    async def fetch(self, url: str) -> HTMLContent:
        """
        Fetch HTML from the requested URL

        Args:
            url (str): The URL of the webpage to be scraped.
                       This can be a either a static page or a dynamic page.

        Returns:
            Union[str, ElementHandle, WebElement]:
            - Static page: Return HTML as a string.
            - Dynamic page: Return a DOM tree (e.g., ElementHandle).
        """
        pass

    @abstractmethod
    async def parse(self, content: HTMLContent) -> ParsedContent:
        """
        Parse the HTML

        Args:
            content (Union[str, ElementHandle, WebElement]):
                - HTML string for static pages.
                - DOM tree (ElementHandle or WebElement) for dynamic pages.

        Returns:
            Union[_ElementTree, BeautifulSoup, Dict[str, Any]]:
                - BeautifulSoup or lxml Dom tree
                - Structured data (e.g., dict, list)
        """
        pass

    @abstractmethod
    def set_headers(self, headers: Dict[str, str]):
        """Set custom HTTP headers"""
        pass

    @abstractmethod
    def set_user_agent(self, user_agent: List[str]):
        """
        Set a random user agent from a list for each request
        to bypass anti-scraping mechanisms.
        
        This helps to avoid detection by websites that block
        scrapers based on repeated or specific user agent strings.
        """
        pass

    @abstractmethod
    async def bypass_protection(self):
        """Bypass anti-scraping mechanisms"""
        pass
    
    @abstractmethod
    async def get_url(self): 
        pass
    
    @staticmethod
    async def validate_url(url: str) -> bool:
        """
        Validate the URL by checking its format and existencd. 
        
        This method should: 
        - Verify if the URL format is correct using regex or other validation techniques.
        - Make a request to check if the URL is accessible. 
        
        Return `True` if the URL is valid and reachable, otherwise `ValueError` 
        """
        try:
            if not is_valid_url(url): 
                raise ValueError(f"Invalid URL: {url}")

            return True 
        except Exception as e:
            logger.error(f"Error during URL validation: {e}")

    @abstractmethod
    def clean_data(self, data):
        """Post-process and clean the parsed data"""
        pass

    @abstractmethod
    def manipulate_dom(self, dom_tree):
        """Mainpulate the prased Dom tree"""
        pass

    @abstractmethod
    def save(self, data, file_format: str):
        """Save the parsed data in a specific format"""
        pass

    @abstractmethod
    def handle_error(self, error: Exception):
        """Handle errors that occur during scraping"""
        pass
