"""
Monitor: System Collector

Collects system metrics: CPU, RAM, disk, battery, top processes.
Uses psutil with graceful fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SystemMetrics:
    """Snapshot of system health."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    battery_percent: float = -1.0  # -1 = no battery
    battery_plugged: bool = False
    top_processes: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


class SystemCollector:
    """Collects system metrics via psutil."""

    def __init__(self):
        self._available = False
        try:
            import psutil  # type: ignore[import-untyped]
            self._available = True
        except ImportError:
            pass

    @property
    def is_available(self) -> bool:
        return self._available

    def collect(self) -> SystemMetrics:
        """Collect current system metrics."""
        if not self._available:
            return SystemMetrics(error="psutil not installed")

        import psutil  # type: ignore[import-untyped]

        metrics = SystemMetrics()

        try:
            metrics.cpu_percent = psutil.cpu_percent(interval=0.5)

            mem = psutil.virtual_memory()
            metrics.memory_percent = mem.percent
            metrics.memory_used_gb = round(mem.used / (1024 ** 3), 2)
            metrics.memory_total_gb = round(mem.total / (1024 ** 3), 2)

            disk = psutil.disk_usage("/")
            metrics.disk_percent = disk.percent
            metrics.disk_free_gb = round(disk.free / (1024 ** 3), 2)

            battery = psutil.sensors_battery()
            if battery:
                metrics.battery_percent = battery.percent
                metrics.battery_plugged = battery.power_plugged or False

            # Top 5 processes by memory
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    info = p.info
                    if info["memory_percent"] and info["memory_percent"] > 0.5:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
            metrics.top_processes = procs[:5]

        except Exception as e:
            metrics.error = str(e)

        return metrics

    def summary(self) -> str:
        """Get a human-readable system summary."""
        m = self.collect()
        if m.error:
            return f"System info unavailable: {m.error}"

        parts = [
            f"CPU: {m.cpu_percent}%",
            f"RAM: {m.memory_used_gb}/{m.memory_total_gb} GB ({m.memory_percent}%)",
            f"Disk: {m.disk_free_gb} GB free ({m.disk_percent}% used)",
        ]
        if m.battery_percent >= 0:
            plug = "plugged in" if m.battery_plugged else "on battery"
            parts.append(f"Battery: {m.battery_percent}% ({plug})")

        if m.top_processes:
            top = m.top_processes[0]
            parts.append(f"Top process: {top.get('name', '?')} ({top.get('memory_percent', 0):.1f}% RAM)")

        return " | ".join(parts)
