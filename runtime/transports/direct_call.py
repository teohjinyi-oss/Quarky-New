"""
Infrastructure Transport: Direct Call (Mode 1)

Synchronous fast-path for urgent/simple messages.
Fastest mode — direct function invocation, no queuing.
Used when: payload is small, single target, high urgency.
"""

import time
from typing import Any, Callable, Optional

from runtime.infrastructure.logger import InfraLogger

_logger = InfraLogger()

# Registry of system handlers — populated at startup by each system
_handlers: dict[str, Callable] = {}


def register_handler(system_id: str, handler: Callable):
    """Register a system's direct-call handler."""
    _handlers[system_id] = handler
    _logger.debug("infrastructure.direct_call", system_id,
                  message=f"Handler registered: {system_id}")


def unregister_handler(system_id: str):
    _handlers.pop(system_id, None)


def send(source: str, target: str, payload: Any) -> Any:
    """
    Send a message directly to a target system's handler.
    Synchronous — blocks until handler returns.

    Returns the handler's response.

    Raises:
        KeyError: if target has no registered handler
        Exception: whatever the handler raises
    """
    handler = _handlers.get(target)
    if handler is None:
        _logger.error(source, target,
                      message=f"No handler registered for '{target}'")
        raise KeyError(f"No direct-call handler for system '{target}'")

    start = time.perf_counter()
    try:
        result = handler(payload)
        elapsed = (time.perf_counter() - start) * 1000
        _logger.info(source, target, mode="DIRECT",
                     message="delivered", duration_ms=elapsed)
        return result
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        _logger.error(source, target, mode="DIRECT",
                      message=f"handler error: {exc}", duration_ms=elapsed)
        raise


def is_available(target: str) -> bool:
    """Check if a target system has a direct-call handler registered."""
    return target in _handlers


def get_registered_systems() -> list[str]:
    return list(_handlers.keys())
