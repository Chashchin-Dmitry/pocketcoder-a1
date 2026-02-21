"""
Browser — Playwright wrapper for headless testing
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class Browser:
    """Headless Chromium browser via Playwright CLI"""

    def __init__(self, viewport: str = "1280,720"):
        self.viewport = viewport
        self._screenshots_dir = Path(tempfile.mkdtemp(prefix="a1_test_"))
        self._screenshot_count = 0

    def screenshot(self, url: str, path: Optional[Path] = None) -> Path:
        """Take a screenshot of a URL, return path to PNG"""
        self._screenshot_count += 1
        if path is None:
            path = self._screenshots_dir / f"step_{self._screenshot_count:03d}.png"

        result = subprocess.run(
            ["npx", "playwright@latest", "screenshot",
             "--viewport-size", self.viewport, url, str(path)],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Screenshot failed: {result.stderr}")

        return path

    def pdf(self, url: str, path: Optional[Path] = None) -> Path:
        """Save page as PDF"""
        self._screenshot_count += 1
        if path is None:
            path = self._screenshots_dir / f"step_{self._screenshot_count:03d}.pdf"

        result = subprocess.run(
            ["npx", "playwright@latest", "pdf", url, str(path)],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"PDF failed: {result.stderr}")

        return path

    @property
    def screenshots_dir(self) -> Path:
        return self._screenshots_dir

    @property
    def screenshot_count(self) -> int:
        return self._screenshot_count
