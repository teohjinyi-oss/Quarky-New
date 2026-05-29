"""
Web: Search Engine

Privacy-respecting web search via DuckDuckGo.
Falls back to a "search unavailable" message if the package isn't installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.config.config import CONFIG


@dataclass
class SearchResult:
    """A single web search result."""
    title: str
    snippet: str
    url: str
    relevance: float = 0.5


@dataclass
class SearchResponse:
    """Full search response."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    error: str = ""
    source: str = "duckduckgo"


class WebSearch:
    """DuckDuckGo-backed web search."""

    def __init__(self):
        self._available = False
        try:
            from duckduckgo_search import DDGS  # type: ignore[import-untyped]
            self._available = True
        except ImportError:
            pass

    @property
    def is_available(self) -> bool:
        return self._available

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """Perform a web search."""
        if not self._available:
            return SearchResponse(
                query=query,
                error="Web search not available (install duckduckgo-search)",
            )

        try:
            from duckduckgo_search import DDGS  # type: ignore[import-untyped]
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))

            results = [
                SearchResult(
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    url=r.get("href", ""),
                )
                for r in raw
            ]
            return SearchResponse(query=query, results=results)

        except Exception as e:
            return SearchResponse(query=query, error=str(e))

    def quick_answer(self, query: str) -> str:
        """Get a quick text answer for a query."""
        resp = self.search(query, max_results=3)
        if resp.error:
            return f"I couldn't search the web: {resp.error}"
        if not resp.results:
            return "I didn't find any results for that."

        # Return best snippet
        return resp.results[0].snippet
