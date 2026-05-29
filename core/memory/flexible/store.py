"""
Flexible Memory: Store Department

Reads/writes flexible entries to JSON file.
Thread-safe. Enforces max_entries (oldest evicted).
"""

import json
import threading
from pathlib import Path

from runtime.config.config import MEMORY
from core.memory.flexible.intake import FlexEntry

_lock = threading.Lock()


def _load_raw() -> list[dict]:
    path: Path = MEMORY["flexible_file"]
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("entries", [])
    except (json.JSONDecodeError, KeyError):
        return []


def _save_raw(entries: list[dict]) -> None:
    path: Path = MEMORY["flexible_file"]
    payload = {
        "entries": entries,
        "_meta": {
            "description": "Flexible memory — summarized entries",
            "count": len(entries),
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_all() -> list[FlexEntry]:
    with _lock:
        raw = _load_raw()
    return [FlexEntry.from_dict(d) for d in raw]


def save_entry(entry: FlexEntry) -> None:
    max_entries = MEMORY["flexible_max_entries"]
    with _lock:
        entries = _load_raw()
        entries.append(entry.to_dict())
        if len(entries) > max_entries:
            entries = entries[-max_entries:]
        _save_raw(entries)


def save_all(entries: list[FlexEntry]) -> None:
    with _lock:
        _save_raw([e.to_dict() for e in entries])


def delete_entry(entry_id: str) -> bool:
    with _lock:
        entries = _load_raw()
        before = len(entries)
        entries = [e for e in entries if e.get("id") != entry_id]
        _save_raw(entries)
        return len(entries) < before


def update_entry(entry: FlexEntry) -> bool:
    """Update an existing entry in-place by ID."""
    with _lock:
        entries = _load_raw()
        for i, e in enumerate(entries):
            if e.get("id") == entry.id:
                entries[i] = entry.to_dict()
                _save_raw(entries)
                return True
        return False


def count() -> int:
    with _lock:
        return len(_load_raw())
