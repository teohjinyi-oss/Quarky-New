"""
Quarky_Ai — Config File Watcher

Polls config.py for changes and reloads the module when modified.
Uses polling (no watchdog dependency required) with configurable interval.
"""

import importlib
import os
import threading
import time
from pathlib import Path

from AppStudio.Config import BASE_DIR


_CONFIG_PATH = BASE_DIR / "quarky_ai" / "config.py"
_watch_thread: threading.Thread | None = None
_watching = False
_poll_interval = 5.0  # seconds
_last_mtime: float = 0.0
_callbacks: list = []


def on_config_change(callback) -> None:
    """Register a callback to be called when config changes."""
    _callbacks.append(callback)


def _check_and_reload() -> bool:
    """Check if config.py was modified, reload if so. Returns True if reloaded."""
    global _last_mtime

    try:
        current_mtime = os.path.getmtime(_CONFIG_PATH)
    except OSError:
        return False

    if _last_mtime == 0.0:
        _last_mtime = current_mtime
        return False

    if current_mtime > _last_mtime:
        _last_mtime = current_mtime
        try:
            import AppStudio.Config as cfg
            importlib.reload(cfg)
            for cb in _callbacks:
                try:
                    cb()
                except Exception:
                    pass
            return True
        except Exception:
            return False

    return False


def _watch_loop() -> None:
    """Background polling loop."""
    global _watching
    while _watching:
        _check_and_reload()
        for _ in range(int(_poll_interval)):
            if not _watching:
                break
            time.sleep(1)


def start_watcher(interval: float = 5.0) -> None:
    """Start the config file watcher background thread."""
    global _watch_thread, _watching, _poll_interval, _last_mtime

    if _watching:
        return

    _poll_interval = interval
    try:
        _last_mtime = os.path.getmtime(_CONFIG_PATH)
    except OSError:
        _last_mtime = 0.0

    _watching = True
    _watch_thread = threading.Thread(
        target=_watch_loop, daemon=True, name="ConfigWatcher"
    )
    _watch_thread.start()


def stop_watcher() -> None:
    """Stop the config file watcher."""
    global _watching
    _watching = False
