"""
Quarky_Ai — Auto-Backup System

Hourly backup of memory JSON files + SQLite DB to data/backups/.
Keeps last 24 hourly + last 7 daily backups.
Manual /export creates a timestamped zip of all data.
"""

import os
import shutil
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

from AppStudio.Config import DATA_DIR, MEMORY_DIR, DB_PATH, ACTIONS_DIR


_BACKUP_DIR = DATA_DIR / "backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

_backup_thread: threading.Thread | None = None
_running = False
_interval = 3600  # 1 hour


def _create_backup() -> Path | None:
    """Create a single backup of all memory and action data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = _BACKUP_DIR / f"backup_{timestamp}"

    try:
        backup_folder.mkdir(parents=True, exist_ok=True)

        # Copy memory JSON files
        memory_dest = backup_folder / "memory"
        memory_dest.mkdir(exist_ok=True)
        for f in MEMORY_DIR.glob("*.json"):
            shutil.copy2(f, memory_dest / f.name)

        # Copy SQLite DB
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, backup_folder / "quarky.db")

        # Copy action data
        actions_dest = backup_folder / "actions"
        actions_dest.mkdir(exist_ok=True)
        for f in ACTIONS_DIR.glob("*.json"):
            shutil.copy2(f, actions_dest / f.name)

        return backup_folder
    except Exception:
        return None


def _cleanup_old_backups() -> None:
    """Keep last 24 hourly + last 7 daily. Remove the rest."""
    if not _BACKUP_DIR.exists():
        return

    backups = sorted(
        [d for d in _BACKUP_DIR.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        key=lambda d: d.name,
        reverse=True,
    )

    # Keep the 24 most recent
    keep = set(backups[:24])

    # Also keep one per day for the last 7 days
    seen_days: set[str] = set()
    for b in backups:
        day = b.name[7:15]  # YYYYMMDD from backup_YYYYMMDD_HHMMSS
        if day not in seen_days and len(seen_days) < 7:
            seen_days.add(day)
            keep.add(b)

    # Remove everything else
    for b in backups:
        if b not in keep:
            try:
                shutil.rmtree(b)
            except Exception:
                pass


def _backup_loop() -> None:
    """Background loop that runs backup at configured interval."""
    global _running
    while _running:
        _create_backup()
        _cleanup_old_backups()
        for _ in range(_interval):
            if not _running:
                break
            time.sleep(1)


def start_backup(interval: int = 3600) -> None:
    """Start the background backup thread."""
    global _backup_thread, _running, _interval

    if _running:
        return

    _interval = interval
    _running = True
    _backup_thread = threading.Thread(
        target=_backup_loop, daemon=True, name="AutoBackup"
    )
    _backup_thread.start()


def stop_backup() -> None:
    """Stop the backup thread."""
    global _running
    _running = False


def run_backup_once() -> Path | None:
    """Run a single backup manually."""
    result = _create_backup()
    _cleanup_old_backups()
    return result


def export_all() -> Path:
    """
    Export all data (memory, actions, config, sessions) to a timestamped zip.
    Returns the path to the created zip file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"quarky_export_{timestamp}.zip"
    zip_path = _BACKUP_DIR / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Memory files
        for f in MEMORY_DIR.glob("*.json"):
            zf.write(f, f"memory/{f.name}")

        # SQLite DB
        if DB_PATH.exists():
            zf.write(DB_PATH, "quarky.db")

        # Action data
        for f in ACTIONS_DIR.glob("*.json"):
            zf.write(f, f"actions/{f.name}")

        # Config
        config_path = Path(__file__).resolve().parent / "config.py"
        if config_path.exists():
            zf.write(config_path, "config.py")

    return zip_path
