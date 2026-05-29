"""
Monitor: Alerter

Monitors system metrics and generates alerts when thresholds are exceeded.
Supports 3 modes:
  - "critical"  — only fire on critical-level alerts (toast notification)
  - "periodic"  — summary every N seconds pushed to sidebar
  - "live"      — real-time updates pushed to sidebar monitor tab
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from services.monitoring.collector import SystemCollector, SystemMetrics
from runtime.config.config import CONFIG


class MonitorMode(Enum):
    CRITICAL = "critical"
    PERIODIC = "periodic"
    LIVE = "live"


@dataclass
class Alert:
    """A system alert."""
    level: str          # "warning", "critical"
    metric: str         # "cpu", "memory", "disk", "battery"
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)


class SystemAlerter:
    """Checks system metrics against thresholds and generates alerts."""

    def __init__(self):
        self._collector = SystemCollector()
        thresholds = CONFIG.get("MONITOR", {}).get("alerts", {})
        self._cpu_warn = thresholds.get("cpu_high", 90)
        self._mem_warn = thresholds.get("memory_high", 85)
        self._disk_warn = thresholds.get("disk_high", 90)
        self._battery_low = thresholds.get("battery_low", 20)
        self._recent_alerts: list[Alert] = []
        self._mode: MonitorMode = MonitorMode.CRITICAL
        self._periodic_interval: float = 300.0  # 5 minutes
        self._last_periodic: float = 0.0
        self._metrics_callback: Callable[[SystemMetrics], None] | None = None
        self._alert_callback: Callable[[Alert], None] | None = None

    @property
    def mode(self) -> MonitorMode:
        return self._mode

    def set_mode(self, mode: MonitorMode) -> None:
        self._mode = mode

    def set_metrics_callback(self, cb: Callable[[SystemMetrics], None]) -> None:
        """Callback for live-mode metric pushes."""
        self._metrics_callback = cb

    def set_alert_callback(self, cb: Callable[[Alert], None]) -> None:
        """Callback for delivering alerts (toast/GUI)."""
        self._alert_callback = cb

    def check(self) -> list[Alert]:
        """Check current metrics and return any alerts."""
        metrics = self._collector.collect()
        if metrics.error:
            return []

        alerts: list[Alert] = []

        if metrics.cpu_percent > self._cpu_warn:
            alerts.append(Alert(
                level="warning",
                metric="cpu",
                message=f"CPU usage is high: {metrics.cpu_percent}%",
                value=metrics.cpu_percent,
                threshold=self._cpu_warn,
            ))

        if metrics.memory_percent > self._mem_warn:
            alerts.append(Alert(
                level="warning",
                metric="memory",
                message=f"Memory usage is high: {metrics.memory_percent}% ({metrics.memory_used_gb} GB)",
                value=metrics.memory_percent,
                threshold=self._mem_warn,
            ))

        if metrics.disk_percent > self._disk_warn:
            alerts.append(Alert(
                level="warning",
                metric="disk",
                message=f"Disk usage is high: {metrics.disk_percent}%",
                value=metrics.disk_percent,
                threshold=self._disk_warn,
            ))

        if 0 <= metrics.battery_percent < self._battery_low and not metrics.battery_plugged:
            alerts.append(Alert(
                level="critical",
                metric="battery",
                message=f"Battery low: {metrics.battery_percent}%",
                value=metrics.battery_percent,
                threshold=self._battery_low,
            ))

        self._recent_alerts.extend(alerts)
        # Cap history
        self._recent_alerts = self._recent_alerts[-50:]

        # Mode-based dispatch
        if self._mode == MonitorMode.LIVE and self._metrics_callback:
            self._metrics_callback(metrics)

        if self._mode == MonitorMode.PERIODIC:
            now = time.time()
            if now - self._last_periodic >= self._periodic_interval:
                self._last_periodic = now
                if self._metrics_callback:
                    self._metrics_callback(metrics)

        # Always dispatch critical alerts, or all alerts in non-critical modes
        for alert in alerts:
            if self._alert_callback:
                if self._mode == MonitorMode.CRITICAL and alert.level != "critical":
                    continue
                self._alert_callback(alert)

        return alerts

    @property
    def recent_alerts(self) -> list[Alert]:
        return list(self._recent_alerts)
