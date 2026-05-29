"""
Infrastructure: Load Balancer

Monitors workload across ALL system departments and provides
load information for transport decisions and worker scaling.

Runs periodic checks and exposes stats that other infrastructure
components can query.
"""

import time
import threading
from typing import Optional

from AppStudio.Infrastructure.worker_pool import get_all_pool_stats
from AppStudio.Infrastructure.transport.async_queue import queue_stats
from AppStudio.Infrastructure.logger import InfraLogger

_logger = InfraLogger()


class SystemLoad:
    """Snapshot of a system's current load."""
    __slots__ = ("system_id", "worker_load", "queue_depth",
                 "timestamp", "status")

    def __init__(self, system_id: str, worker_load: float = 0.0,
                 queue_depth: int = 0):
        self.system_id = system_id
        self.worker_load = worker_load    # 0.0 to 1.0
        self.queue_depth = queue_depth
        self.timestamp = time.time()

        if worker_load > 0.9:
            self.status = "OVERLOADED"
        elif worker_load > 0.7:
            self.status = "HIGH"
        elif worker_load > 0.4:
            self.status = "MODERATE"
        else:
            self.status = "LOW"

    def to_dict(self) -> dict:
        return {
            "system": self.system_id,
            "worker_load": round(self.worker_load, 2),
            "queue_depth": self.queue_depth,
            "status": self.status,
        }


class LoadBalancer:
    """
    Singleton that tracks load across all systems.

    Used by:
    - Transport Manager: to avoid sending to overloaded systems
    - Worker Pools: to decide when to scale up/down
    - Dashboard: to show system health
    """

    _instance: Optional["LoadBalancer"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LoadBalancer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._snapshots: dict[str, SystemLoad] = {}
        self._snap_lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def refresh(self):
        """Take a fresh snapshot of all system loads."""
        # Aggregate worker pool stats by system
        pool_stats = get_all_pool_stats()
        system_loads: dict[str, list[dict]] = {}

        for ps in pool_stats:
            dept = ps["department"]
            system = dept.split(".")[0]
            if system not in system_loads:
                system_loads[system] = []
            system_loads[system].append(ps)

        # Get queue depths
        q_stats = queue_stats()

        with self._snap_lock:
            for system_id, dept_stats in system_loads.items():
                # Average load across departments
                if dept_stats:
                    avg_load = sum(d["load_ratio"] for d in dept_stats) / len(dept_stats)
                else:
                    avg_load = 0.0

                q_depth = q_stats.get(system_id, 0)

                self._snapshots[system_id] = SystemLoad(
                    system_id, avg_load, q_depth
                )

    def get_load(self, system_id: str) -> Optional[SystemLoad]:
        """Get load snapshot for a system."""
        with self._snap_lock:
            return self._snapshots.get(system_id)

    def get_all_loads(self) -> list[dict]:
        """Get all system loads."""
        with self._snap_lock:
            return [s.to_dict() for s in self._snapshots.values()]

    def is_overloaded(self, system_id: str) -> bool:
        """Check if a system is currently overloaded."""
        load = self.get_load(system_id)
        return load is not None and load.status == "OVERLOADED"

    def least_loaded_system(self, candidates: list[str]) -> Optional[str]:
        """Among candidates, return the one with lowest load."""
        with self._snap_lock:
            best = None
            best_load = float("inf")
            for sid in candidates:
                snap = self._snapshots.get(sid)
                if snap and snap.worker_load < best_load:
                    best = sid
                    best_load = snap.worker_load
            return best

    def start_monitoring(self, interval: float = 5.0):
        """Start background monitoring thread."""
        if self._running:
            return

        self._running = True

        def _monitor():
            while self._running:
                try:
                    self.refresh()
                except Exception as exc:
                    _logger.error("load_balancer", "all",
                                  message=f"refresh error: {exc}")
                time.sleep(interval)

        self._monitor_thread = threading.Thread(
            target=_monitor, daemon=True,
            name="quarky-load-balancer"
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
            self._monitor_thread = None
