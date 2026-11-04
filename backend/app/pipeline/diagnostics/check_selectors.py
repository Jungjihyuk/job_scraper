#!/usr/bin/env python3
"""실제 원티드 공고를 파이프라인 추출 코드로 읽어 칸별 추출 결과를 점검한다.

사이트 개편이 의심될 때 실행한다. 추출은 ContentScraperStage에 맡기며,
저장 스테이지를 부르지 않으므로 DB에 쓰지 않는다.

Usage:
    uv run python app/pipeline/diagnostics/check_selectors.py
    uv run python app/pipeline/diagnostics/check_selectors.py --limit 5
    uv run python app/pipeline/diagnostics/check_selectors.py --url https://www.wanted.co.kr/wd/347915
    uv run python app/pipeline/diagnostics/check_selectors.py --list-url https://www.wanted.co.kr/wdlist/518/872
"""

import argparse
import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import Page, async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.pipeline.data_models import (
    JobPostingData,
    PipelineConfig,
    ValidatedURL,
)
from app.pipeline.stages.content_scraper import ContentScraperStage
from app.utils.stealth import (
    MODERN_USER_AGENT,
    STEALTH_LAUNCH_ARGS,
    apply_stealth,
)

LIST_SELECTORS = {
    "POST_LIST": "li.Card_Card__aaatv",
    "JOB_POST_LINK": 'div[data-cy="job-card"] a',
}
SAMPLE_LINK = "a[href^='/wd/']"
MAX_SAMPLE_SCROLLS = 10

DEFAULT_LIST_URL = "https://www.wanted.co.kr/wdlist/518/872"
DEFAULT_LIMIT = 20

REQUIRED_FIELDS = ("title", "main_tasks", "requirements")
OPTIONAL_FIELDS = (
    "position_detail",
    "location",
    "location_details",
    "deadline",
    "experience",
    "tags",
)

# 추출 코드가 실패할 때 채우는 대체 문자열. W-002가 없애면 이 목록도 지운다.
PLACEHOLDER_VALUES = {
    "No title",
    "No location",
    "No experience",
    "No position detail",
    "No due time",
    "No work place",
    "Extraction failed",
}


@dataclass
class SelectorResult:
    """목록 페이지 셀렉터 하나의 일치 결과."""

    name: str
    selector: str
    count: int
    sample_text: str


@dataclass
class PostingCheck:
    """공고 한 건의 칸별 추출 결과."""

    url: str
    values: dict[str, object]
    error: str | None = None


def is_extracted(value: object) -> bool:
    """칸의 값을 실제로 읽었는지 판단한다.

    Args:
        value: 추출 코드가 돌려준 칸의 값.

    Returns:
        비어 있지 않고 대체 문자열도 아니면 True.
    """
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() not in PLACEHOLDER_VALUES
    return bool(value)


def missing_fields(check: PostingCheck, fields: tuple[str, ...]) -> list[str]:
    """주어진 칸 중 읽지 못한 칸의 이름을 돌려준다.

    Args:
        check: 공고 한 건의 추출 결과.
        fields: 확인할 칸 이름.

    Returns:
        읽지 못한 칸 이름. 순서는 `fields`를 따른다.
    """
    return [name for name in fields if not is_extracted(check.values.get(name))]


def has_required_failure(checks: list[PostingCheck]) -> bool:
    """필수 칸을 읽지 못한 공고가 있는지 판단한다.

    Args:
        checks: 공고별 추출 결과.

    Returns:
        한 건이라도 필수 칸을 읽지 못했으면 True.
    """
    return any(missing_fields(check, REQUIRED_FIELDS) for check in checks)


@asynccontextmanager
async def open_page() -> AsyncIterator[Page]:
    """파이프라인과 같은 브라우저 설정으로 페이지를 연다.

    Yields:
        스텔스 설정을 적용한 새 페이지.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_LAUNCH_ARGS,
        )
        context = await browser.new_context(
            user_agent=MODERN_USER_AGENT,
        )
        await apply_stealth(context)
        try:
            yield await context.new_page()
        finally:
            await browser.close()


async def check_page_selectors(
    url: str,
    selectors: dict[str, str],
    label: str,
) -> list[SelectorResult]:
    """페이지에서 셀렉터마다 일치하는 요소 수를 잰다.

    Args:
        url: 확인할 페이지 주소.
        selectors: 셀렉터 이름과 값.
        label: 출력에 쓸 이름.

    Returns:
        셀렉터별 결과. 페이지를 열지 못하면 빈 목록.
    """
    results: list[SelectorResult] = []

    async with open_page() as page:
        try:
            response = await page.goto(url, timeout=30000)
            if not response or response.status != 200:
                status = response.status if response else "no response"
                print(f"  page load failed ({status})")
                return results
        except Exception as e:
            print(f"  page load error: {e}")
            return results

        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        print(f"\n{'=' * 60}")
        print(f"  {label}: {url}")
        print(f"{'=' * 60}")

        for name, sel in selectors.items():
            try:
                elements = await page.query_selector_all(sel)
                count = len(elements)
                sample = ""
                if count > 0:
                    sample = (await elements[0].text_content() or "")[:50]

                results.append(SelectorResult(name, sel, count, sample))

                status = "PASS" if count > 0 else "FAIL"
                icon = "✅" if count > 0 else "❌"
                print(f"  {icon} [{status}] {name}: {count} matches")
                if sample:
                    print(f"         sample: '{sample}'")
            except Exception as e:
                results.append(SelectorResult(name, sel, 0, ""))
                print(f"  ❌ [ERROR] {name}: {e}")

    return results


async def collect_sample_urls(list_url: str, limit: int) -> list[str]:
    """목록 페이지에서 점검할 공고 주소를 모은다.

    Args:
        list_url: 원티드 목록 페이지 주소.
        limit: 모을 공고 수.

    Returns:
        중복 없는 공고 주소. 목록에 공고가 적으면 `limit`보다 적을 수 있다.
    """
    urls: list[str] = []

    async with open_page() as page:
        await page.goto(list_url, timeout=30000)
        await page.wait_for_selector(SAMPLE_LINK, timeout=30000)

        for _ in range(MAX_SAMPLE_SCROLLS):
            hrefs = await page.eval_on_selector_all(
                SAMPLE_LINK, "els => els.map(e => e.getAttribute('href'))"
            )
            urls = list(
                dict.fromkeys(urljoin(list_url, href) for href in hrefs)
            )
            if len(urls) >= limit:
                break
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            await page.wait_for_timeout(1500)

    return urls[:limit]


async def check_posting(stage: ContentScraperStage, url: str) -> PostingCheck:
    """공고 한 건을 파이프라인 추출 코드로 읽는다.

    Args:
        stage: 상세 스크래핑 스테이지.
        url: 공고 주소.

    Returns:
        칸별 추출 결과.
    """
    job_url = JobPostingData(
        full_url=url,
        position="",
        company="",
        posting_id=url.rsplit("/", 1)[-1],
        job_category="",
    )
    details = await stage.process_single_item(
        ValidatedURL(job_url=job_url, is_valid=True)
    )
    return PostingCheck(
        url, dict(details.job_description), details.error_message
    )


def print_posting(check: PostingCheck) -> None:
    """공고 한 건의 칸별 값을 앞부분만 출력한다.

    Args:
        check: 공고 한 건의 추출 결과.
    """
    print(f"\n{check.url}")
    if check.error:
        print(f"  ❌ error: {check.error}")
    for name in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        value = check.values.get(name)
        icon = "✅" if is_extracted(value) else "❌"
        print(f"  {icon} {name}: {str(value).strip()[:60]!r}")


def print_summary(checks: list[PostingCheck]) -> None:
    """칸별 추출 건수와 칸을 읽지 못한 공고의 주소를 출력한다.

    Args:
        checks: 공고별 추출 결과.
    """
    print(f"\n{'=' * 60}")
    print(f"  Field summary ({len(checks)} postings)")
    print(f"{'=' * 60}")

    for label, fields in (
        ("required", REQUIRED_FIELDS),
        ("optional", OPTIONAL_FIELDS),
    ):
        for name in fields:
            failed = [c.url for c in checks if missing_fields(c, (name,))]
            print(
                f"  [{label}] {name}: {len(checks) - len(failed)}/{len(checks)}"
            )
            for url in failed:
                print(f"      missing: {url}")


async def run(
    url: str | None, list_url: str, limit: int, check_list: bool
) -> int:
    """점검을 실행하고 종료 코드를 돌려준다.

    Args:
        url: 공고 하나만 점검할 때의 주소.
        list_url: 표본을 고르고 목록 셀렉터를 확인할 페이지 주소.
        limit: 표본 공고 수.
        check_list: 목록 셀렉터도 확인할지 여부.

    Returns:
        점검 공고가 없거나, 필수 칸을 못 읽었거나, 목록 셀렉터가
        실패하면 1. 아니면 0.
    """
    list_results: list[SelectorResult] = []
    if check_list:
        list_results = await check_page_selectors(
            list_url, LIST_SELECTORS, "List Page Selectors"
        )

    urls = [url] if url else await collect_sample_urls(list_url, limit)
    stage = ContentScraperStage(PipelineConfig(job="selector-check"))

    checks: list[PostingCheck] = []
    for posting_url in urls:
        check = await check_posting(stage, posting_url)
        print_posting(check)
        checks.append(check)

    print_summary(checks)

    failed_selectors = [r for r in list_results if r.count == 0]
    for r in failed_selectors:
        print(f"  Failed list selector: {r.name}: {r.selector}")

    return int(
        not checks or has_required_failure(checks) or bool(failed_selectors)
    )


def main() -> None:
    """명령줄 인자를 읽어 점검을 실행한다."""
    parser = argparse.ArgumentParser(
        description="Check Wanted extraction field by field on live postings"
    )
    parser.add_argument(
        "--url",
        help="Check this one posting instead of sampling the list page",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Postings to sample (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--list-url",
        default=DEFAULT_LIST_URL,
        help=f"List page URL (default: {DEFAULT_LIST_URL})",
    )
    parser.add_argument(
        "--no-list",
        action="store_true",
        help="Skip list page selector check",
    )
    args = parser.parse_args()

    sys.exit(
        asyncio.run(run(args.url, args.list_url, args.limit, not args.no_list))
    )


if __name__ == "__main__":
    main()
