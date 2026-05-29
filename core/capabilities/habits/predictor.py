"""
Habits: Predictor

Uses habit history to predict what the user might want next.
Simple frequency-and-time based predictions (no ML dependency).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.capabilities.habits.tracker import HabitTracker
from core.capabilities.habits.analyzer import HabitAnalyzer


@dataclass
class Prediction:
    """A predicted next-action suggestion."""
    action: str
    confidence: float   # 0-1
    reason: str


class HabitPredictor:
    """Predicts next user action based on patterns."""

    def __init__(self, tracker: HabitTracker):
        self._tracker = tracker
        self._analyzer = HabitAnalyzer(tracker)

    def predict_next(self, n: int = 3) -> list[Prediction]:
        """Return up to n predicted next actions."""
        predictions: list[Prediction] = []
        now = datetime.now()
        current_hour = now.hour

        # 1. Actions common at this hour
        hour_events = [
            e for e in self._tracker.events
            if datetime.fromtimestamp(e.timestamp).hour == current_hour
        ]
        if hour_events:
            from collections import Counter
            counts = Counter(e.action for e in hour_events)
            total = len(hour_events)
            for action, cnt in counts.most_common(n):
                conf = min(cnt / max(total, 1), 0.95)
                predictions.append(Prediction(
                    action=action,
                    confidence=round(conf, 2),
                    reason=f"You often do '{action}' around {current_hour}:00",
                ))

        # 2. Recency fallback — things done recently tend to repeat
        if len(predictions) < n:
            recent = self._tracker.recent(10)
            from collections import Counter
            counts = Counter(e.action for e in recent)
            seen = {p.action for p in predictions}
            for action, cnt in counts.most_common(n):
                if action not in seen:
                    predictions.append(Prediction(
                        action=action,
                        confidence=round(cnt / 10, 2),
                        reason=f"'{action}' appeared in your recent activity",
                    ))
                    if len(predictions) >= n:
                        break

        return predictions[:n]

    def should_suggest(self, action: str) -> bool:
        """Should we proactively suggest this action right now?"""
        preds = self.predict_next(5)
        return any(p.action == action and p.confidence >= 0.4 for p in preds)
