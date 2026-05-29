"""
Infrastructure Transport: Manager

The central orchestrator that auto-selects transport mode per message.

Decision logic:
- Urgent + small + single target → DIRECT CALL (fastest)
- Large payload → ASYNC QUEUE + packing
- Multiple targets → EVENT BUS (broadcast)
- Default → ASYNC QUEUE

The transport manager NEVER sends to all systems — it picks the minimal
path based on the message characteristics.
"""

import time
from typing import Any, Optional
from enum import Enum

from AppStudio.Infrastructure.logger import InfraLogger
from AppStudio.Infrastructure import packer, unpacker as unpacker_mod
from AppStudio.Infrastructure.transport import direct_call, async_queue, event_bus
from AppStudio.Config import TRANSPORT

_logger = InfraLogger()


class TransportMode(Enum):
    DIRECT = "DIRECT"
    ASYNC = "ASYNC"
    EVENT_BUS = "EVENT_BUS"


class TransportDecision:
    """Records why a particular mode was chosen — for debugging."""
    __slots__ = ("mode", "reason", "needs_packing")

    def __init__(self, mode: TransportMode, reason: str,
                 needs_packing: bool = False):
        self.mode = mode
        self.reason = reason
        self.needs_packing = needs_packing

    def __repr__(self):
        return f"TransportDecision({self.mode.value}, packing={self.needs_packing}, reason={self.reason!r})"


def decide_mode(payload: Any, target_count: int = 1,
                urgent: bool = False,
                payload_size: Optional[int] = None) -> TransportDecision:
    """
    Decide which transport mode is optimal for this message.

    Args:
        payload: the data being sent
        target_count: how many systems receive this message
        urgent: if True, prefer fastest path
        payload_size: pre-computed size (optimization), or None to compute
    """
    # Compute size if not given
    if payload_size is None:
        needs_pack = packer.needs_packing(payload)
        if isinstance(payload, str):
            payload_size = len(payload)
        else:
            import json
            try:
                payload_size = len(json.dumps(payload, default=str))
            except (TypeError, ValueError):
                payload_size = len(str(payload))
    else:
        needs_pack = payload_size > TRANSPORT["direct_call_max_payload"]

    # Rule 1: Multiple targets → Event Bus
    if target_count > 1:
        return TransportDecision(
            TransportMode.EVENT_BUS,
            f"multiple targets ({target_count})",
            needs_packing=needs_pack
        )

    # Rule 2: Urgent + small + direct handler available → Direct Call
    if urgent and not needs_pack:
        return TransportDecision(
            TransportMode.DIRECT,
            "urgent + small payload",
            needs_packing=False
        )

    # Rule 3: Small payload + direct handler available → Direct Call
    if not needs_pack and payload_size <= TRANSPORT["direct_call_max_payload"]:
        return TransportDecision(
            TransportMode.DIRECT,
            f"small payload ({payload_size}B)",
            needs_packing=False
        )

    # Rule 4: Large payload → Async + packing
    if needs_pack:
        return TransportDecision(
            TransportMode.ASYNC,
            f"large payload ({payload_size}B, needs packing)",
            needs_packing=True
        )

    # Default: Async queue
    return TransportDecision(
        TransportMode.ASYNC,
        "default async path",
        needs_packing=False
    )


def send(source: str, target: str, payload: Any,
         urgent: bool = False) -> Any:
    """
    Send a message from source to target using the optimal transport mode.
    Synchronous — returns the result (for DIRECT) or True/None (for ASYNC/EVENT).

    This is the primary API that the Gateway calls.
    """
    decision = decide_mode(payload, target_count=1, urgent=urgent)

    _logger.debug(source, target, mode=decision.mode.value,
                  message=f"transport decision: {decision.reason}")

    # Pack if needed
    if decision.needs_packing:
        chunks = packer.pack(payload)
        _logger.debug(source, target, mode=decision.mode.value,
                      message=f"packed into {len(chunks)} chunks")
    else:
        chunks = None

    start = time.perf_counter()

    if decision.mode == TransportMode.DIRECT:
        result = direct_call.send(source, target, payload)
        elapsed = (time.perf_counter() - start) * 1000
        _logger.info(source, target, mode="DIRECT",
                     duration_ms=elapsed, message="delivered")
        return result

    elif decision.mode == TransportMode.ASYNC:
        # For sync context, we use the queue in a fire-and-forget style
        # The actual async enqueue is handled via the gateway's event loop
        import asyncio
        data = chunks if chunks else payload

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in async context — schedule directly
            asyncio.create_task(async_queue.enqueue(source, target, data))
        else:
            # Not in async context — run in new loop
            asyncio.run(async_queue.enqueue(source, target, data))

        elapsed = (time.perf_counter() - start) * 1000
        _logger.info(source, target, mode="ASYNC",
                     duration_ms=elapsed, message="enqueued")
        return True

    elif decision.mode == TransportMode.EVENT_BUS:
        count = event_bus.publish(target, source, payload)
        elapsed = (time.perf_counter() - start) * 1000
        _logger.info(source, target, mode="EVENT_BUS",
                     duration_ms=elapsed,
                     message=f"published to {count} subscribers")
        return count

    return None


def broadcast(source: str, event_type: str, data: Any = None) -> int:
    """
    Broadcast an event to all subscribers of event_type.
    Always uses Event Bus mode.
    """
    return event_bus.publish(event_type, source, data)
