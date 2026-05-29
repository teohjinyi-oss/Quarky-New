"""
Web: Summarizer

Extracts key facts from scraped web content.
Uses extractive summarization (sentence ranking by keyword relevance).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Summary:
    """A text summary."""
    original_length: int
    summary: str
    key_facts: list[str]
    source: str = ""


class TextSummarizer:
    """Extractive text summarizer using sentence scoring."""

    def summarize(
        self, text: str, query: str = "", max_sentences: int = 3
    ) -> Summary:
        """Extract the most relevant sentences from text."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return Summary(
                original_length=len(text),
                summary=text[:200],
                key_facts=[],
            )

        # Score sentences by keyword overlap with query
        query_words = set(query.lower().split()) if query else set()
        scored = []
        for s in sentences:
            words = set(s.lower().split())
            # Base score: sentence position (earlier = better)
            score = 1.0 / (1 + sentences.index(s) * 0.2)
            # Query relevance bonus
            if query_words:
                overlap = len(query_words & words)
                score += overlap * 0.3
            # Length bonus: prefer medium-length sentences
            if 30 < len(s) < 200:
                score += 0.2
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_sentences]

        # Preserve original order
        top.sort(key=lambda x: sentences.index(x[1]))

        summary_text = " ".join(s for _, s in top)
        key_facts = [s for _, s in scored[:5]]

        return Summary(
            original_length=len(text),
            summary=summary_text,
            key_facts=key_facts,
        )
