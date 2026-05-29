"""
Web: Scraper

Extracts clean text content from web pages.
Uses BeautifulSoup with fallback to basic regex extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass
class ScrapedPage:
    """Scraped page content."""
    url: str
    title: str = ""
    text: str = ""
    error: str = ""


class WebScraper:
    """Extracts readable text from web pages."""

    def __init__(self):
        self._bs4_available = False
        self._requests_available = False
        try:
            import bs4  # type: ignore[import-untyped]
            self._bs4_available = True
        except ImportError:
            pass
        try:
            import requests  # type: ignore[import-untyped]
            self._requests_available = True
        except ImportError:
            pass

    @property
    def is_available(self) -> bool:
        return self._bs4_available and self._requests_available

    def scrape(self, url: str, max_chars: int = 5000) -> ScrapedPage:
        """Scrape a URL and return clean text."""
        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ScrapedPage(url=url, error="Only http/https URLs are supported")

        if not self.is_available:
            return ScrapedPage(url=url, error="Scraping not available (install requests + beautifulsoup4)")

        try:
            import requests  # type: ignore[import-untyped]
            from bs4 import BeautifulSoup  # type: ignore[import-untyped]

            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Quarky-AI/2.0 (Personal Assistant)"
            })
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string if soup.title else ""
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text[:max_chars]

            return ScrapedPage(url=url, title=title or "", text=text)

        except Exception as e:
            return ScrapedPage(url=url, error=str(e))
