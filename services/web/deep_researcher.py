"""
Web: Adaptive-Depth Researcher

Provides iterative web research with 3 depth levels:
  Level 1 (Quick)    — 2 DuckDuckGo results, extract best sentence
  Level 2 (Expanded) — 5 results + scrape top page, summarize
  Level 3 (Deep)     — reformulate query into 3 variants, combine + summarize

Depth is chosen automatically based on query complexity.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchResult:
    """Aggregated research output."""
    answer: str
    facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    depth_used: int = 1
    query: str = ""


class AdaptiveResearcher:
    """
    Multi-depth web researcher.
    Depth selection is automatic based on query complexity.
    """

    def __init__(self):
        self._search = None
        self._scraper = None
        self._summarizer = None
        self._init_components()

    def _init_components(self):
        try:
            from services.web.search import WebSearch
            self._search = WebSearch()
        except Exception:
            pass
        try:
            from services.web.scraper import WebScraper
            self._scraper = WebScraper()
        except Exception:
            pass
        try:
            from services.web.summarizer import TextSummarizer
            self._summarizer = TextSummarizer()
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._search is not None and self._search.is_available

    def research(
        self,
        query: str,
        timeout: float = 8.0,
        max_depth: int = 3,
    ) -> ResearchResult:
        """
        Research a query with automatic depth selection.
        Returns the best answer found within the timeout.
        """
        if not self.is_available:
            return ResearchResult(answer="", query=query)

        depth = min(max_depth, self._choose_depth(query))
        result = ResearchResult(query=query, depth_used=depth)

        container: list[ResearchResult] = [result]

        def _do_research():
            r = container[0]
            if depth >= 1:
                self._level_1(query, r)
            if depth >= 2 and not r.answer:
                self._level_2(query, r)
            if depth >= 3 and not r.answer:
                self._level_3(query, r)

        t = threading.Thread(target=_do_research, daemon=True)
        t.start()
        t.join(timeout=timeout)

        return container[0]

    def _choose_depth(self, query: str) -> int:
        """Pick research depth based on query complexity."""
        words = query.split()
        word_count = len(words)

        # Simple factual questions → quick
        if word_count <= 5 and "?" in query:
            return 1
        # Medium-length informational questions → expanded
        if word_count <= 12:
            return 2
        # Complex / multi-part questions → deep
        return 3

    def _level_1(self, query: str, result: ResearchResult):
        """Quick: 2 results, extract best sentence."""
        resp = self._search.search(query, max_results=2)
        if resp.error or not resp.results:
            return
        for r in resp.results:
            if r.snippet and len(r.snippet) > 20:
                result.facts.append(r.snippet)
                result.sources.append(r.url)
        if result.facts:
            result.answer = result.facts[0]

    def _level_2(self, query: str, result: ResearchResult):
        """Expanded: 5 results + scrape top page."""
        resp = self._search.search(query, max_results=5)
        if resp.error or not resp.results:
            return
        for r in resp.results:
            if r.snippet and len(r.snippet) > 20:
                result.facts.append(r.snippet)
                result.sources.append(r.url)

        # Scrape top result for deeper content
        if self._scraper and self._scraper.is_available and resp.results:
            top_url = resp.results[0].url
            if top_url:
                page = self._scraper.scrape(top_url, max_chars=3000)
                if page.text and self._summarizer:
                    summary = self._summarizer.summarize(page.text, query, max_sentences=2)
                    if summary.summary:
                        result.answer = summary.summary
                        return

        if result.facts:
            result.answer = result.facts[0]

    def _level_3(self, query: str, result: ResearchResult):
        """Deep: reformulate into 3 query variants, combine results."""
        variants = self._reformulate(query)
        all_snippets: list[str] = []

        for variant in variants:
            resp = self._search.search(variant, max_results=3)
            if resp.error or not resp.results:
                continue
            for r in resp.results:
                if r.snippet and len(r.snippet) > 20:
                    all_snippets.append(r.snippet)
                    result.sources.append(r.url)

        if not all_snippets:
            return

        # Deduplicate by rough similarity
        unique: list[str] = []
        for s in all_snippets:
            if not any(self._rough_overlap(s, u) > 0.7 for u in unique):
                unique.append(s)
        result.facts.extend(unique[:5])

        # Summarize if we have enough content
        if self._summarizer and len(unique) >= 2:
            combined = " ".join(unique[:5])
            summary = self._summarizer.summarize(combined, query, max_sentences=3)
            if summary.summary:
                result.answer = summary.summary
                return

        if unique:
            result.answer = unique[0]

    def _reformulate(self, query: str) -> list[str]:
        """Generate query variants for deeper research."""
        base = query.rstrip("?").strip()
        variants = [query]
        # Add "what is" variant
        if not base.lower().startswith(("what", "who", "how", "why", "when", "where")):
            variants.append(f"what is {base}")
        # Add "explain" variant
        variants.append(f"explain {base}")
        return variants[:3]

    @staticmethod
    def _rough_overlap(a: str, b: str) -> float:
        """Quick word-overlap ratio between two strings."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / max(len(words_a), len(words_b))
