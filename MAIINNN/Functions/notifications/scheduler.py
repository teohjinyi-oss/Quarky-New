"""
Notifications: Scheduler

Schedules recurring or one-shot notifications (reminders, periodic checks).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from MAIINNN.Functions.notifications.manager import NotificationManager


@dataclass
class ScheduledNotification:
    """A notification scheduled for future delivery."""
    id: str
    title: str
    message: str
    fire_at: float              # epoch timestamp
    repeat_seconds: float = 0   # 0 = one-shot
    source: str = "scheduler"
    priority: int = 0
    fired: bool = False


class NotificationScheduler:
    """Runs scheduled notifications on a background timer."""

    def __init__(self, manager: NotificationManager):
        self._manager = manager
        self._items: list[ScheduledNotification] = []
        self._counter = 0
        self._running = False
        self._thread: threading.Thread | None = None

    # ── scheduling ───────────────────────────────────────────

    def schedule(
        self,
        title: str,
        message: str,
        delay_seconds: float,
        repeat_seconds: float = 0,
        priority: int = 0,
        source: str = "scheduler",
    ) -> str:
        """Schedule a notification. Returns its ID."""
        self._counter += 1
        item_id = f"sched_{self._counter}"
        self._items.append(ScheduledNotification(
            id=item_id,
            title=title,
            message=message,
            fire_at=time.time() + delay_seconds,
            repeat_seconds=repeat_seconds,
            source=source,
            priority=priority,
        ))
        return item_id

    def cancel(self, item_id: str):
        self._items = [i for i in self._items if i.id != item_id]

    @property
    def pending(self) -> list[ScheduledNotification]:
        return [i for i in self._items if not i.fired or i.repeat_seconds > 0]

    # ── tick ─────────────────────────────────────────────────

    def tick(self):
        """Check for due notifications and fire them. Call periodically."""
        now = time.time()
        for item in self._items:
            if item.fire_at <= now and not item.fired:
                self._manager.notify(
                    title=item.title,
                    message=item.message,
                    priority=item.priority,
                    source=item.source,
                )
                if item.repeat_seconds > 0:
                    item.fire_at = now + item.repeat_seconds
                else:
                    item.fired = True
        # purge one-shots that have fired
        self._items = [i for i in self._items if not i.fired or i.repeat_seconds > 0]

    # ── background loop ──────────────────────────────────────

    def start(self, interval: float = 1.0):
        """Start a background thread that calls tick() every `interval` seconds."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self, interval: float):
        while self._running:
            self.tick()
            time.sleep(interval)
