import requests
import httpx
from urllib.parse import urlparse
from backend.core.logging import setup_logger

logger= setup_logger(__name__)

def is_https_url(url):
    """https 프로토콜 요청이 가능한 주소인가 판단하는 함수"""
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False

def can_parse_url(url):
    """파싱이 가능한 url인가 판단하는 함수 🛠️개선 필요"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if 200 <= response.status_code < 400:
            return True
        else:
            return False
    except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
        print(f"요청 실패: {e}")
        return False

async def can_parse_url_async(url):
    """비동기적으로 파싱이 가능한 url인지 판단하는 함수"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, timeout=5, follow_redirects=True)
            if 200 <= response.status_code < 400:
                return True
            else:
                return False
    except (httpx.RequestError, httpx.TimeoutException) as e:
        print(f"요청 실패: {e}")
        return False


def is_valid_protocol(url):
    """URL이 유효한 프로토콜을 가지고 있는지 확인"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"]
    except Exception:
        return False


def normalize_url(url):
    """URL을 표준 형식으로 변환"""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    elif parsed.scheme == "http":
        url = url.replace("http://", "https://", 1)
    return url


def is_valid_url(url):
    """유효한 URL인지 판단하는 함수"""
    if not is_valid_protocol(url):
        logger.info("Invalid URL protocol")
        return False
    normalized_url = normalize_url(url)
    if is_https_url(normalized_url):
        logger.info(f"Valid URL: {url}")
        return can_parse_url(normalized_url)
    else:
        logger.error(f"Invalid URL: {url}")
        return False

async def is_valid_url_async(url):
    """유효한 URL인지 비동기적으로 판단하는 함수"""
    if not is_valid_protocol(url):
        logger.info("Invalid URL protocol")
        return False
    normalized_url = normalize_url(url)
    if is_https_url(normalized_url):
        logger.info(f"Valid URL: {url}")
        return await can_parse_url_async(normalized_url)
    else:
        logger.error(f"Invalid URL: {url}")
        return False
