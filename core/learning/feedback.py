"""
Learning System: Feedback Processor

Handles explicit user feedback on Quarky's responses:
  - "that's wrong" / "no, it's X" → correction
  - thumbs up/down → confidence adjustment
  - "remember that" → explicit memory store

Feedback updates token values:
  - Positive feedback → boost importance + confirm token
  - Negative feedback → reduce importance + mark unverified
  - Correction → store corrected version as USER_CONFIRMED
"""

from __future__ import annotations

import re
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.config.config import DATA_DIR


@dataclass
class FeedbackEntry:
    """A single feedback event."""
    feedback_type: str      # "positive", "negative", "correction", "remember"
    original_query: str
    original_response: str
    correction: str = ""     # for corrections: what the right answer is
    timestamp: float = field(default_factory=time.time)
    applied: bool = False


# Patterns that indicate feedback
_POSITIVE_PATTERNS = [
    re.compile(r"\b(?:correct|right|yes|exactly|perfect|good|thanks|thank you)\b", re.I),
    re.compile(r"\bthumb(?:s)?\s*up\b", re.I),
    re.compile(r"\bthat(?:'s| is) (?:correct|right|good)\b", re.I),
]

_NEGATIVE_PATTERNS = [
    re.compile(r"\b(?:wrong|incorrect|no|nope|not right)\b", re.I),
    re.compile(r"\bthumb(?:s)?\s*down\b", re.I),
    re.compile(r"\bthat(?:'s| is) (?:wrong|incorrect|not right)\b", re.I),
]

_CORRECTION_PATTERNS = [
    re.compile(r"(?:no|actually|wrong)[,.]?\s*(?:it(?:'s| is)|the answer is)\s+(.+)", re.I),
    re.compile(r"(?:correct(?:ion)?|fix):\s*(.+)", re.I),
    re.compile(r"it(?:'s| is) actually\s+(.+)", re.I),
]

_REMEMBER_PATTERNS = [
    re.compile(r"\bremember (?:that |this:?\s*)(.+)", re.I),
    re.compile(r"\bnote:?\s+(.+)", re.I),
    re.compile(r"\bsave (?:that |this:?\s*)(.+)", re.I),
]


class FeedbackProcessor:
    """
    Processes user feedback and applies it to the system.
    """

    def __init__(self):
        self._history: list[FeedbackEntry] = []
        self._log_path = Path(DATA_DIR) / "learning" / "feedback_log.json"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_manager = None
        self._token_tracker = None

    def set_memory(self, memory_manager: Any) -> None:
        self._memory_manager = memory_manager

    def set_tracker(self, tracker: Any) -> None:
        self._token_tracker = tracker

    def detect_feedback(self, text: str) -> FeedbackEntry | None:
        """
        Detect if user text is feedback on a previous response.
        Returns FeedbackEntry or None if not feedback.
        """
        # Check corrections first (most specific)
        for pattern in _CORRECTION_PATTERNS:
            m = pattern.search(text)
            if m:
                return FeedbackEntry(
                    feedback_type="correction",
                    original_query="",  # filled by caller
                    original_response="",
                    correction=m.group(1).strip(),
                )

        # Check remember requests
        for pattern in _REMEMBER_PATTERNS:
            m = pattern.search(text)
            if m:
                return FeedbackEntry(
                    feedback_type="remember",
                    original_query=text,
                    original_response="",
                    correction=m.group(1).strip(),
                )

        # Check negative (before positive — "no" should catch)
        for pattern in _NEGATIVE_PATTERNS:
            if pattern.search(text):
                return FeedbackEntry(
                    feedback_type="negative",
                    original_query="",
                    original_response="",
                )

        # Check positive
        for pattern in _POSITIVE_PATTERNS:
            if pattern.search(text):
                return FeedbackEntry(
                    feedback_type="positive",
                    original_query="",
                    original_response="",
                )

        return None

    def apply_feedback(self, entry: FeedbackEntry) -> str:
        """
        Apply feedback to token system and memory.
        Returns a status message.
        """
        self._history.append(entry)

        if entry.feedback_type == "positive":
            self._boost_last_tokens()
            self._save_log()
            return "Got it, I'll remember that was helpful."

        elif entry.feedback_type == "negative":
            self._penalize_last_tokens()
            self._save_log()
            return "Thanks for the correction. I'll adjust."

        elif entry.feedback_type == "correction":
            self._store_correction(entry)
            self._save_log()
            return f"Noted. I'll remember: {entry.correction}"

        elif entry.feedback_type == "remember":
            self._store_memory(entry)
            self._save_log()
            return f"Saved to memory: {entry.correction}"

        return ""

    def _boost_last_tokens(self) -> None:
        """Boost importance of recent response tokens."""
        if self._token_tracker is None:
            return
        recent = self._token_tracker.top_tokens(3)
        for token in recent:
            token.confirm()
            token.boost_importance(0.1)

    def _penalize_last_tokens(self) -> None:
        """Reduce importance of recent response tokens."""
        if self._token_tracker is None:
            return
        recent = self._token_tracker.top_tokens(3)
        for token in recent:
            token.decay_importance(0.15)

    def _store_correction(self, entry: FeedbackEntry) -> None:
        """Store the corrected answer in memory as USER_CONFIRMED."""
        if self._memory_manager is None:
            return
        try:
            from core.intelligence.token import Token, ConfirmationTier
            token = Token(
                text=entry.correction,
                source="user_correction",
                topic="correction",
            )
            token.confirmation = ConfirmationTier.USER_CONFIRMED
            token.importance = 0.8
            self._memory_manager.store(token)
        except ImportError:
            pass

    def _store_memory(self, entry: FeedbackEntry) -> None:
        """Store an explicit memory request."""
        if self._memory_manager is None:
            return
        try:
            from core.intelligence.token import Token, ConfirmationTier
            token = Token(
                text=entry.correction,
                source="user_memory",
                topic="user_note",
            )
            token.confirmation = ConfirmationTier.USER_CONFIRMED
            token.importance = 0.9
            self._memory_manager.store(token)
        except ImportError:
            pass

    def _save_log(self) -> None:
        """Persist feedback history."""
        entries = [
            {
                "type": e.feedback_type,
                "query": e.original_query,
                "response": e.original_response,
                "correction": e.correction,
                "timestamp": e.timestamp,
            }
            for e in self._history[-100:]  # keep last 100
        ]
        try:
            self._log_path.write_text(json.dumps(entries, indent=2))
        except OSError:
            pass

    @property
    def history(self) -> list[FeedbackEntry]:
        return list(self._history)
