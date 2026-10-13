"""Optional Playwright renderer for pages that need JavaScript."""

from common import BlockedError, check_block_status, looks_blocked


class BrowserFetcher:
    def __init__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError(
                "JavaScript mode needs Playwright. Install it with "
                "'pip install playwright' and 'playwright install chromium'."
            ) from error

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

    def get(self, url, wait_selector=None):
        page = self.browser.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else 200
            check_block_status(status, url)
            if status >= 400:
                raise RuntimeError(f"Page returned HTTP {status}: {url}")

            if wait_selector:
                page.locator(wait_selector).wait_for(state="visible", timeout=15000)

            html = page.content()
            if looks_blocked(html):
                raise BlockedError(f"A challenge page was returned: {url}")
            return html
        finally:
            page.close()

    def close(self):
        self.browser.close()
        self.playwright.stop()
