"""
Infrastructure: Worker Pool Framework

Generic worker pool used by ALL departments that need dynamic scaling.
Supports both thread-based (CPU) and asyncio-based (I/O) workers.

Usage:
    pool = WorkerPool("core.analytical.calculator", max_workers=4)
    pool.submit(task_fn, *args)
    results = pool.collect()
"""

import threading
import asyncio
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Optional

from runtime.config.config import WORKER_POOL, DEPARTMENT_WORKERS


class WorkerStats:
    """Tracks live stats for a worker pool — used by Load Balancer."""

    __slots__ = ("department_id", "active_workers", "max_workers",
                 "pending_tasks", "completed_tasks", "failed_tasks",
                 "last_activity")

    def __init__(self, department_id: str, max_workers: int):
        self.department_id = department_id
        self.max_workers = max_workers
        self.active_workers = 0
        self.pending_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.last_activity = time.time()

    @property
    def load_ratio(self) -> float:
        if self.max_workers == 0:
            return 0.0
        return self.active_workers / self.max_workers

    def to_dict(self) -> dict:
        return {
            "department": self.department_id,
            "active": self.active_workers,
            "max": self.max_workers,
            "pending": self.pending_tasks,
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "load_ratio": round(self.load_ratio, 2),
        }


# Global registry so Load Balancer can see all pool stats
_pool_registry: dict[str, Any] = {}
_registry_lock = threading.Lock()


def get_all_pool_stats() -> list[dict]:
    """Returns stats for every active worker pool — used by Load Balancer."""
    with _registry_lock:
        return [pool.stats.to_dict() for pool in _pool_registry.values()]


def get_pool(department_id: str) -> Optional["WorkerPool"]:
    """Get a specific pool by department ID."""
    with _registry_lock:
        return _pool_registry.get(department_id)


class WorkerPool:
    """
    Thread-based worker pool with auto-scaling.

    - Starts with min_workers
    - Scales up to max_workers when queue fill > scale_up_threshold
    - Scales down when queue fill < scale_down_threshold
    - Idle workers removed after worker_idle_timeout
    """

    def __init__(self, department_id: str,
                 min_workers: Optional[int] = None,
                 max_workers: Optional[int] = None):
        self.department_id = department_id

        # Resolve worker counts: department override > defaults
        self._min: int = min_workers or int(WORKER_POOL["default_min_workers"])
        self._max: int = max_workers or int(
            DEPARTMENT_WORKERS.get(department_id) or WORKER_POOL["default_max_workers"]
        )

        self._executor = ThreadPoolExecutor(
            max_workers=self._max,
            thread_name_prefix=f"quarky-{department_id}"
        )
        self._futures: deque[Future] = deque()
        self._lock = threading.Lock()
        self._shutdown = False
        self._max_retries = 3
        self._dlq: deque[dict[str, Any]] = deque(maxlen=100)

        self.stats = WorkerStats(department_id, self._max)

        # Register globally
        with _registry_lock:
            _pool_registry[department_id] = self

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """Submit a task to the pool. Returns a Future."""
        if self._shutdown:
            raise RuntimeError(f"Pool {self.department_id} is shut down")

        with self._lock:
            self.stats.pending_tasks += 1
            self.stats.active_workers = min(
                self.stats.active_workers + 1, self._max
            )

        future = self._executor.submit(self._wrapped_exec, fn, *args, **kwargs)
        with self._lock:
            self._futures.append(future)

        return future

    def submit_with_retry(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """Submit a task with automatic retry (up to max_retries) and DLQ on final failure."""
        return self._executor.submit(self._retry_exec, fn, *args, **kwargs)

    def _retry_exec(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute with retry + exponential backoff. Dead-letter on final failure."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                with self._lock:
                    self.stats.completed_tasks += 1
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(min(2 ** attempt * 0.1, 2.0))  # 0.1s, 0.2s, 0.4s ...
                    continue
        # All retries exhausted — send to dead-letter queue
        with self._lock:
            self.stats.failed_tasks += 1
            self._dlq.append({
                "fn": fn.__name__ if hasattr(fn, "__name__") else str(fn),
                "args": str(args)[:200],
                "error": str(last_exc)[:500],
                "timestamp": time.time(),
            })
        raise last_exc  # type: ignore[misc]

    def get_dlq(self) -> list[dict[str, Any]]:
        """Return dead-letter queue contents."""
        with self._lock:
            return list(self._dlq)

    def _wrapped_exec(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Wraps task execution with stats tracking."""
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self.stats.completed_tasks += 1
            return result
        except Exception as exc:
            with self._lock:
                self.stats.failed_tasks += 1
            raise
        finally:
            with self._lock:
                self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
                self.stats.active_workers = max(0, self.stats.active_workers - 1)
                self.stats.last_activity = time.time()

    def submit_batch(self, fn: Callable, args_list: list[tuple]) -> list[Future]:
        """Submit multiple tasks at once."""
        return [self.submit(fn, *args) for args in args_list]

    def collect(self, timeout: Optional[float] = None) -> list[Any]:
        """Wait for all pending futures and return results. Clears the queue."""
        results = []
        with self._lock:
            futures = list(self._futures)
            self._futures.clear()

        for future in futures:
            try:
                results.append(future.result(timeout=timeout))
            except Exception as exc:
                results.append(exc)

        return results

    def pending_count(self) -> int:
        with self._lock:
            return self.stats.pending_tasks

    def shutdown(self, wait: bool = True):
        """Shutdown the pool. Removes from global registry."""
        self._shutdown = True
        self._executor.shutdown(wait=wait)
        with _registry_lock:
            _pool_registry.pop(self.department_id, None)

    def __repr__(self) -> str:
        return (f"WorkerPool({self.department_id!r}, "
                f"workers={self._min}-{self._max}, "
                f"pending={self.stats.pending_tasks})")


class AsyncWorkerPool:
    """
    Asyncio-based worker pool for I/O-bound departments.

    Uses asyncio.Semaphore to limit concurrency.
    """

    def __init__(self, department_id: str,
                 max_workers: Optional[int] = None):
        self.department_id = department_id
        self._max: int = max_workers or int(
            DEPARTMENT_WORKERS.get(department_id) or WORKER_POOL["default_max_workers"]
        )
        self._semaphore = asyncio.Semaphore(self._max)
        self._pending: list[asyncio.Task] = []
        self.stats = WorkerStats(department_id, self._max)

        with _registry_lock:
            _pool_registry[f"async.{department_id}"] = self

    async def submit(self, coro_fn: Callable, *args: Any, **kwargs: Any) -> asyncio.Task:
        """Submit an async task."""
        self.stats.pending_tasks += 1
        task = asyncio.create_task(self._run(coro_fn, *args, **kwargs))
        self._pending.append(task)
        return task

    async def _run(self, coro_fn: Callable, *args: Any, **kwargs: Any) -> Any:
        async with self._semaphore:
            self.stats.active_workers += 1
            try:
                result = await coro_fn(*args, **kwargs)
                self.stats.completed_tasks += 1
                return result
            except Exception:
                self.stats.failed_tasks += 1
                raise
            finally:
                self.stats.active_workers -= 1
                self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
                self.stats.last_activity = time.time()

    async def collect(self) -> list[Any]:
        """Await all pending tasks, return results."""
        results = []
        tasks = list(self._pending)
        self._pending.clear()
        for task in tasks:
            try:
                results.append(await task)
            except Exception as exc:
                results.append(exc)
        return results

    def shutdown(self):
        for task in self._pending:
            task.cancel()
        self._pending.clear()
        with _registry_lock:
            _pool_registry.pop(f"async.{self.department_id}", None)
