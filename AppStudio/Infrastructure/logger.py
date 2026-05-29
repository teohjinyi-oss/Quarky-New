"""
Infrastructure: Transport Logger

Logs every message that flows through Infrastructure.
Used for debugging, monitoring, and auditing.
Supports JSON structured logging with rotating file output (10 MB).
"""

import json
import os
import time
import threading
from collections import deque
from pathlib import Path
from typing import Optional

from AppStudio.Config import LOG, DATA_DIR


_LOG_DIR = DATA_DIR / "logs"
_LOG_FILE = _LOG_DIR / "quarky.jsonl"
_MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB


class LogEntry:
    __slots__ = ("timestamp", "level", "source", "target", "mode",
                 "payload_size", "message", "duration_ms")

    def __init__(self, level: str, source: str, target: str,
                 mode: str = "", payload_size: int = 0,
                 message: str = "", duration_ms: float = 0.0):
        self.timestamp = time.time()
        self.level = level
        self.source = source
        self.target = target
        self.mode = mode
        self.payload_size = payload_size
        self.message = message
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "ts": self.timestamp,
            "level": self.level,
            "src": self.source,
            "tgt": self.target,
            "mode": self.mode,
            "size": self.payload_size,
            "msg": self.message,
            "ms": round(self.duration_ms, 2),
        }

    def __repr__(self) -> str:
        t = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[{t}] {self.level} {self.source}→{self.target} ({self.mode}) {self.message}"


class InfraLogger:
    """
    Centralized logger for all infrastructure transport events.

    Thread-safe, bounded ring buffer (prevents unbounded memory growth).
    """

    _instance: Optional["InfraLogger"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "InfraLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        max_entries = LOG.get("transport_log_max_entries", 10000)
        self._buffer: deque[LogEntry] = deque(maxlen=max_entries)
        self._console = LOG.get("log_to_console", True)
        self._file_logging = LOG.get("log_to_file", True)
        self._level = LOG.get("log_level", "INFO")
        self._level_rank = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        self._min_rank = self._level_rank.get(self._level, 1)
        self._write_lock = threading.Lock()
        # Ensure log directory exists
        if self._file_logging:
            try:
                _LOG_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                self._file_logging = False

    def _should_log(self, level: str) -> bool:
        return self._level_rank.get(level, 1) >= self._min_rank

    def log(self, level: str, source: str, target: str,
            mode: str = "", payload_size: int = 0,
            message: str = "", duration_ms: float = 0.0):
        if not self._should_log(level):
            return

        entry = LogEntry(level, source, target, mode,
                         payload_size, message, duration_ms)

        with self._write_lock:
            self._buffer.append(entry)

        if self._console:
            print(repr(entry))

        if self._file_logging:
            self._write_json(entry)

    def debug(self, source: str, target: str, message: str = "", **kw):
        self.log("DEBUG", source, target, message=message, **kw)

    def info(self, source: str, target: str, message: str = "", **kw):
        self.log("INFO", source, target, message=message, **kw)

    def warning(self, source: str, target: str, message: str = "", **kw):
        self.log("WARNING", source, target, message=message, **kw)

    def error(self, source: str, target: str, message: str = "", **kw):
        self.log("ERROR", source, target, message=message, **kw)

    def get_recent(self, count: int = 50) -> list[dict]:
        """Get the N most recent log entries."""
        with self._write_lock:
            entries = list(self._buffer)[-count:]
        return [e.to_dict() for e in entries]

    def get_by_source(self, source: str, count: int = 50) -> list[dict]:
        with self._write_lock:
            entries = [e for e in self._buffer if e.source == source]
        return [e.to_dict() for e in entries[-count:]]

    def clear(self):
        with self._write_lock:
            self._buffer.clear()

    @property
    def total_entries(self) -> int:
        return len(self._buffer)

    def _write_json(self, entry: LogEntry) -> None:
        """Append a JSON line to the log file, rotating if over max size."""
        try:
            if _LOG_FILE.exists() and _LOG_FILE.stat().st_size > _MAX_LOG_SIZE:
                self._rotate()
            line = json.dumps(entry.to_dict(), default=str)
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    @staticmethod
    def _rotate() -> None:
        """Rotate log file: rename current → .1, delete .2 if exists."""
        try:
            backup = _LOG_DIR / "quarky.1.jsonl"
            old_backup = _LOG_DIR / "quarky.2.jsonl"
            if old_backup.exists():
                old_backup.unlink()
            if backup.exists():
                backup.rename(old_backup)
            _LOG_FILE.rename(backup)
        except Exception:
            pass
