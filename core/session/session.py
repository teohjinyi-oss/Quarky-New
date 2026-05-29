"""
Quarky_Ai — Session Manager

Tracks conversation turns, provides history, replay, search, duplicate detection.
Auto-saves each turn to temporary memory for persistence.
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationTurn:
    """A single conversation exchange."""
    turn_number: int
    user_text: str
    response: str
    source: str                 # analytical, creative, merged, fallback, error
    timestamp: float = 0.0
    time_str: str = ""
    action_performed: str = ""  # e.g. "Opened Chrome"
    confidence: float = 0.0


class Session:
    """Manages a single conversation session."""

    def __init__(self) -> None:
        self.turns: list[ConversationTurn] = []
        self.start_time: float = time.time()
        self.turn_count: int = 0
        self.topics: list[str] = []

    def add_turn(self, user_text: str, response: str, source: str,
                 confidence: float = 0.0,
                 action_performed: str = "") -> ConversationTurn:
        """Record a new conversation turn."""
        self.turn_count += 1
        turn = ConversationTurn(
            turn_number=self.turn_count,
            user_text=user_text,
            response=response,
            source=source,
            timestamp=time.time(),
            time_str=time.strftime("%H:%M:%S"),
            action_performed=action_performed,
            confidence=confidence,
        )
        self.turns.append(turn)

        # Auto-save to temporary memory
        self._save_to_temp(turn)

        return turn

    def _save_to_temp(self, turn: ConversationTurn) -> None:
        """Save turn to temporary memory for session persistence."""
        try:
            from core.memory.manager import store_temporary
            content = f"Q: {turn.user_text}\nA: {turn.response}"
            store_temporary(content, source="session")
        except Exception:
            pass  # Memory not critical for session tracking

    def get_history(self, count: int = 20,
                    search: str = "",
                    filter_source: str = "",
                    filter_date: str = "") -> list[ConversationTurn]:
        """
        Get conversation history with optional filters.
        search: keyword to filter by
        filter_source: "analytical", "creative", etc.
        filter_date: "HH:MM" format for time-based filter
        """
        results = list(self.turns)

        if search:
            search_lower = search.lower()
            results = [t for t in results
                       if search_lower in t.user_text.lower()
                       or search_lower in t.response.lower()]

        if filter_source:
            results = [t for t in results if t.source == filter_source]

        if filter_date:
            results = [t for t in results if filter_date in t.time_str]

        return results[-count:]

    def check_duplicate(self, text: str) -> ConversationTurn | None:
        """
        Check if the exact same question was asked before.
        Returns the previous turn if found, None otherwise.
        """
        text_lower = text.lower().strip()
        for turn in reversed(self.turns):
            if turn.user_text.lower().strip() == text_lower:
                return turn
        return None

    def format_replay(self, count: int = 0) -> str:
        """Format the session as a readable replay."""
        turns = self.turns if count == 0 else self.turns[-count:]
        if not turns:
            return "No conversation history."

        lines = [f"Session Replay ({len(turns)} turns):"]
        lines.append("─" * 40)

        for turn in turns:
            lines.append(f"[{turn.time_str}] You: {turn.user_text}")
            lines.append(f"[{turn.time_str}] Quarky: {turn.response}")
            if turn.action_performed:
                lines.append(f"  → Action: {turn.action_performed}")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        sources: dict[str, int] = {}
        actions = 0
        for turn in self.turns:
            sources[turn.source] = sources.get(turn.source, 0) + 1
            if turn.action_performed:
                actions += 1

        return {
            "turn_count": self.turn_count,
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "uptime_seconds": round(elapsed),
            "actions_performed": actions,
            "response_sources": sources,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.localtime(self.start_time)),
        }

    def get_recent_context(self, count: int = 5) -> list[dict[str, str]]:
        """Get recent turns as context for the brain (memory-driven context window)."""
        recent = self.turns[-count:] if self.turns else []
        return [
            {"user": t.user_text, "response": t.response}
            for t in recent
        ]


# Global session instance
_current_session: Session | None = None


def get_session() -> Session:
    """Get or create the current session."""
    global _current_session
    if _current_session is None:
        _current_session = Session()
    return _current_session


def new_session() -> Session:
    """Start a fresh session."""
    global _current_session
    _current_session = Session()
    return _current_session


def end_session() -> dict[str, Any]:
    """End the current session and return final stats."""
    session = get_session()
    stats = session.get_stats()
    return stats
