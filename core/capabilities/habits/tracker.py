"""
Habits: Tracker

Records timestamped user actions to build a behavioural profile.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from runtime.config.config import CONFIG


@dataclass
class HabitEvent:
    """A single user-action event."""
    action: str          # e.g. "ask_question", "open_app", "check_email"
    category: str = ""   # grouping bucket
    timestamp: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category,
            "timestamp": self.timestamp,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> HabitEvent:
        return cls(
            action=d["action"],
            category=d.get("category", ""),
            timestamp=d.get("timestamp", 0.0),
            meta=d.get("meta", {}),
        )


class HabitTracker:
    """Records and persists user habit events."""

    def __init__(self, max_events: int = 5000):
        hab_cfg = CONFIG.get("HABITS", {})
        self._path = os.path.join(
            hab_cfg.get("dir", "data/habits"),
            "events.json"
        )
        self._max = max_events
        self._events: list[HabitEvent] = []
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                self._events = [HabitEvent.from_dict(d) for d in items]
            except (json.JSONDecodeError, KeyError):
                self._events = []

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._events], f)

    # ── recording ────────────────────────────────────────────

    def record(self, action: str, category: str = "", **meta: Any):
        """Record a habit event."""
        event = HabitEvent(action=action, category=category, meta=meta)
        self._events.append(event)
        if len(self._events) > self._max:
            self._events = self._events[-self._max:]
        self._save()

    # ── queries ──────────────────────────────────────────────

    @property
    def events(self) -> list[HabitEvent]:
        return list(self._events)

    def recent(self, n: int = 20) -> list[HabitEvent]:
        return self._events[-n:]

    def by_action(self, action: str) -> list[HabitEvent]:
        return [e for e in self._events if e.action == action]

    def by_category(self, category: str) -> list[HabitEvent]:
        return [e for e in self._events if e.category == category]

    def since(self, seconds_ago: float) -> list[HabitEvent]:
        cutoff = time.time() - seconds_ago
        return [e for e in self._events if e.timestamp >= cutoff]

    @property
    def count(self) -> int:
        return len(self._events)
