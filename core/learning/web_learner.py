"""
Learning System: Web Learner

Allows Quarky to learn from the web when it doesn't know an answer.

Flow:
  1. User asks something Quarky doesn't know
  2. Brain returns low confidence
  3. Web learner searches, extracts key facts
  4. Facts stored as INFERRED tokens in memory
  5. Next time the question is asked, memory provides the answer

Uses DuckDuckGo for privacy-respecting search.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebFact:
    """A fact extracted from web search."""
    text: str
    source_url: str = ""
    confidence: float = 0.5
    query: str = ""
    timestamp: float = field(default_factory=time.time)


class WebLearner:
    """
    Searches the web and extracts facts for storage in memory.
    """

    def __init__(self):
        self._search_available = False
        self._ddgs_module: str | None = None
        self._memory_manager = None
        self._check_search()

    def set_memory(self, memory_manager: Any) -> None:
        self._memory_manager = memory_manager

    def _check_search(self) -> None:
        """Check if web search is available."""
        try:
            from ddgs import DDGS  # type: ignore[import-untyped]
            self._search_available = True
            self._ddgs_module = "ddgs"
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # type: ignore[import-untyped]
                self._search_available = True
                self._ddgs_module = "duckduckgo_search"
            except ImportError:
                self._search_available = False
                self._ddgs_module = None

    @property
    def is_available(self) -> bool:
        return self._search_available

    def search_and_learn(
        self,
        query: str,
        max_results: int = 3,
        timeout_seconds: float = 4.0,
    ) -> list[WebFact]:
        """
        Search the web for a query and extract key facts.
        Returns list of WebFact objects.
        """
        if not self._search_available:
            return []

        facts: list[WebFact] = []
        results: list[dict[str, Any]] = []

        def _run_search() -> None:
            try:
                if self._ddgs_module == "ddgs":
                    from ddgs import DDGS  # type: ignore[import-untyped]
                else:
                    from duckduckgo_search import DDGS  # type: ignore[import-untyped]
                with DDGS() as ddgs:
                    found = list(ddgs.text(query, max_results=max_results))
                results.extend(found)
            except Exception:
                # Keep fallback behavior graceful on network/API errors.
                pass

        search_thread = threading.Thread(target=_run_search, daemon=True)
        search_thread.start()
        search_thread.join(timeout=max(0.5, timeout_seconds))
        if search_thread.is_alive():
            # Timed out: return quickly so app never appears frozen.
            return []

        for r in results:
            body = r.get("body", "")
            url = r.get("href", "")
            if body and len(body) > 20:
                # Extract the most informative sentence
                fact_text = self._extract_best_sentence(body, query)
                if fact_text:
                    fact = WebFact(
                        text=fact_text,
                        source_url=url,
                        confidence=0.5,
                        query=query,
                    )
                    facts.append(fact)

        # Store facts in memory if available
        if facts and self._memory_manager:
            self._store_facts(facts, query)

        return facts

    def _extract_best_sentence(self, text: str, query: str) -> str:
        """Extract the most relevant sentence from a text block."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return text[:200]

        # Score each sentence by keyword overlap with query
        query_words = set(query.lower().split())
        best = ""
        best_score = 0

        for sentence in sentences:
            if len(sentence) < 15 or len(sentence) > 300:
                continue
            words = set(sentence.lower().split())
            overlap = len(query_words & words)
            if overlap > best_score:
                best_score = overlap
                best = sentence

        return best or sentences[0][:200]

    def _store_facts(self, facts: list[WebFact], query: str) -> None:
        """Store learned facts in memory as INFERRED tokens."""
        try:
            from core.intelligence.token import Token, ConfirmationTier

            if self._memory_manager is None:
                return
            for fact in facts[:3]:  # store at most 3 per query
                token = Token(
                    text=fact.text,
                    source=f"web:{fact.source_url[:100]}",
                    topic=query[:50],
                )
                token.confirmation = ConfirmationTier.INFERRED
                token.importance = fact.confidence
                self._memory_manager.store(token)
        except (ImportError, Exception):
            pass
