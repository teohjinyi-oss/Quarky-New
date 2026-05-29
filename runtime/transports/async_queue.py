"""
Infrastructure Transport: Async Queue (Mode 2)

Asynchronous message queues for parallel multi-target delivery.
Each system gets its own input queue. Messages are enqueued and
processed by the target system at its own pace.

Used when: parallel delivery needed, or target may be busy.
"""

import asyncio
import time
import threading
from typing import Any, Optional

from runtime.config.config import TRANSPORT
from runtime.infrastructure.logger import InfraLogger

_logger = InfraLogger()

# Per-system async queues
_queues: dict[str, asyncio.Queue] = {}
_queue_lock = threading.Lock()


class Message:
    """A message in the async queue."""
    __slots__ = ("source", "target", "payload", "timestamp", "priority")

    def __init__(self, source: str, target: str, payload: Any,
                 priority: int = 0):
        self.source = source
        self.target = target
        self.payload = payload
        self.timestamp = time.time()
        self.priority = priority

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "ts": self.timestamp,
            "priority": self.priority,
        }


def get_or_create_queue(system_id: str) -> asyncio.Queue:
    """Get or create an async queue for a system."""
    with _queue_lock:
        if system_id not in _queues:
            max_size = TRANSPORT.get("async_queue_size", 256)
            _queues[system_id] = asyncio.Queue(maxsize=max_size)
        return _queues[system_id]


async def enqueue(source: str, target: str, payload: Any,
                  priority: int = 0) -> bool:
    """
    Put a message into the target system's queue.
    Returns True if enqueued, False if queue is full.
    """
    queue = get_or_create_queue(target)
    msg = Message(source, target, payload, priority)

    try:
        queue.put_nowait(msg)
        _logger.debug(source, target, mode="ASYNC_QUEUE",
                      message=f"enqueued (qsize={queue.qsize()})")
        return True
    except asyncio.QueueFull:
        _logger.warning(source, target, mode="ASYNC_QUEUE",
                        message=f"QUEUE FULL for {target}")
        return False


async def dequeue(system_id: str, timeout: float = 5.0) -> Optional[Message]:
    """
    Get next message from a system's queue.
    Returns None if timeout expires.
    """
    queue = get_or_create_queue(system_id)
    try:
        msg = await asyncio.wait_for(queue.get(), timeout=timeout)
        _logger.debug(system_id, system_id, mode="ASYNC_QUEUE",
                      message=f"dequeued from {msg.source}")
        return msg
    except asyncio.TimeoutError:
        return None


async def enqueue_multi(source: str, targets: list[str],
                        payload: Any) -> dict[str, bool]:
    """
    Enqueue the same message to multiple target systems in parallel.
    Returns {target: success} dict.
    """
    results = {}
    tasks = []
    for target in targets:
        tasks.append(enqueue(source, target, payload))

    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    for target, outcome in zip(targets, outcomes):
        results[target] = outcome is True

    _logger.info(source, ",".join(targets), mode="ASYNC_QUEUE",
                 message=f"multi-enqueue: {sum(results.values())}/{len(targets)}")
    return results


def queue_size(system_id: str) -> int:
    """Current queue size for a system."""
    with _queue_lock:
        q = _queues.get(system_id)
        return q.qsize() if q else 0


def queue_stats() -> dict[str, int]:
    """Get all queue sizes."""
    with _queue_lock:
        return {sid: q.qsize() for sid, q in _queues.items()}


def clear_queue(system_id: str):
    """Clear a system's queue."""
    with _queue_lock:
        if system_id in _queues:
            while not _queues[system_id].empty():
                try:
                    _queues[system_id].get_nowait()
                except asyncio.QueueEmpty:
                    break


def clear_all():
    """Clear all queues."""
    with _queue_lock:
        for sid in list(_queues):
            clear_queue(sid)
