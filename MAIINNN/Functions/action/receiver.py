"""
Action System: Receiver — Public API

The single entry point for executing actions.
  execute(ActionRequest, confirmed) → ActionResult

Flow:
  1. Safety gate check
  2. Registry handler lookup
  3. Live progress output
  4. Execute handler
  5. Log to action_logger
  6. Return ActionResult
"""

import time
from typing import Any

from MAIINNN.Decision.action_resolver import ActionRequest
from MAIINNN.Functions.result_reporter import ActionResult, UndoInfo
from MAIINNN.Functions.action.safety import check_safety, is_system_path, SafetyVerdict
from MAIINNN.Functions.action.registry import get_handler, ensure_builtins
from MAIINNN.Functions.action import action_logger


def execute(action_request: ActionRequest,
            confirmed: bool = False) -> ActionResult:
    """
    Execute an action request through the safety → registry → handler pipeline.

    Args:
        action_request: The prepared ActionRequest from the Decision Engine
        confirmed: True if user has already confirmed a HIGH/CRITICAL action

    Returns:
        ActionResult with success status, message, and optional undo info
    """
    ensure_builtins()

    action_type = action_request.action_type
    target = action_request.target
    risk_level = action_request.risk_level
    start = time.perf_counter()

    # 1. Block system paths for file operations
    if action_type == "file_op" and target and is_system_path(target):
        return ActionResult(
            success=False,
            message=f"Blocked: cannot operate on system path '{target}'.",
        )

    # 2. Safety gate
    if not confirmed:
        verdict: SafetyVerdict = check_safety(action_type, target, risk_level)
        if not verdict.allowed:
            return ActionResult(
                success=False,
                message=verdict.reason,
                data={"needs_confirmation": verdict.needs_user_input,
                      "permission_type": verdict.permission_type},
            )

    # 3. Look up handler
    handler = get_handler(action_type)
    if handler is None:
        return ActionResult(
            success=False,
            message=f"No handler registered for action type '{action_type}'.",
        )

    # 4. Execute the handler
    try:
        result: ActionResult = handler(action_request)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        action_logger.log_action(
            action_type=action_type,
            target=target,
            risk_level=risk_level,
            success=False,
            message=f"Handler error: {e}",
            duration_ms=elapsed,
        )
        return ActionResult(
            success=False,
            message=f"Action failed: {e}",
            duration_ms=elapsed,
        )

    # 5. Calculate duration and log
    elapsed = (time.perf_counter() - start) * 1000
    result.duration_ms = elapsed

    action_logger.log_action(
        action_type=action_type,
        target=target,
        risk_level=risk_level,
        success=result.success,
        message=result.message,
        duration_ms=elapsed,
        undo_available=result.undo_info is not None,
    )

    return result


def execute_batch(requests: list[ActionRequest],
                  confirmed_indices: set[int] | None = None) -> list[ActionResult]:
    """
    Execute multiple action requests in order.
    Auto-executes LOW/MEDIUM risk; skips HIGH/CRITICAL unless in confirmed_indices.

    Args:
        requests: List of ActionRequests to execute
        confirmed_indices: Set of 0-based indices that the user confirmed

    Returns:
        List of ActionResults, one per request
    """
    if confirmed_indices is None:
        confirmed_indices = set()

    results: list[ActionResult] = []
    for i, req in enumerate(requests):
        is_confirmed = i in confirmed_indices
        auto_safe = req.risk_level in ("LOW", "MEDIUM")

        if auto_safe or is_confirmed:
            result = execute(req, confirmed=True)
        else:
            result = ActionResult(
                success=False,
                message=f"Skipped: {req.action_type} → {req.target} (requires confirmation)",
                data={"needs_confirmation": True, "index": i},
            )
        results.append(result)

    return results
