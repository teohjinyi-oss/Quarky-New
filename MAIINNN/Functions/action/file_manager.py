"""
Action System: File Manager

File operations with 3-tier permission system and soft delete.
Supports: create, move, copy, rename, delete (to trash), search, list.
System paths are blocked. Undo restores from quarky_trash/.
"""

import shutil
import time
from pathlib import Path
from typing import Any

from AppStudio.Config import DATA_DIR
from MAIINNN.Decision.action_resolver import ActionRequest
from MAIINNN.Functions.result_reporter import ActionResult, UndoInfo
from MAIINNN.Functions.action.safety import is_system_path


_TRASH_DIR = DATA_DIR / "quarky_trash"
_TRASH_DIR.mkdir(parents=True, exist_ok=True)

# Track last trashed item for undo
_last_trashed: dict[str, str] = {}  # trash_name → original_path


def execute(action_request: ActionRequest) -> ActionResult:
    """
    Main handler for file_op actions.
    Routes based on keywords in target/command.
    """
    target = action_request.target.strip()
    command = action_request.command.lower()
    params = action_request.parameters

    if not target:
        return ActionResult(success=False, message="No file target specified.")

    # Block system paths
    if is_system_path(target):
        return ActionResult(
            success=False,
            message=f"Blocked: cannot operate on system path '{target}'.",
        )

    if "delete" in command or "remove" in command:
        return _delete_file(target)
    if "create" in command or "make" in command or "new" in command:
        content = params.get("content", "")
        return _create_file(target, content)
    if "move" in command:
        dest = params.get("destination", "")
        return _move_file(target, dest)
    if "copy" in command:
        dest = params.get("destination", "")
        return _copy_file(target, dest)
    if "rename" in command:
        new_name = params.get("new_name", "")
        return _rename_file(target, new_name)
    if "search" in command or "find" in command:
        pattern = params.get("pattern", "*")
        return _search_files(target, pattern)
    if "list" in command or "ls" in command or "dir" in command:
        return _list_directory(target)

    return ActionResult(
        success=False,
        message=f"Unknown file operation. Target: {target}",
    )


def _create_file(path: str, content: str = "") -> ActionResult:
    """Create a file with optional content."""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ActionResult(
            success=True,
            message=f"Created file: {p.name}",
            data={"path": str(p)},
        )
    except PermissionError:
        return ActionResult(success=False, message=f"Permission denied: {path}")
    except Exception as e:
        return ActionResult(success=False, message=f"Create failed: {e}")


def _delete_file(path: str) -> ActionResult:
    """Soft delete — move to quarky_trash/ instead of permanent deletion."""
    p = Path(path)
    if not p.exists():
        return ActionResult(success=False, message=f"File not found: {path}")

    try:
        trash_name = f"{int(time.time())}_{p.name}"
        trash_path = _TRASH_DIR / trash_name

        if p.is_dir():
            shutil.move(str(p), str(trash_path))
        else:
            shutil.move(str(p), str(trash_path))

        _last_trashed[trash_name] = str(p)

        return ActionResult(
            success=True,
            message=f"Moved to trash: {p.name}",
            data={"trash_path": str(trash_path), "original": str(p)},
            undo_info=UndoInfo(
                undo_type="file_restore",
                previous_value=str(p),
                trash_path=str(trash_path),
                description=f"Restore {p.name} from trash",
            ),
        )
    except PermissionError:
        return ActionResult(success=False, message=f"Permission denied: {path}")
    except Exception as e:
        return ActionResult(success=False, message=f"Delete failed: {e}")


def _move_file(source: str, dest: str) -> ActionResult:
    """Move a file or directory."""
    if not dest:
        return ActionResult(success=False, message="No destination specified for move.")

    src = Path(source)
    dst = Path(dest)

    if not src.exists():
        return ActionResult(success=False, message=f"Source not found: {source}")

    if is_system_path(dest):
        return ActionResult(success=False, message=f"Cannot move to system path: {dest}")

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return ActionResult(
            success=True,
            message=f"Moved: {src.name} → {dst}",
            data={"source": str(src), "destination": str(dst)},
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Move failed: {e}")


def _copy_file(source: str, dest: str) -> ActionResult:
    """Copy a file or directory."""
    if not dest:
        return ActionResult(success=False, message="No destination specified for copy.")

    src = Path(source)
    dst = Path(dest)

    if not src.exists():
        return ActionResult(success=False, message=f"Source not found: {source}")

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        return ActionResult(
            success=True,
            message=f"Copied: {src.name} → {dst}",
            data={"source": str(src), "destination": str(dst)},
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Copy failed: {e}")


def _rename_file(path: str, new_name: str) -> ActionResult:
    """Rename a file or directory."""
    if not new_name:
        return ActionResult(success=False, message="No new name specified.")

    p = Path(path)
    if not p.exists():
        return ActionResult(success=False, message=f"File not found: {path}")

    try:
        new_path = p.parent / new_name
        p.rename(new_path)
        return ActionResult(
            success=True,
            message=f"Renamed: {p.name} → {new_name}",
            data={"old": str(p), "new": str(new_path)},
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Rename failed: {e}")


def _search_files(directory: str, pattern: str = "*") -> ActionResult:
    """Search for files matching a pattern in a directory."""
    d = Path(directory)
    if not d.exists() or not d.is_dir():
        return ActionResult(success=False, message=f"Directory not found: {directory}")

    try:
        matches = list(d.rglob(pattern))[:50]  # Limit results
        file_list = [str(m) for m in matches]
        return ActionResult(
            success=True,
            message=f"Found {len(file_list)} file(s) matching '{pattern}'.",
            data={"files": file_list, "count": len(file_list)},
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Search failed: {e}")


def _list_directory(path: str) -> ActionResult:
    """List contents of a directory."""
    d = Path(path)
    if not d.exists():
        return ActionResult(success=False, message=f"Directory not found: {path}")
    if not d.is_dir():
        return ActionResult(success=False, message=f"Not a directory: {path}")

    try:
        entries = []
        for item in sorted(d.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return ActionResult(
            success=True,
            message=f"Listed {len(entries)} item(s) in {d.name}/",
            data={"entries": entries[:100]},  # Limit
        )
    except PermissionError:
        return ActionResult(success=False, message=f"Permission denied: {path}")
    except Exception as e:
        return ActionResult(success=False, message=f"List failed: {e}")


# ─── Undo / Trash Management ────────────────────────────────

def undo_delete() -> ActionResult:
    """Restore the last trashed file to its original location."""
    if not _last_trashed:
        return ActionResult(success=False, message="Nothing to restore from trash.")

    # Get the most recent trashed item
    trash_name = list(_last_trashed.keys())[-1]
    original_path = _last_trashed[trash_name]
    trash_path = _TRASH_DIR / trash_name

    if not trash_path.exists():
        _last_trashed.pop(trash_name, None)
        return ActionResult(
            success=False, message="Trashed file no longer exists.")

    try:
        shutil.move(str(trash_path), original_path)
        _last_trashed.pop(trash_name, None)
        return ActionResult(
            success=True,
            message=f"Restored: {Path(original_path).name}",
            data={"restored_to": original_path},
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Restore failed: {e}")


def list_trash() -> list[dict[str, str]]:
    """List items in the trash."""
    items = []
    for name, original in _last_trashed.items():
        items.append({"trash_name": name, "original_path": original})
    return items
