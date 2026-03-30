#!/usr/bin/env python3
"""
Capture diagnostic artifacts when scraping fails.

Navigates to a URL and captures screenshot + HAR trace regardless
of success or failure. Useful for post-mortem analysis when
ContentScraper times out.

Usage:
    uv run python backend/pipeline/diagnostics/capture_failure.py
    uv run python backend/pipeline/diagnostics/capture_failure.py --url https://www.wanted.co.kr/wd/12345
    uv run python backend/pipeline/diagnostics/capture_failure.py --timeout 60000
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

DEFAULT_URL = "https://www.wanted.co.kr/wd/347915"
OUTPUT_DIR = Path("logs/diagnostics")
TIMEOUT_MS = 30000


async def capture(url: str, timeout_ms: int, headed: bool = False):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_path = OUTPUT_DIR / f"capture_{timestamp}.png"
    har_path = OUTPUT_DIR / f"capture_{timestamp}.har"
    meta_path = OUTPUT_DIR / f"capture_{timestamp}_meta.json"

    print(f"Capturing: {url}")
    print(f"  timeout: {timeout_ms}ms")
    print(f"  output:  {OUTPUT_DIR}/")

    metadata: dict[str, object] = {
        "url": url,
        "timestamp": timestamp,
        "timeout_ms": timeout_ms,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            record_har_path=str(har_path),
        )
        page = await context.new_page()

        try:
            response = await page.goto(url, timeout=timeout_ms)
            metadata["status"] = response.status if response else None
            metadata["outcome"] = "loaded"

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                metadata["networkidle"] = "timeout"

        except Exception as e:
            metadata["outcome"] = "failed"
            metadata["error"] = str(e)
            print(f"\n  Page load failed: {e}")

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            metadata["screenshot"] = str(screenshot_path)
            print(f"\n  Screenshot: {screenshot_path}")
        except Exception as e:
            print(f"\n  Screenshot failed: {e}")

        html_len = len(await page.content())
        metadata["html_length"] = html_len

        title = await page.title()
        metadata["page_title"] = title

        current_url = page.url
        metadata["final_url"] = current_url
        if current_url != url:
            metadata["redirected"] = True

        await context.close()
        await browser.close()

    metadata["har"] = str(har_path)
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    print(f"  HAR:        {har_path}")
    print(f"  Metadata:   {meta_path}")
    print(f"\n  Outcome:    {metadata['outcome']}")
    print(f"  HTML size:  {html_len:,} chars")
    print(f"  Page title: {title}")

    if metadata.get("redirected"):
        print(f"  Redirected: {current_url}")


def main():
    parser = argparse.ArgumentParser(
        description="Capture screenshot + HAR on scraping failure"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL to capture (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_MS,
        help=f"Page load timeout in ms (default: {TIMEOUT_MS})",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run with visible browser window",
    )
    args = parser.parse_args()

    asyncio.run(capture(args.url, args.timeout, args.headed))


if __name__ == "__main__":
    main()
