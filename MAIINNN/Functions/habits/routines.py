"""
Habits: Routines

Morning/evening routine suggestions built from analysed habits.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Config import CONFIG
from MAIINNN.Functions.habits.analyzer import HabitAnalyzer
from MAIINNN.Functions.habits.tracker import HabitTracker


@dataclass
class RoutineStep:
    """A single step in a suggested routine."""
    action: str
    label: str
    order: int


@dataclass
class Routine:
    """A named routine (morning, evening, work, etc.)."""
    name: str
    steps: list[RoutineStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "steps": [
                {"action": s.action, "label": s.label, "order": s.order}
                for s in self.steps
            ],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Routine:
        steps = [
            RoutineStep(action=s["action"], label=s["label"], order=s["order"])
            for s in d.get("steps", [])
        ]
        return cls(name=d["name"], steps=steps)


class RoutineManager:
    """Manages user routines — auto-generated and custom."""

    def __init__(self, tracker: HabitTracker):
        self._tracker = tracker
        self._analyzer = HabitAnalyzer(tracker)
        hab_cfg = CONFIG.get("HABITS", {})
        self._path = os.path.join(
            hab_cfg.get("dir", "data/habits"),
            "routines.json"
        )
        self._routines: dict[str, Routine] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for d in items:
                    r = Routine.from_dict(d)
                    self._routines[r.name] = r
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._routines.values()], f)

    # ── CRUD ─────────────────────────────────────────────────

    def get(self, name: str) -> Routine | None:
        return self._routines.get(name)

    def list_routines(self) -> list[str]:
        return list(self._routines.keys())

    def save_routine(self, routine: Routine):
        self._routines[routine.name] = routine
        self._save()

    def delete_routine(self, name: str):
        self._routines.pop(name, None)
        self._save()

    # ── auto-generate ────────────────────────────────────────

    def suggest_morning(self) -> Routine:
        """Build a morning routine from 6-11 AM habits."""
        from datetime import datetime
        morning = [
            e for e in self._tracker.events
            if 6 <= datetime.fromtimestamp(e.timestamp).hour < 12
        ]
        from collections import Counter
        counts = Counter(e.action for e in morning)
        steps = [
            RoutineStep(action=act, label=act.replace("_", " ").title(), order=i)
            for i, (act, _) in enumerate(counts.most_common(5))
        ]
        return Routine(name="morning", steps=steps)

    def suggest_evening(self) -> Routine:
        """Build an evening routine from 6-11 PM habits."""
        from datetime import datetime
        evening = [
            e for e in self._tracker.events
            if 18 <= datetime.fromtimestamp(e.timestamp).hour < 24
        ]
        from collections import Counter
        counts = Counter(e.action for e in evening)
        steps = [
            RoutineStep(action=act, label=act.replace("_", " ").title(), order=i)
            for i, (act, _) in enumerate(counts.most_common(5))
        ]
        return Routine(name="evening", steps=steps)
