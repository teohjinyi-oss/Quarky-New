"""
Decision Engine: Action Resolver Department

If the task requires an action, prepares an ActionRequest with the
appropriate safety level from config. Does NOT execute — just packages
the request for the Action System.
Supports multi-action parsing for commands like "open chrome and play spotify".
"""

import re
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Config import ACTION
from MAIINNN.Decision.collector import DecisionContext
from MAIINNN.Decision.evaluator import EvalScores


@dataclass
class ActionRequest:
    """A prepared action request ready for the Action System."""
    action_type: str            # "app_launch", "system_control", "file_op", etc.
    command: str                # the original user text
    target: str                 # extracted target (app name, file path, etc.)
    risk_level: str             # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    parameters: dict[str, Any] = field(default_factory=dict)
    needs_confirmation: bool = False


def resolve(ctx: DecisionContext, scores: EvalScores) -> ActionRequest | None:
    """
    If an action is needed, build an ActionRequest.
    Returns None if no action is required.
    """
    if not scores.needs_action:
        return None

    action_type = scores.action_type
    target = _extract_target(ctx.user_text, action_type)
    risk_level = _get_risk_level(action_type, target, ctx.user_text)
    needs_confirm = risk_level in ("HIGH", "CRITICAL")

    return ActionRequest(
        action_type=action_type,
        command=ctx.user_text,
        target=target,
        risk_level=risk_level,
        needs_confirmation=needs_confirm,
    )


def _extract_target(text: str, action_type: str) -> str:
    """
    Extract the action target from user text.
    e.g. "open chrome" → "chrome", "delete report.pdf" → "report.pdf"
    """
    lower = text.lower().strip()

    # Action verbs to strip from the front
    verbs = [
        "open", "launch", "start", "run", "execute",
        "close", "kill", "stop",
        "create", "delete", "remove", "move", "copy", "rename",
        "set", "change", "adjust", "increase", "decrease",
        "mute", "unmute",
    ]
    for verb in verbs:
        if lower.startswith(verb + " "):
            return text[len(verb):].strip()
        if lower.startswith("please " + verb + " "):
            return text[len("please " + verb):].strip()

    # Fallback: return everything after first word
    parts = text.split(None, 1)
    return parts[1] if len(parts) > 1 else text


_BROWSER_TARGETS = {
    "chrome", "google chrome", "chromium",
    "firefox", "mozilla firefox",
    "edge", "microsoft edge",
    "brave", "opera", "safari",
    "browser", "web browser",
}


def _get_risk_level(action_type: str, target: str,
                    command: str = "") -> str:
    """Map action type + target + command to a risk level from config."""
    risk_map = ACTION["risk_levels"]

    # Direct risk lookup by action type
    type_to_risk_key = {
        "app_launch":      "open_app",
        "code_run":        "run_code",
        "system_control":  "volume",       # default for system
        "file_op":         "create_file",  # default for files
        "clipboard":       "clipboard_read",
    }

    risk_key = type_to_risk_key.get(action_type, "open_app")

    # Refine based on target AND original command
    combined = (target + " " + command).lower()

    # Browser launches always require confirmation
    if action_type == "app_launch" and target.lower().strip() in _BROWSER_TARGETS:
        return "HIGH"

    # URL opens always require confirmation (already HIGH in config, explicit here)
    if action_type in ("app_launch", "web_search") and (
        combined.startswith("http") or "www." in combined or "open_url" in combined
    ):
        return "HIGH"

    if "delete" in combined or "remove" in combined:
        risk_key = "delete_file"
    elif "shutdown" in combined:
        risk_key = "shutdown"
    elif "restart" in combined:
        risk_key = "restart"
    elif "volume" in combined or "mute" in combined:
        risk_key = "volume"
    elif "brightness" in combined:
        risk_key = "brightness"

    return risk_map.get(risk_key, "MEDIUM")


# ═══════════════════════════════════════════════════════════════
#  Multi-Action Parsing
# ═══════════════════════════════════════════════════════════════

_SPLIT_PATTERN = re.compile(
    r'\s+(?:and\s+(?:then\s+)?|then\s+|also\s+|,\s*(?:and\s+)?)',
    re.IGNORECASE,
)

# Keywords that signal an action verb at the start of a sub-command
_ACTION_VERBS = {
    "open", "launch", "start", "run", "execute", "close", "kill", "stop",
    "create", "delete", "remove", "move", "copy", "rename",
    "set", "change", "adjust", "increase", "decrease",
    "mute", "unmute", "shutdown", "restart", "lock", "sleep",
    "play", "pause", "resume", "skip",
}


def _detect_action_type_for_text(text: str) -> str:
    """Detect action type from a single sub-command text."""
    lower = text.lower()
    # Import evaluator's keyword detection logic
    from MAIINNN.Decision.evaluator import _detect_action_type
    return _detect_action_type(lower)


def resolve_multi(ctx: DecisionContext,
                  scores: EvalScores) -> list[ActionRequest]:
    """
    Parse multi-action commands and return a list of ActionRequests.
    Falls back to single action if no multi-action pattern detected.
    """
    if not scores.needs_action:
        return []

    text = ctx.user_text.strip()

    # Split on "and", "then", "also", commas
    parts = _SPLIT_PATTERN.split(text)
    parts = [p.strip() for p in parts if p.strip()]

    # Check if parts look like separate actions (start with an action verb)
    if len(parts) <= 1:
        single = resolve(ctx, scores)
        return [single] if single else []

    # Validate that at least 2 parts start with action verbs
    action_parts = []
    for part in parts:
        first_word = part.split()[0].lower() if part.split() else ""
        if first_word in _ACTION_VERBS:
            action_parts.append(part)
        else:
            # Merge non-verb parts with the previous action
            if action_parts:
                action_parts[-1] = action_parts[-1] + " " + part
            else:
                action_parts.append(part)

    if len(action_parts) <= 1:
        single = resolve(ctx, scores)
        return [single] if single else []

    # Build ActionRequest for each sub-command
    requests: list[ActionRequest] = []
    for part in action_parts:
        action_type = _detect_action_type_for_text(part)
        target = _extract_target(part, action_type)
        risk_level = _get_risk_level(action_type, target, part)
        needs_confirm = risk_level in ("HIGH", "CRITICAL")

        requests.append(ActionRequest(
            action_type=action_type,
            command=part,
            target=target,
            risk_level=risk_level,
            needs_confirmation=needs_confirm,
        ))

    return requests
