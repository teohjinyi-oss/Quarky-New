"""
Infrastructure: Gateway

THE central entry point for ALL inter-system communication.
Every message between systems flows through here.

Pipeline: validate → check permissions → classify → transport

No system calls another directly — everything goes via Gateway.
"""

import time
from typing import Any, Optional
from dataclasses import dataclass, field

from AppStudio.Infrastructure.logger import InfraLogger
from AppStudio.Infrastructure.permissions import is_allowed
from AppStudio.Infrastructure.transport import manager as transport_mgr

_logger = InfraLogger()


@dataclass
class GatewayMessage:
    """Standard message format for all inter-system communication."""
    source: str
    target: str
    payload: Any
    msg_type: str = "request"       # request, response, event, command
    urgent: bool = False
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "type": self.msg_type,
            "urgent": self.urgent,
            "metadata": self.metadata,
            "ts": self.timestamp,
        }


class GatewayError(Exception):
    """Raised when a message cannot be delivered."""
    pass


class PermissionDeniedError(GatewayError):
    """Raised when source is not allowed to send to target."""
    pass


# Stats counters
_stats = {
    "messages_sent": 0,
    "messages_blocked": 0,
    "messages_failed": 0,
}


def send(source: str, target: str, payload: Any,
         msg_type: str = "request", urgent: bool = False,
         metadata: Optional[dict] = None) -> Any:
    """
    Send a message from one system to another.
    This is THE primary API for inter-system communication.

    Args:
        source: sending system ID (e.g., "core", "memory", "decision")
        target: receiving system ID
        payload: the data to deliver
        msg_type: "request", "response", "event", "command"
        urgent: if True, prefer fastest transport (direct call)
        metadata: optional metadata dict

    Returns:
        Response from the target system (for DIRECT mode)
        True (for ASYNC mode — fire and forget)
        Subscriber count (for EVENT_BUS mode)

    Raises:
        PermissionDeniedError: if source→target is not allowed
        GatewayError: on delivery failure
    """
    # Step 1: Permission check
    if not is_allowed(source, target):
        _stats["messages_blocked"] += 1
        raise PermissionDeniedError(
            f"Permission denied: {source} → {target}"
        )

    # Step 2: Build message
    msg = GatewayMessage(
        source=source,
        target=target,
        payload=payload,
        msg_type=msg_type,
        urgent=urgent,
        metadata=metadata or {},
    )

    # Step 3: Transport
    try:
        result = transport_mgr.send(
            source=source,
            target=target,
            payload=payload,
            urgent=urgent,
        )
        _stats["messages_sent"] += 1
        return result

    except Exception as exc:
        _stats["messages_failed"] += 1
        _logger.error(source, target,
                      message=f"Gateway delivery failed: {exc}")
        raise GatewayError(f"Delivery failed: {exc}") from exc


def broadcast(source: str, event_type: str, data: Any = None) -> int:
    """
    Broadcast an event to all subscribers.
    Uses Event Bus transport mode.
    """
    _stats["messages_sent"] += 1
    return transport_mgr.broadcast(source, event_type, data)


def get_stats() -> dict:
    """Get gateway message counters."""
    return dict(_stats)


def reset_stats():
    """Reset all counters."""
    for key in _stats:
        _stats[key] = 0
