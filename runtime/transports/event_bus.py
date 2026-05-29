"""
Infrastructure Transport: Event Bus (Mode 3)

Pub/sub broadcast system for event-driven communication.
Systems subscribe to event types. When an event is published,
all subscribers receive it.

Used when: broadcasting state changes ("system_awake", "memory_updated",
"action_completed"), or notifying multiple systems at once.
"""

import time
import threading
from typing import Any, Callable

from runtime.config.config import TRANSPORT
from runtime.infrastructure.logger import InfraLogger

_logger = InfraLogger()

# Subscriber registry: event_type → list of (system_id, callback)
_subscribers: dict[str, list[tuple[str, Callable]]] = {}
_sub_lock = threading.Lock()

# Event history (bounded ring buffer)
_history: list[dict] = []
_history_max = 500


def subscribe(event_type: str, system_id: str, callback: Callable):
    """
    Subscribe a system to an event type.

    callback signature: callback(event_data: dict) -> None
    """
    max_subs = TRANSPORT.get("event_bus_max_subscribers", 64)

    with _sub_lock:
        if event_type not in _subscribers:
            _subscribers[event_type] = []

        subs = _subscribers[event_type]

        # Prevent duplicate subscriptions
        for sid, _ in subs:
            if sid == system_id:
                return

        if len(subs) >= max_subs:
            _logger.warning("event_bus", system_id,
                            message=f"Max subscribers reached for '{event_type}'")
            return

        subs.append((system_id, callback))

    _logger.debug("event_bus", system_id,
                  message=f"subscribed to '{event_type}'")


def unsubscribe(event_type: str, system_id: str):
    """Unsubscribe a system from an event type."""
    with _sub_lock:
        if event_type in _subscribers:
            _subscribers[event_type] = [
                (sid, cb) for sid, cb in _subscribers[event_type]
                if sid != system_id
            ]


def unsubscribe_all(system_id: str):
    """Remove a system from all event subscriptions."""
    with _sub_lock:
        for event_type in _subscribers:
            _subscribers[event_type] = [
                (sid, cb) for sid, cb in _subscribers[event_type]
                if sid != system_id
            ]


def publish(event_type: str, source: str, data: Any = None) -> int:
    """
    Publish an event to all subscribers.

    Returns the number of subscribers notified.
    Errors in individual callbacks are caught and logged (never propagated).
    """
    event = {
        "type": event_type,
        "source": source,
        "data": data,
        "timestamp": time.time(),
    }

    with _sub_lock:
        subs = list(_subscribers.get(event_type, []))

    notified = 0
    for system_id, callback in subs:
        try:
            callback(event)
            notified += 1
        except Exception as exc:
            _logger.error(source, system_id, mode="EVENT_BUS",
                          message=f"subscriber error on '{event_type}': {exc}")

    # Record in history
    _record_event(event, notified)

    if notified > 0:
        _logger.info(source, f"{notified} subscribers", mode="EVENT_BUS",
                     message=f"published '{event_type}'")

    return notified


def _record_event(event: dict, subscriber_count: int):
    """Add to bounded history."""
    global _history
    event_record = {**event, "subscribers_notified": subscriber_count}
    _history.append(event_record)
    if len(_history) > _history_max:
        _history = _history[-_history_max:]


def get_subscribers(event_type: str) -> list[str]:
    """List system IDs subscribed to an event type."""
    with _sub_lock:
        return [sid for sid, _ in _subscribers.get(event_type, [])]


def get_all_event_types() -> list[str]:
    """List all event types that have subscribers."""
    with _sub_lock:
        return list(_subscribers.keys())


def get_history(count: int = 50) -> list[dict]:
    """Get recent event history."""
    return _history[-count:]


def clear():
    """Clear all subscriptions and history."""
    global _history
    with _sub_lock:
        _subscribers.clear()
    _history = []
