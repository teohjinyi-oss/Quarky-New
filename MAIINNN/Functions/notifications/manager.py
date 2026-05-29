"""
Notifications: Manager

Central notification manager that de-duplicates, prioritises,
and dispatches notifications via the GUI protocol or toast.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from MAIINNN.Functions.notifications.toast import ToastNotifier


@dataclass
class Notification:
    """A pending notification."""
    id: str
    title: str
    message: str
    priority: int = 0          # higher = more important
    source: str = ""           # "monitor", "email", "calendar", "habit", etc.
    timestamp: float = field(default_factory=time.time)
    delivered: bool = False


class NotificationManager:
    """Collects, deduplicates, and dispatches notifications."""

    def __init__(self):
        self._toast = ToastNotifier()
        self._queue: list[Notification] = []
        self._history: list[Notification] = []
        self._max_history = 100
        self._gui_callback: Callable[[Notification], None] | None = None
        self._counter = 0

    def set_gui_callback(self, cb: Callable[[Notification], None]):
        """Register a callback that sends notifications to the JavaFX GUI."""
        self._gui_callback = cb

    # ── enqueue ──────────────────────────────────────────────

    def notify(
        self,
        title: str,
        message: str,
        priority: int = 0,
        source: str = "",
    ) -> Notification:
        """Add a notification to the queue."""
        self._counter += 1
        n = Notification(
            id=f"n_{self._counter}",
            title=title,
            message=message,
            priority=priority,
            source=source,
        )
        self._queue.append(n)
        return n

    # ── dispatch ─────────────────────────────────────────────

    def flush(self):
        """Deliver all queued notifications, highest priority first."""
        self._queue.sort(key=lambda n: -n.priority)
        for n in self._queue:
            self._deliver(n)
        self._queue.clear()

    def _deliver(self, n: Notification):
        if self._gui_callback:
            self._gui_callback(n)
        else:
            self._toast.show(n.title, n.message)
        n.delivered = True
        self._history.append(n)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    # ── queries ──────────────────────────────────────────────

    @property
    def pending(self) -> list[Notification]:
        return list(self._queue)

    @property
    def history(self) -> list[Notification]:
        return list(self._history)

    def pending_count(self) -> int:
        return len(self._queue)
