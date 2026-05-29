"""
Infrastructure: Classifier

Determines routing metadata for messages flowing through Gateway:
- Which system should handle this?
- What urgency level?
- Should it be packed?

This is used by the Gateway to enrich messages before transport.
For INPUT classification (COMMAND/QUESTION/TASK/CREATIVE), see nlp/classifier.py
"""

from typing import Any, Optional
from AppStudio.Infrastructure.packer import needs_packing


class RouteInfo:
    """Routing metadata determined by the classifier."""
    __slots__ = ("target_systems", "urgency", "needs_packing",
                 "estimated_size", "transport_hint")

    def __init__(self, target_systems: list[str],
                 urgency: str = "normal",
                 needs_packing: bool = False,
                 estimated_size: int = 0,
                 transport_hint: Optional[str] = None):
        self.target_systems = target_systems
        self.urgency = urgency          # "low", "normal", "high", "critical"
        self.needs_packing = needs_packing
        self.estimated_size = estimated_size
        self.transport_hint = transport_hint  # "direct", "async", "event_bus", or None

    def to_dict(self) -> dict:
        return {
            "targets": self.target_systems,
            "urgency": self.urgency,
            "packing": self.needs_packing,
            "size": self.estimated_size,
            "hint": self.transport_hint,
        }


def classify_message(source: str, target: str, payload: Any,
                     msg_type: str = "request") -> RouteInfo:
    """
    Classify a message for routing.

    Determines:
    - Target validation
    - Urgency based on message type
    - Whether payload needs packing
    - Transport hint for the manager
    """
    # Urgency mapping
    urgency_map = {
        "command": "high",
        "event": "normal",
        "request": "normal",
        "response": "high",
    }
    urgency = urgency_map.get(msg_type, "normal")

    # Check packing needs
    packing_needed = needs_packing(payload)

    # Estimate size
    if isinstance(payload, str):
        est_size = len(payload)
    elif isinstance(payload, (dict, list)):
        import json
        try:
            est_size = len(json.dumps(payload, default=str))
        except (TypeError, ValueError):
            est_size = 0
    else:
        est_size = len(str(payload))

    # Transport hint
    if urgency == "high" and not packing_needed:
        hint = "direct"
    elif packing_needed:
        hint = "async"
    else:
        hint = None  # let transport manager decide

    return RouteInfo(
        target_systems=[target],
        urgency=urgency,
        needs_packing=packing_needed,
        estimated_size=est_size,
        transport_hint=hint,
    )
