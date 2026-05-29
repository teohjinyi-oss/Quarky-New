"""
Quarky_Ai — Session v2

Enhanced session that integrates with MemoryManagerV2, token tracking,
habits, and the GUI protocol. Wraps the v1 Session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.session.session import Session, ConversationTurn


class SessionV2:
    """
    Enhanced session manager.

    Delegates core turn tracking to v1 Session, adds:
    - Memory v2 integration (token-scored storage)
    - Habit event recording per turn
    - GUI metadata per turn
    """

    def __init__(self):
        self._session = Session()
        self._memory: Any = None  # set lazily
        self._habits: Any = None  # set lazily

    # ── dependency injection ─────────────────────────────────

    def set_memory(self, memory: Any):
        """Inject MemoryManagerV2."""
        self._memory = memory

    def set_habits(self, tracker: Any):
        """Inject HabitTracker."""
        self._habits = tracker

    # ── turn management ──────────────────────────────────────

    def add_turn(
        self,
        user_text: str,
        response: str,
        source: str,
        confidence: float = 0.0,
        action_performed: str = "",
        specificity_tier: str = "",
    ) -> ConversationTurn:
        """Record a turn, store in memory, and log habit event."""
        turn = self._session.add_turn(
            user_text=user_text,
            response=response,
            source=source,
            confidence=confidence,
            action_performed=action_performed,
        )

        # Store in v2 memory
        if self._memory:
            try:
                self._memory.store(
                    f"Q: {user_text}\nA: {response}",
                    source="session",
                    topic="conversation",
                )
            except Exception:
                pass

        # Log habit
        if self._habits:
            try:
                self._habits.record(
                    action="chat",
                    category="conversation",
                    source=source,
                    tier=specificity_tier,
                )
            except Exception:
                pass

        return turn

    # ── delegate to v1 ───────────────────────────────────────

    def get_history(self, count: int = 20, **kwargs: Any) -> list[ConversationTurn]:
        return self._session.get_history(count=count, **kwargs)

    def check_duplicate(self, text: str) -> ConversationTurn | None:
        return self._session.check_duplicate(text)

    def format_replay(self, count: int = 0) -> str:
        return self._session.format_replay(count)

    def get_stats(self) -> dict[str, Any]:
        return self._session.get_stats()

    def get_recent_context(self, count: int = 5) -> list[dict[str, str]]:
        return self._session.get_recent_context(count)

    @property
    def turn_count(self) -> int:
        return self._session.turn_count

    @property
    def turns(self) -> list[ConversationTurn]:
        return self._session.turns


# ─── module-level convenience ────────────────────────────────

_session_v2: SessionV2 | None = None


def get_session_v2() -> SessionV2:
    global _session_v2
    if _session_v2 is None:
        _session_v2 = SessionV2()
    return _session_v2
