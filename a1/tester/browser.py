"""
Browser — Playwright Python wrapper for REAL browser interaction
Actually clicks, types, navigates — not just HTTP requests.
"""

import tempfile
from pathlib import Path
from typing import Optional


class Browser:
    """Real headless Chromium browser via Playwright Python API"""

    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._screenshots_dir = Path(tempfile.mkdtemp(prefix="a1_test_"))
        self._screenshot_count = 0
        self._pw = None
        self._browser = None
        self._page = None

    def launch(self):
        """Launch headless browser"""
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._page = self._browser.new_page(
            viewport={"width": self.viewport_width, "height": self.viewport_height}
        )

    def close(self):
        """Close browser"""
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = None
        self._browser = None
        self._pw = None

    @property
    def page(self):
        if not self._page:
            self.launch()
        return self._page

    def navigate(self, url: str, wait_until: str = "networkidle"):
        """Navigate to URL and wait for page load"""
        self.page.goto(url, wait_until=wait_until, timeout=15000)

    def screenshot(self, path: Optional[Path] = None, full_page: bool = False) -> Path:
        """Take screenshot of current page"""
        self._screenshot_count += 1
        if path is None:
            path = self._screenshots_dir / f"step_{self._screenshot_count:03d}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        return path

    def click(self, selector: str, timeout: int = 5000):
        """Click an element by CSS selector"""
        self.page.click(selector, timeout=timeout)

    def fill(self, selector: str, text: str, timeout: int = 5000):
        """Fill text into an input field"""
        self.page.fill(selector, text, timeout=timeout)

    def type_text(self, selector: str, text: str, delay: int = 50):
        """Type text character by character (more realistic)"""
        self.page.type(selector, text, delay=delay)

    def press(self, selector: str, key: str):
        """Press a key (Enter, Tab, etc.)"""
        self.page.press(selector, key)

    def submit_form(self, selector: str, data: dict):
        """Fill and submit a form"""
        for field, value in data.items():
            self.page.fill(f'{selector} [name="{field}"]', value)
        self.page.click(f'{selector} button[type="submit"]')

    def get_text(self, selector: str) -> str:
        """Get text content of an element"""
        return self.page.text_content(selector) or ""

    def get_inner_html(self, selector: str) -> str:
        """Get inner HTML of an element"""
        return self.page.inner_html(selector)

    def is_visible(self, selector: str, timeout: int = 3000) -> bool:
        """Check if element is visible"""
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for(self, selector: str, timeout: int = 5000):
        """Wait for element to appear"""
        self.page.wait_for_selector(selector, timeout=timeout)

    def get_url(self) -> str:
        """Get current page URL"""
        return self.page.url

    def get_title(self) -> str:
        """Get page title"""
        return self.page.title()

    def evaluate(self, js: str):
        """Execute JavaScript on page"""
        return self.page.evaluate(js)

    def get_all_text(self) -> str:
        """Get all visible text on page"""
        return self.page.inner_text("body")

    @property
    def screenshots_dir(self) -> Path:
        return self._screenshots_dir

    @property
    def screenshot_count(self) -> int:
        return self._screenshot_count
