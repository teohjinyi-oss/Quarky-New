"""
Action System: Safety Gate

3-tier file permission system + risk-level enforcement.
Permission tiers per path:
  "once"              — allow this one time only
  "always_auth"       — always require confirmation
  "allow_unless_risky" — auto-allow LOW/MEDIUM, confirm HIGH/CRITICAL

General risk enforcement:
  LOW    → auto-execute
  MEDIUM → auto-execute + log
  HIGH   → require user confirmation
  CRITICAL → require confirmation + detailed preview
"""

import json
import threading
from dataclasses import dataclass
from pathlib import Path

from AppStudio.Config import ACTION, ACTIONS_DIR


@dataclass
class SafetyVerdict:
    """Result of a safety check."""
    allowed: bool
    reason: str
    needs_user_input: bool = False
    permission_type: str = ""       # "once", "always_auth", "allow_unless_risky", "risk_gate"


_PERMISSIONS_FILE = ACTIONS_DIR / "permissions.json"
_lock = threading.Lock()

# Track one-time permissions that have been used this session
_used_once_permissions: set[str] = set()


def _load_permissions() -> dict[str, str]:
    """Load path → tier mapping from disk."""
    if not _PERMISSIONS_FILE.exists():
        _PERMISSIONS_FILE.write_text("{}", encoding="utf-8")
        return {}
    try:
        data = json.loads(_PERMISSIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_permissions(perms: dict[str, str]) -> None:
    _PERMISSIONS_FILE.write_text(
        json.dumps(perms, indent=2), encoding="utf-8")


def set_permission(path: str, tier: str) -> None:
    """
    Set file/directory permission tier.
    tier: "once", "always_auth", "allow_unless_risky"
    """
    if tier not in ("once", "always_auth", "allow_unless_risky"):
        return
    with _lock:
        perms = _load_permissions()
        perms[str(path)] = tier
        _save_permissions(perms)


def get_permission(path: str) -> str | None:
    """Get the permission tier for a path, or None if not set."""
    with _lock:
        perms = _load_permissions()
    # Check exact path, then parent directories
    p = Path(path).resolve()
    for check in [str(p)] + [str(parent) for parent in p.parents]:
        if check in perms:
            return perms[check]
    return None


def remove_permission(path: str) -> None:
    """Remove a stored permission."""
    with _lock:
        perms = _load_permissions()
        perms.pop(str(path), None)
        _save_permissions(perms)


def check_safety(action_type: str, target: str,
                 risk_level: str) -> SafetyVerdict:
    """
    Main safety gate. Checks risk level + path permissions.
    Returns SafetyVerdict telling the receiver whether to proceed.
    """
    # 1. Check file-specific permissions for file operations
    if action_type == "file_op" and target:
        return _check_file_permission(target, risk_level)

    # 2. Software install/update is always HIGH risk minimum
    if action_type in ("software_install", "software_update"):
        effective_risk = "HIGH" if risk_level in ("LOW", "MEDIUM") else risk_level
        return _check_risk_gate(action_type, effective_risk)

    # 3. General risk-level gate for all other actions
    return _check_risk_gate(action_type, risk_level)


def _check_file_permission(target: str, risk_level: str) -> SafetyVerdict:
    """Apply 3-tier file permission logic."""
    tier = get_permission(target)

    if tier == "once":
        # Check if already used this session
        if target in _used_once_permissions:
            return SafetyVerdict(
                allowed=False,
                reason="One-time permission already used this session. Re-authorize required.",
                needs_user_input=True,
                permission_type="once_expired",
            )
        # Mark as used and allow
        _used_once_permissions.add(target)
        return SafetyVerdict(
            allowed=True,
            reason="One-time permission granted.",
            permission_type="once",
        )

    if tier == "always_auth":
        return SafetyVerdict(
            allowed=False,
            reason=f"Path requires confirmation: {target}",
            needs_user_input=True,
            permission_type="always_auth",
        )

    if tier == "allow_unless_risky":
        if risk_level in ("LOW", "MEDIUM"):
            return SafetyVerdict(
                allowed=True,
                reason="Path auto-allowed for safe operations.",
                permission_type="allow_unless_risky",
            )
        return SafetyVerdict(
            allowed=False,
            reason=f"Risky operation on managed path: {target}",
            needs_user_input=True,
            permission_type="allow_unless_risky",
        )

    # No tier set — fall back to risk-level gate
    return _check_risk_gate("file_op", risk_level)


def _check_risk_gate(action_type: str, risk_level: str) -> SafetyVerdict:
    """Standard risk-level gate: LOW/MEDIUM auto, HIGH/CRITICAL confirm."""
    if risk_level == "LOW":
        return SafetyVerdict(
            allowed=True,
            reason="Low-risk action, auto-executing.",
            permission_type="risk_gate",
        )

    if risk_level == "MEDIUM":
        return SafetyVerdict(
            allowed=True,
            reason="Medium-risk action, auto-executing with logging.",
            permission_type="risk_gate",
        )

    if risk_level == "HIGH":
        return SafetyVerdict(
            allowed=False,
            reason=f"High-risk action ({action_type}) requires confirmation.",
            needs_user_input=True,
            permission_type="risk_gate",
        )

    if risk_level == "CRITICAL":
        return SafetyVerdict(
            allowed=False,
            reason=f"CRITICAL action ({action_type}) requires explicit confirmation.",
            needs_user_input=True,
            permission_type="risk_gate",
        )

    # Unknown risk — block and ask
    return SafetyVerdict(
        allowed=False,
        reason=f"Unknown risk level '{risk_level}', blocking for safety.",
        needs_user_input=True,
        permission_type="unknown",
    )


def reset_session_permissions() -> None:
    """Reset one-time permissions for a new session."""
    _used_once_permissions.clear()


def is_system_path(path: str) -> bool:
    """Check if a path is a protected system directory."""
    blocked = [
        "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
        "C:\\System32", "C:\\ProgramData",
    ]
    resolved = str(Path(path).resolve())
    return any(resolved.lower().startswith(b.lower()) for b in blocked)
