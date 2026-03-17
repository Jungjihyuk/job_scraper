#!/usr/bin/env python3
"""
CSS selector health check for Wanted scraper.

Validates each WantedSelectors CSS selector against a live page
and reports match counts. Run after suspected site redesign.

Usage:
    uv run python scripts/diagnostics/check_selectors.py
    uv run python scripts/diagnostics/check_selectors.py --url https://www.wanted.co.kr/wd/347915
    uv run python scripts/diagnostics/check_selectors.py --list-url https://www.wanted.co.kr/wdlist/518/872
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.utils.stealth import (
    MODERN_USER_AGENT,
    STEALTH_LAUNCH_ARGS,
    apply_stealth,
)

DETAIL_SELECTORS = {
    "CONTENT_WRAPPER": "section.JobContent_descriptionWrapper__RMlfm",
    "TITLE": "h1.wds-58fmok",
    "POSITION_DETAIL": (
        "div.JobDescription_JobDescription__paragraph__wrapper__WPrKC span.wds-h4ga6o"
    ),
    "JOBDESCRIPTION": "div.JobDescription_JobDescription__paragraph__87w8I",
    "COMPANY_TAGS": "ul.CompanyTags_CompanyTags__list__XmzkW li",
    "DEADLINE": "span.wds-1u1yyy",
    "WORK_PLACE": (
        "div.JobWorkPlace_JobWorkPlace__map__location__6pp2d span.wds-1td1qmv"
    ),
    "EXPAND_BUTTON": "button:has(span:text('상세 정보 더 보기'))",
    "LOCATION": (
        "div.JobHeader_JobHeader__Tools__lyxqQ"
        " span.JobHeader_JobHeader__Tools__Company__Info__b9P4Y"
    ),
    "EXPERIENCE": (
        "div.JobHeader_JobHeader__Tools__lyxqQ"
        " span.JobHeader_JobHeader__Tools__Company__Info__b9P4Y"
    ),
}

LIST_SELECTORS = {
    "POST_LIST": "li.Card_Card__aaatv",
    "JOB_POST_LINK": 'div[data-cy="job-card"] a',
}

DEFAULT_DETAIL_URL = "https://www.wanted.co.kr/wd/347915"
DEFAULT_LIST_URL = "https://www.wanted.co.kr/wdlist/518/872"


@dataclass
class SelectorResult:
    name: str
    selector: str
    count: int
    sample_text: str


async def check_page_selectors(
    url: str,
    selectors: dict[str, str],
    label: str,
) -> list[SelectorResult]:
    results: list[SelectorResult] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_LAUNCH_ARGS,
        )
        context = await browser.new_context(
            user_agent=MODERN_USER_AGENT,
        )
        await apply_stealth(context)
        page = await context.new_page()

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
                icon = "\u2705" if count > 0 else "\u274c"
                print(f"  {icon} [{status}] {name}: {count} matches")
                if sample:
                    print(f"         sample: '{sample}'")
            except Exception as e:
                results.append(SelectorResult(name, sel, 0, ""))
                print(f"  \u274c [ERROR] {name}: {e}")

        await browser.close()

    return results


async def run(detail_url: str, list_url: str | None):
    all_results: list[SelectorResult] = []

    detail_results = await check_page_selectors(
        detail_url, DETAIL_SELECTORS, "Detail Page Selectors"
    )
    all_results.extend(detail_results)

    if list_url:
        list_results = await check_page_selectors(
            list_url, LIST_SELECTORS, "List Page Selectors"
        )
        all_results.extend(list_results)

    passed = sum(1 for r in all_results if r.count > 0)
    failed = sum(1 for r in all_results if r.count == 0)

    print(f"\n{'=' * 60}")
    print(f"  Total: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\n  Failed selectors (likely changed by site update):")
        for r in all_results:
            if r.count == 0:
                print(f"    - {r.name}: {r.selector}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="CSS selector health check for Wanted scraper"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_DETAIL_URL,
        help=f"Detail page URL (default: {DEFAULT_DETAIL_URL})",
    )
    parser.add_argument(
        "--list-url",
        default=DEFAULT_LIST_URL,
        help="List page URL (omit to skip list check)",
    )
    parser.add_argument(
        "--no-list",
        action="store_true",
        help="Skip list page selector check",
    )
    args = parser.parse_args()

    list_url = None if args.no_list else args.list_url
    asyncio.run(run(args.url, list_url))


if __name__ == "__main__":
    main()
