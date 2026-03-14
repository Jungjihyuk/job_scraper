#!/usr/bin/env python3
"""
🔍 스크래핑 진단 스크립트 — 6단계로 실패 원인을 특정한다.

실행:
    uv run python scripts/diagnostics/diagnose_scraper.py
    uv run python scripts/diagnostics/diagnose_scraper.py --url https://www.wanted.co.kr/wd/347915
    uv run python scripts/diagnostics/diagnose_scraper.py --headed

출력:
    - 각 단계별 PASS/FAIL 판정
    - diagnostic_screenshot.png (실제 브라우저 화면)
    - 최종 진단 요약
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from job_scraper.utils.stealth import (
    MODERN_USER_AGENT,
    STEALTH_LAUNCH_ARGS,
    apply_stealth,
)


# ── 진단 대상 셀렉터 (content_scraper.py WantedSelectors 기준) ──
WANTED_SELECTORS = {
    "CONTENT_WRAPPER": "section.JobContent_descriptionWrapper__RMlfm",
    "TITLE": "h1.wds-58fmok",
    "POSITION_DETAIL": (
        "div.JobDescription_JobDescription__paragraph__wrapper__WPrKC span.wds-h4ga6o"
    ),
    "JOBDESCRIPTION": ("div.JobDescription_JobDescription__paragraph__87w8I"),
    "COMPANY_TAGS": "ul.CompanyTags_CompanyTags__list__XmzkW li",
    "DEADLINE": "span.wds-1u1yyy",
    "WORK_PLACE": (
        "div.JobWorkPlace_JobWorkPlace__map__location__6pp2d span.wds-1td1qmv"
    ),
    "EXPAND_BUTTON": "button:has(span:text('상세 정보 더 보기'))",
}

# 목록 페이지용 셀렉터
LIST_SELECTORS = {
    "POST_LIST": "li.Card_Card__aaatv",
    "JOB_POST_LINK": 'div[data-cy="job-card"] a',
}

# Anti-bot header prefixes/names that indicate active bot protection.
# Excludes normal CDN headers (x-amz-cf-*, cf-ray, cf-cache-status).
ANTI_BOT_HEADER_EXACT = {
    "cf-mitigated",
}
ANTI_BOT_HEADER_PREFIXES = [
    "x-datadome",
    "x-px",
    "x-dd-",
]
ANTI_BOT_HEADER_CONTAINS = [
    "x-akamai-bot-reason",
    "x-akamai-bot-score",
]


def _is_anti_bot_header(name: str) -> bool:
    lower = name.lower()
    if lower in ANTI_BOT_HEADER_EXACT:
        return True
    if any(lower.startswith(p) for p in ANTI_BOT_HEADER_PREFIXES):
        return True
    return lower in ANTI_BOT_HEADER_CONTAINS


DEFAULT_TEST_URL = "https://www.wanted.co.kr/wd/347915"
SCREENSHOT_DIR = Path("logs/diagnostics")


class DiagnosticResult:
    """진단 결과 누적기"""

    def __init__(self):
        self.results = []

    def add(self, step: str, passed: bool, detail: str):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((step, status, detail))
        print(f"  [{status}] {step}: {detail}")

    def summary(self):
        print("\n" + "=" * 60)
        print("📋 진단 요약")
        print("=" * 60)
        for step, status, detail in self.results:
            print(f"  {status} {step}")

        # 원인 추정
        fails = [r for r in self.results if r[1] == "❌ FAIL"]
        if not fails:
            print("\n✅ 모든 진단 통과 — 현재 시점에서는 정상 동작")
        else:
            print(f"\n❌ {len(fails)}개 항목 실패:")
            for step, _, detail in fails:
                print(f"  → {step}: {detail}")

            # 원인 추정 로직
            fail_steps = {r[0] for r in fails}
            if "Step 1: 페이지 로드" in fail_steps:
                print("\n🔎 추정 원인: 네트워크 차단 또는 IP 블락")
            elif "Step 2: 응답 코드" in fail_steps:
                print("\n🔎 추정 원인: Anti-bot 차단 (HTTP 에러)")
            elif "Step 3: 페이지 내용" in fail_steps:
                print("\n🔎 추정 원인: Anti-bot 차단 (CAPTCHA/Challenge 페이지)")
            elif any("Step 5" in s for s in fail_steps):
                print(
                    "\n🔎 추정 원인: 셀렉터 변경 (사이트 리뉴얼)"
                    "\n   → 원티드가 프론트엔드를 업데이트한 것으로 보입니다."
                    "\n   → check_selectors.py로 현재 유효한 셀렉터를"
                    " 확인하세요."
                )


async def diagnose(url: str, headed: bool = False, stealth: bool = False):
    result = DiagnosticResult()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    mode = "stealth" if stealth else "raw"
    print(f"🔍 스크래핑 진단 시작: {url}")
    print(f"   모드: {mode} / {'headed' if headed else 'headless'}")
    print(f"   시간: {timestamp}")
    print("-" * 60)

    async with async_playwright() as p:
        if stealth:
            browser = await p.chromium.launch(
                headless=not headed,
                args=STEALTH_LAUNCH_ARGS,
            )
            context = await browser.new_context(
                user_agent=MODERN_USER_AGENT,
            )
            await apply_stealth(context)
        else:
            browser = await p.chromium.launch(headless=not headed)
            context = await browser.new_context(
                user_agent=MODERN_USER_AGENT,
            )
        page = await context.new_page()

        # ── Step 1: 페이지 로드 ──
        print("\n📌 Step 1: 페이지 로드")
        response = None
        try:
            response = await page.goto(url, timeout=30000)
            if not response:
                result.add("Step 1: 페이지 로드", False, "응답 없음")
                await browser.close()
                result.summary()
                return
            result.add(
                "Step 1: 페이지 로드",
                True,
                f"응답 수신 완료 ({response.status})",
            )
        except Exception as e:
            result.add(
                "Step 1: 페이지 로드",
                False,
                f"goto 실패 — {e}",
            )
            await browser.close()
            result.summary()
            return

        # ── Step 2: HTTP 응답 코드 ──
        print("\n📌 Step 2: 응답 코드 확인")
        status = response.status
        if status == 200:
            result.add(
                "Step 2: 응답 코드",
                True,
                "200 OK",
            )
        elif status in (403, 503):
            result.add(
                "Step 2: 응답 코드",
                False,
                f"{status} — anti-bot 차단 가능성 높음",
            )
        elif status in (301, 302):
            result.add(
                "Step 2: 응답 코드",
                False,
                f"{status} 리다이렉트 — challenge 페이지일 수 있음",
            )
        else:
            result.add(
                "Step 2: 응답 코드",
                True,
                f"Status {status}",
            )

        # ── Step 3: 페이지 내용 검사 ──
        print("\n📌 Step 3: 페이지 내용 검사")
        html = await page.content()
        html_lower = html.lower()
        html_len = len(html)

        if any(
            kw in html_lower
            for kw in ["captcha", "challenge-form", "cf-browser-verification"]
        ):
            result.add(
                "Step 3: 페이지 내용",
                False,
                "CAPTCHA 또는 Challenge 페이지 감지",
            )
        elif html_len < 1000:
            result.add(
                "Step 3: 페이지 내용",
                False,
                f"비정상적으로 짧은 HTML ({html_len} chars) — 차단 또는 빈 페이지",
            )
        else:
            result.add(
                "Step 3: 페이지 내용",
                True,
                f"HTML 정상 ({html_len:,} chars)",
            )

        # ── Step 4: 스크린샷 캡처 ──
        print("\n📌 Step 4: 스크린샷 캡처")
        screenshot_path = SCREENSHOT_DIR / f"diagnose_{timestamp}.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
            result.add(
                "Step 4: 스크린샷",
                True,
                f"저장 완료 → {screenshot_path}",
            )
        except Exception as e:
            result.add(
                "Step 4: 스크린샷",
                False,
                f"캡처 실패 — {e}",
            )

        # ── Step 5: 셀렉터 존재 여부 ──
        print("\n📌 Step 5: 셀렉터 존재 여부")
        # 먼저 networkidle 대기
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # networkidle 타임아웃은 무시

        selector_pass = 0
        selector_fail = 0
        for name, sel in WANTED_SELECTORS.items():
            try:
                elem = await page.wait_for_selector(sel, timeout=5000)
                if elem:
                    text = (await elem.text_content() or "")[:40]
                    result.add(
                        f"Step 5: {name}",
                        True,
                        f"발견 ('{text}...')",
                    )
                    selector_pass += 1
                else:
                    result.add(
                        f"Step 5: {name}",
                        False,
                        "셀렉터 매칭 실패",
                    )
                    selector_fail += 1
            except Exception:
                result.add(
                    f"Step 5: {name}",
                    False,
                    "타임아웃 — 셀렉터 변경 의심",
                )
                selector_fail += 1

        print(f"\n   셀렉터 결과: {selector_pass} 통과 / {selector_fail} 실패")

        # ── Step 6: 자동화 탐지 신호 ──
        print("\n📌 Step 6: 자동화 탐지 신호")

        # navigator.webdriver
        webdriver_val = await page.evaluate("navigator.webdriver")
        result.add(
            "Step 6: navigator.webdriver",
            not webdriver_val,
            f"webdriver={webdriver_val}"
            + (" (노출됨!)" if webdriver_val else " (정상)"),
        )

        if response:
            headers = response.headers
            detected_headers = {
                k: v for k, v in headers.items() if _is_anti_bot_header(k)
            }
            if detected_headers:
                result.add(
                    "Step 6: Anti-bot 헤더",
                    False,
                    f"감지됨 — {detected_headers}",
                )
            else:
                result.add(
                    "Step 6: Anti-bot 헤더",
                    True,
                    "anti-bot 헤더 없음",
                )

        await browser.close()

    # 최종 요약
    result.summary()


def main():
    parser = argparse.ArgumentParser(description="스크래핑 실패 원인 진단 스크립트")
    parser.add_argument(
        "--url",
        default=DEFAULT_TEST_URL,
        help=f"진단할 URL (기본값: {DEFAULT_TEST_URL})",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="브라우저 창을 열어서 실행 (디버깅용)",
    )
    parser.add_argument(
        "--stealth",
        action="store_true",
        help="stealth.py 적용 상태로 진단 (수정 후 검증용)",
    )
    args = parser.parse_args()

    asyncio.run(diagnose(args.url, args.headed, args.stealth))


if __name__ == "__main__":
    main()
