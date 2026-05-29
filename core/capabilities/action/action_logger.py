"""
Action System: Action Logger

Append-only JSON log for every action executed.
Provides get_recent(), get_by_type(), get_stats() for /actions command.
"""

import json
import time
import threading
from typing import Any

from runtime.config.config import ACTION


_LOG_FILE = ACTION["log_file"]
_lock = threading.Lock()


def _ensure_log_file() -> None:
    if not _LOG_FILE.exists():
        _LOG_FILE.write_text("[]", encoding="utf-8")


def _read_log() -> list[dict[str, Any]]:
    _ensure_log_file()
    try:
        data = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_log(entries: list[dict[str, Any]]) -> None:
    _LOG_FILE.write_text(json.dumps(entries, indent=2, default=str),
                         encoding="utf-8")


def log_action(action_type: str, target: str, risk_level: str,
               success: bool, message: str, duration_ms: float = 0.0,
               undo_available: bool = False) -> None:
    """Append a single action entry to the log file."""
    entry = {
        "timestamp": time.time(),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action_type": action_type,
        "target": target,
        "risk_level": risk_level,
        "success": success,
        "message": message,
        "duration_ms": round(duration_ms, 2),
        "undo_available": undo_available,
    }

    with _lock:
        entries = _read_log()
        entries.append(entry)
        # Keep last 1000 entries to prevent unbounded growth
        if len(entries) > 1000:
            entries = entries[-1000:]
        _write_log(entries)


def get_recent(count: int = 20) -> list[dict[str, Any]]:
    """Return the most recent N log entries."""
    with _lock:
        entries = _read_log()
    return entries[-count:] if entries else []


def get_by_type(action_type: str, count: int = 20) -> list[dict[str, Any]]:
    """Return recent entries filtered by action type."""
    with _lock:
        entries = _read_log()
    filtered = [e for e in entries if e.get("action_type") == action_type]
    return filtered[-count:]


def get_stats() -> dict[str, Any]:
    """Return aggregate action statistics."""
    with _lock:
        entries = _read_log()

    if not entries:
        return {
            "total_actions": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0.0,
            "by_type": {},
            "by_risk": {},
        }

    total = len(entries)
    successful = sum(1 for e in entries if e.get("success"))
    failed = total - successful

    by_type: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for e in entries:
        t = e.get("action_type", "unknown")
        r = e.get("risk_level", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_risk[r] = by_risk.get(r, 0) + 1

    return {
        "total_actions": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round(successful / total, 3) if total else 0.0,
        "by_type": by_type,
        "by_risk": by_risk,
    }


def clear_log() -> None:
    """Clear the entire action log."""
    with _lock:
        _write_log([])
