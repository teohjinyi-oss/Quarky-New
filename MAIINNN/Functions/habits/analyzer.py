"""
Habits: Analyzer

Analyses habit data to find patterns in user behaviour —
most-used actions, peak hours, action frequencies, streaks.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from MAIINNN.Functions.habits.tracker import HabitTracker, HabitEvent


@dataclass
class HabitInsight:
    """A single insight derived from habit data."""
    kind: str           # "frequency", "peak_hour", "streak", "top_action"
    description: str
    data: dict[str, Any] = field(default_factory=dict)


class HabitAnalyzer:
    """Derives patterns from recorded habit events."""

    def __init__(self, tracker: HabitTracker):
        self._tracker = tracker

    # ── analysis methods ─────────────────────────────────────

    def top_actions(self, n: int = 5) -> list[tuple[str, int]]:
        """Most frequent actions."""
        counts = Counter(e.action for e in self._tracker.events)
        return counts.most_common(n)

    def hourly_distribution(self) -> dict[int, int]:
        """Action counts per hour of day (0-23)."""
        from datetime import datetime
        dist: dict[int, int] = {h: 0 for h in range(24)}
        for e in self._tracker.events:
            h = datetime.fromtimestamp(e.timestamp).hour
            dist[h] += 1
        return dist

    def peak_hours(self, top_n: int = 3) -> list[int]:
        """Hours with most activity."""
        dist = self.hourly_distribution()
        sorted_hours = sorted(dist, key=dist.get, reverse=True)  # type: ignore[arg-type]
        return sorted_hours[:top_n]

    def daily_counts(self, days: int = 7) -> dict[str, int]:
        """Action counts per day for the last N days."""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        result: dict[str, int] = {}
        for i in range(days):
            day = today - timedelta(days=i)
            key = day.isoformat()
            count = sum(
                1
                for e in self._tracker.events
                if datetime.fromtimestamp(e.timestamp).date() == day
            )
            result[key] = count
        return result

    def streak(self, action: str) -> int:
        """Consecutive days the user performed a given action, ending today."""
        from datetime import datetime, timedelta
        events = self._tracker.by_action(action)
        if not events:
            return 0
        dates = sorted({datetime.fromtimestamp(e.timestamp).date() for e in events})
        today = datetime.now().date()
        if dates[-1] != today:
            return 0
        streak = 1
        for i in range(len(dates) - 2, -1, -1):
            if dates[i] == dates[i + 1] - timedelta(days=1):
                streak += 1
            else:
                break
        return streak

    # ── aggregate insights ───────────────────────────────────

    def generate_insights(self) -> list[HabitInsight]:
        """Generate a set of canonical insights from current data."""
        insights: list[HabitInsight] = []

        top = self.top_actions(3)
        if top:
            insights.append(HabitInsight(
                kind="top_action",
                description=f"Most used action: {top[0][0]} ({top[0][1]} times)",
                data={"top_actions": top},
            ))

        peaks = self.peak_hours(2)
        if peaks:
            insights.append(HabitInsight(
                kind="peak_hour",
                description=f"You're most active around {peaks[0]}:00",
                data={"peak_hours": peaks},
            ))

        return insights
