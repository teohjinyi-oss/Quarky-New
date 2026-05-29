"""
Learning System: Correction Engine

When Quarky gives a wrong answer and the user corrects it:
  1. Store the correction as a high-priority USER_CONFIRMED token
  2. Link the correction to the original query in the graph
  3. Boost the corrected answer for future recall
  4. Optionally retrain the NLP classifier with the new data point

This is the core "learning from mistakes" mechanism.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.config.config import DATA_DIR


@dataclass
class Correction:
    """A recorded correction from the user."""
    original_query: str
    wrong_answer: str
    correct_answer: str
    timestamp: float = field(default_factory=time.time)
    applied: bool = False


class CorrectionEngine:
    """
    Manages corrections: stores, applies, and uses them
    to prevent the same mistake twice.
    """

    def __init__(self):
        self._corrections: list[Correction] = []
        self._store_path = Path(DATA_DIR) / "learning" / "corrections.json"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_manager = None
        self._load()

    def set_memory(self, memory_manager: Any) -> None:
        self._memory_manager = memory_manager

    def record(
        self,
        original_query: str,
        wrong_answer: str,
        correct_answer: str,
    ) -> Correction:
        """Record a new correction."""
        correction = Correction(
            original_query=original_query,
            wrong_answer=wrong_answer,
            correct_answer=correct_answer,
        )
        self._corrections.append(correction)
        self._apply(correction)
        self._save()
        return correction

    def check(self, query: str) -> str | None:
        """
        Check if we have a correction for this query.
        Uses exact match first, then falls back to fuzzy embedding similarity.
        Returns the correct answer if found, None otherwise.
        """
        query_lower = query.lower().strip()
        # 1. Exact match (fast path)
        for c in reversed(self._corrections):
            if c.original_query.lower().strip() == query_lower:
                return c.correct_answer
        # 2. Fuzzy similarity match via embeddings
        if self._corrections:
            try:
                from core.nlp.embeddings import similarity
                best_score = 0.0
                best_answer: str | None = None
                for c in reversed(self._corrections):
                    score = similarity(query_lower, c.original_query.lower().strip())
                    if score > best_score:
                        best_score = score
                        best_answer = c.correct_answer
                if best_score >= 0.85 and best_answer is not None:
                    return best_answer
            except Exception:
                pass
        return None

    def _apply(self, correction: Correction) -> None:
        """Apply the correction to memory and knowledge graph."""
        if self._memory_manager is None:
            correction.applied = False
            return

        try:
            from core.intelligence.token import Token, ConfirmationTier

            # Store corrected answer as high-priority token
            token = Token(
                text=correction.correct_answer,
                source="correction",
                topic=correction.original_query[:50],
            )
            token.confirmation = ConfirmationTier.USER_CONFIRMED
            token.importance = 0.85
            self._memory_manager.store(token)

            # Create graph edge: query → corrected_answer
            self._memory_manager.relate(
                correction.original_query[:50],
                token.id,
                "corrected_to",
            )

            correction.applied = True
        except (ImportError, Exception):
            correction.applied = False

    def _save(self) -> None:
        """Persist corrections to disk."""
        data = [
            {
                "query": c.original_query,
                "wrong": c.wrong_answer,
                "correct": c.correct_answer,
                "timestamp": c.timestamp,
                "applied": c.applied,
            }
            for c in self._corrections[-200:]
        ]
        try:
            self._store_path.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _load(self) -> None:
        """Load corrections from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for entry in data:
                self._corrections.append(Correction(
                    original_query=entry["query"],
                    wrong_answer=entry["wrong"],
                    correct_answer=entry["correct"],
                    timestamp=entry.get("timestamp", 0),
                    applied=entry.get("applied", False),
                ))
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    @property
    def count(self) -> int:
        return len(self._corrections)
