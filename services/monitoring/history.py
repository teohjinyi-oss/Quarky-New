"""
Monitor: History

Stores metrics history for trend analysis and reporting.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from services.monitoring.collector import SystemCollector, SystemMetrics
from runtime.config.config import CONFIG


@dataclass
class MetricSnapshot:
    """A single timestamped metrics snapshot."""
    timestamp: float
    cpu: float
    memory: float
    disk: float
    battery: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk": self.disk,
            "battery": self.battery,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MetricSnapshot:
        return cls(
            timestamp=d["timestamp"],
            cpu=d["cpu"],
            memory=d["memory"],
            disk=d["disk"],
            battery=d["battery"],
        )


class MetricsHistory:
    """Stores and queries historical system metrics."""

    def __init__(self, max_entries: int = 1000):
        mon_cfg = CONFIG.get("MONITOR", {})
        self._path = os.path.join(
            mon_cfg.get("dir", "data/monitor"),
            "history.json"
        )
        self._max = max_entries
        self._snapshots: list[MetricSnapshot] = []
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                self._snapshots = [MetricSnapshot.from_dict(d) for d in items]
            except (json.JSONDecodeError, KeyError):
                self._snapshots = []

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self._snapshots], f)

    # ── recording ────────────────────────────────────────────

    def record(self, metrics: SystemMetrics):
        """Record a metrics snapshot."""
        snap = MetricSnapshot(
            timestamp=time.time(),
            cpu=metrics.cpu_percent,
            memory=metrics.memory_percent,
            disk=metrics.disk_percent,
            battery=metrics.battery_percent,
        )
        self._snapshots.append(snap)
        if len(self._snapshots) > self._max:
            self._snapshots = self._snapshots[-self._max:]
        self._save()

    # ── queries ──────────────────────────────────────────────

    def last(self, n: int = 10) -> list[MetricSnapshot]:
        return self._snapshots[-n:]

    def since(self, seconds_ago: float) -> list[MetricSnapshot]:
        cutoff = time.time() - seconds_ago
        return [s for s in self._snapshots if s.timestamp >= cutoff]

    def average(self, metric: str, last_n: int = 10) -> float:
        """Average of a metric over last N snapshots."""
        recent = self._snapshots[-last_n:]
        if not recent:
            return 0.0
        values = [getattr(s, metric, 0.0) for s in recent]
        return sum(values) / len(values)

    def trend(self, metric: str, last_n: int = 10) -> str:
        """Simple trend: 'rising', 'falling', or 'stable'."""
        recent = self._snapshots[-last_n:]
        if len(recent) < 2:
            return "stable"
        first_half = recent[: len(recent) // 2]
        second_half = recent[len(recent) // 2:]
        avg_first = sum(getattr(s, metric, 0.0) for s in first_half) / len(first_half)
        avg_second = sum(getattr(s, metric, 0.0) for s in second_half) / len(second_half)
        diff = avg_second - avg_first
        if diff > 5:
            return "rising"
        elif diff < -5:
            return "falling"
        return "stable"

    @property
    def count(self) -> int:
        return len(self._snapshots)
