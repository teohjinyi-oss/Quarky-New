"""
Priority Memory: Store Department

Reads/writes priority entries to JSON file.
Thread-safe. Enforces max_entries.
"""

import json
import threading
from pathlib import Path

from AppStudio.Config import MEMORY
from MAIINNN.Memory.priority.intake import PriorityEntry

_lock = threading.Lock()


def _load_raw() -> list[dict]:
    path: Path = MEMORY["priority_file"]
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("entries", [])
    except (json.JSONDecodeError, KeyError):
        return []


def _save_raw(entries: list[dict]) -> None:
    path: Path = MEMORY["priority_file"]
    payload = {
        "entries": entries,
        "_meta": {
            "description": "Priority memory — importance-scored entries",
            "count": len(entries),
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_all() -> list[PriorityEntry]:
    with _lock:
        raw = _load_raw()
    return [PriorityEntry.from_dict(d) for d in raw]


def save_entry(entry: PriorityEntry) -> None:
    max_entries = MEMORY["priority_max_entries"]
    with _lock:
        entries = _load_raw()
        entries.append(entry.to_dict())
        if len(entries) > max_entries:
            # Evict lowest importance entries
            entries.sort(key=lambda e: e.get("importance", 0), reverse=True)
            entries = entries[:max_entries]
        _save_raw(entries)


def save_all(entries: list[PriorityEntry]) -> None:
    with _lock:
        _save_raw([e.to_dict() for e in entries])


def update_entry(entry: PriorityEntry) -> bool:
    with _lock:
        entries = _load_raw()
        for i, e in enumerate(entries):
            if e.get("id") == entry.id:
                entries[i] = entry.to_dict()
                _save_raw(entries)
                return True
        return False


def delete_entry(entry_id: str) -> bool:
    with _lock:
        entries = _load_raw()
        before = len(entries)
        entries = [e for e in entries if e.get("id") != entry_id]
        _save_raw(entries)
        return len(entries) < before


def count() -> int:
    with _lock:
        return len(_load_raw())
