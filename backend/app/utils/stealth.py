"""Playwright stealth configuration for anti-detection."""

from playwright.async_api import Browser, BrowserContext, BrowserType

MODERN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

STEALTH_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security",
]

# Proxy-based webdriver evasion from playwright_stealth (910★)
# Survives Object.getOwnPropertyDescriptor() checks unlike
# simple `get: () => false` overrides.
_WEBDRIVER_EVASION_JS = """\
if (navigator.webdriver) {
  Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {
    set: undefined,
    enumerable: true,
    configurable: true,
    get: new Proxy(
      Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(navigator), 'webdriver'
      ).get,
      { apply: (target, thisArg, args) => {
          Reflect.apply(target, thisArg, args);
          return false;
        }
      }
    )
  });
}
"""

_CHROME_RUNTIME_JS = """\
if (!window.chrome) {
  Object.defineProperty(window, 'chrome', {
    writable: true,
    enumerable: true,
    configurable: false,
    value: {}
  });
}
if (!window.chrome.runtime) {
  window.chrome.runtime = {
    id: undefined,
    connect: null,
    sendMessage: null
  };
}
"""

STEALTH_INIT_SCRIPT = _WEBDRIVER_EVASION_JS + _CHROME_RUNTIME_JS


async def launch_stealth_browser(
    browser_type: BrowserType,
    *,
    headless: bool = True,
    extra_args: list[str] | None = None,
) -> Browser:
    args = list(STEALTH_LAUNCH_ARGS)
    if extra_args:
        args.extend(extra_args)
    return await browser_type.launch(headless=headless, args=args)


async def apply_stealth(context: BrowserContext) -> None:
    await context.add_init_script(script=STEALTH_INIT_SCRIPT)
