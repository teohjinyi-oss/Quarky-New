"""
Temporary Memory: Store Department

Reads/writes temporary entries to JSON file.
Thread-safe with a lock. Enforces max_entries limit (FIFO eviction).
"""

import json
import threading
from pathlib import Path
from typing import Any

from AppStudio.Config import MEMORY
from MAIINNN.Memory.temporary.intake import TempEntry

_lock = threading.Lock()


def _load_raw() -> list[dict]:
    """Load raw entries from JSON file."""
    path: Path = MEMORY["temporary_file"]
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("entries", [])
    except (json.JSONDecodeError, KeyError):
        return []


def _save_raw(entries: list[dict]) -> None:
    """Save entries to JSON file."""
    path: Path = MEMORY["temporary_file"]
    payload = {
        "entries": entries,
        "_meta": {
            "description": "Temporary memory — auto-expiring entries",
            "count": len(entries),
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_all() -> list[TempEntry]:
    """Load all temporary entries as TempEntry objects."""
    with _lock:
        raw = _load_raw()
    return [TempEntry.from_dict(d) for d in raw]


def save_entry(entry: TempEntry) -> None:
    """
    Append a new entry. Enforces max_entries (oldest evicted first).
    """
    max_entries = MEMORY["temporary_max_entries"]

    with _lock:
        entries = _load_raw()
        entries.append(entry.to_dict())

        # FIFO eviction if over limit
        if len(entries) > max_entries:
            entries = entries[-max_entries:]

        _save_raw(entries)


def save_all(entries: list[TempEntry]) -> None:
    """Overwrite all entries (used by cleanup)."""
    with _lock:
        _save_raw([e.to_dict() for e in entries])


def delete_entry(entry_id: str) -> bool:
    """Delete a single entry by ID. Returns True if found."""
    with _lock:
        entries = _load_raw()
        before = len(entries)
        entries = [e for e in entries if e.get("id") != entry_id]
        _save_raw(entries)
        return len(entries) < before


def count() -> int:
    """Get current entry count."""
    with _lock:
        return len(_load_raw())
