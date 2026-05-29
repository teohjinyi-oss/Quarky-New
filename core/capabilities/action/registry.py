"""
Action System: Handler Registry

Maps action_type strings → handler functions.
Extensible via register() for future plugin support.
"""

from typing import Callable, Any

# Type alias for action handlers
# handler(action_type, target, parameters) → ActionResult
ActionHandler = Callable[..., Any]

# The registry: action_type → handler function
_registry: dict[str, ActionHandler] = {}


def register(action_type: str, handler: ActionHandler) -> None:
    """Register a handler function for an action type."""
    _registry[action_type] = handler


def get_handler(action_type: str) -> ActionHandler | None:
    """Look up the handler for an action type."""
    return _registry.get(action_type)


def list_registered() -> list[str]:
    """Return list of all registered action types."""
    return list(_registry.keys())


def is_registered(action_type: str) -> bool:
    """Check if an action type has a handler."""
    return action_type in _registry


def unregister(action_type: str) -> bool:
    """Remove a handler. Returns True if it existed."""
    return _registry.pop(action_type, None) is not None


def _register_builtins() -> None:
    """
    Register all built-in action handlers.
    Called once during system init. Each executor module exposes
    a top-level function that matches the ActionHandler signature.
    """
    # Lazy imports to avoid circular deps and allow partial installs
    try:
        from core.capabilities.action.app_launcher import launch
        register("app_launch", launch)
    except ImportError:
        pass

    try:
        from core.capabilities.action.system_control import execute as sys_execute
        register("system_control", sys_execute)
    except ImportError:
        pass

    try:
        from core.capabilities.action.file_manager import execute as file_execute
        register("file_op", file_execute)
    except ImportError:
        pass

    try:
        from core.capabilities.action.clipboard import execute as clip_execute
        register("clipboard", clip_execute)
    except ImportError:
        pass

    try:
        from core.capabilities.action.code_runner import execute as code_execute
        register("code_run", code_execute)
    except ImportError:
        pass


# Track whether builtins have been registered
_builtins_loaded = False


def ensure_builtins() -> None:
    """Register builtins once on first use."""
    global _builtins_loaded
    if not _builtins_loaded:
        _register_builtins()
        _builtins_loaded = True
