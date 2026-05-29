"""
Action System: Undo Manager

Stack of recent undoable actions (max 20, 5-minute window).
Supports file restore from quarky_trash/, volume/brightness revert,
and file-snapshot restore for destructive file operations.
"""

import shutil
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.config.config import ACTIONS_DIR
from core.capabilities.result_reporter import ActionResult, UndoInfo


# Snapshot dir for file backups before destructive ops
_SNAPSHOT_DIR = ACTIONS_DIR / "undo_snapshots"
_UNDO_TTL_SECONDS = 300  # 5 minutes


@dataclass
class UndoEntry:
    """A recorded undoable action."""
    action_type: str
    undo_info: UndoInfo
    timestamp: float
    description: str


# Undo stack — most recent at the end
_undo_stack: deque[UndoEntry] = deque(maxlen=20)


def record(action_type: str, undo_info: UndoInfo) -> None:
    """Record an undoable action after successful execution."""
    entry = UndoEntry(
        action_type=action_type,
        undo_info=undo_info,
        timestamp=time.time(),
        description=undo_info.description,
    )
    _undo_stack.append(entry)
    # Prune expired entries from bottom of stack
    _prune_expired()


def snapshot_file(path: str) -> UndoInfo | None:
    """
    Create a backup snapshot of a file before a destructive operation.
    Returns an UndoInfo that can be used to restore it, or None on failure.
    """
    src = Path(path)
    if not src.exists() or not src.is_file():
        return None
    try:
        _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snap_name = f"{src.name}.{int(time.time() * 1000)}"
        dest = _SNAPSHOT_DIR / snap_name
        shutil.copy2(str(src), str(dest))
        return UndoInfo(
            undo_type="file_snapshot_restore",
            previous_value={"original": str(src), "snapshot": str(dest)},
            description=f"Restore {src.name} from snapshot",
        )
    except Exception:
        return None


def _prune_expired() -> None:
    """Remove entries older than TTL."""
    cutoff = time.time() - _UNDO_TTL_SECONDS
    while _undo_stack and _undo_stack[0].timestamp < cutoff:
        expired = _undo_stack.popleft()
        # Clean up snapshot files for expired entries
        if expired.undo_info.undo_type == "file_snapshot_restore":
            snap = expired.undo_info.previous_value.get("snapshot", "")
            try:
                Path(snap).unlink(missing_ok=True)
            except Exception:
                pass


def undo_last() -> ActionResult:
    """Undo the most recent undoable action."""
    if not _undo_stack:
        return ActionResult(success=False, message="Nothing to undo.")

    entry = _undo_stack.pop()
    undo_type = entry.undo_info.undo_type

    if undo_type == "file_restore":
        return _undo_file_restore(entry.undo_info)

    if undo_type == "volume_revert":
        return _undo_volume(entry.undo_info)

    if undo_type == "brightness_revert":
        return _undo_brightness(entry.undo_info)

    if undo_type == "file_snapshot_restore":
        return _undo_file_snapshot(entry.undo_info)

    return ActionResult(
        success=False,
        message=f"Unknown undo type: {undo_type}",
    )


def _undo_file_restore(info: UndoInfo) -> ActionResult:
    """Restore a file from quarky_trash/."""
    try:
        from core.capabilities.action.file_manager import undo_delete
        return undo_delete()
    except Exception as e:
        return ActionResult(success=False, message=f"File restore failed: {e}")


def _undo_volume(info: UndoInfo) -> ActionResult:
    """Revert volume to previous state."""
    try:
        from core.capabilities.action.system_control import undo_volume
        return undo_volume()
    except Exception as e:
        return ActionResult(success=False, message=f"Volume undo failed: {e}")


def _undo_brightness(info: UndoInfo) -> ActionResult:
    """Revert brightness to previous state."""
    try:
        from core.capabilities.action.system_control import undo_brightness
        return undo_brightness()
    except Exception as e:
        return ActionResult(success=False, message=f"Brightness undo failed: {e}")


def _undo_file_snapshot(info: UndoInfo) -> ActionResult:
    """Restore a file from its pre-operation snapshot."""
    try:
        data = info.previous_value
        original = data.get("original", "")
        snapshot = data.get("snapshot", "")
        if not original or not snapshot:
            return ActionResult(success=False, message="Missing snapshot info.")
        snap_path = Path(snapshot)
        if not snap_path.exists():
            return ActionResult(success=False, message="Snapshot file expired or missing.")
        shutil.copy2(str(snap_path), original)
        snap_path.unlink(missing_ok=True)
        return ActionResult(
            success=True,
            message=f"Restored {Path(original).name} from snapshot.",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Snapshot restore failed: {e}")


def get_undo_history() -> list[dict[str, Any]]:
    """Return list of available undo actions."""
    return [
        {
            "action_type": entry.action_type,
            "description": entry.description,
            "timestamp": entry.timestamp,
        }
        for entry in reversed(_undo_stack)
    ]


def undo_count() -> int:
    """Number of undoable actions available."""
    return len(_undo_stack)


def clear() -> None:
    """Clear the undo stack."""
    _undo_stack.clear()
