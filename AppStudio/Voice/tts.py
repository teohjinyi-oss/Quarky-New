"""
Voice: TTS (Text-to-Speech)

Speaks text aloud using pyttsx3.
Thread-safe — queues utterances and plays them sequentially.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

_PYTTSX3_AVAILABLE = False
try:
    import pyttsx3  # type: ignore[import-untyped]
    _PYTTSX3_AVAILABLE = True
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]


class TTSEngine:
    """Text-to-speech using pyttsx3."""

    def __init__(self, rate: int = 175, volume: float = 0.9):
        self._rate = rate
        self._volume = volume
        self._engine: Any = None
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def available(self) -> bool:
        return _PYTTSX3_AVAILABLE

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Start the TTS worker thread. Returns False if pyttsx3 unavailable."""
        if not _PYTTSX3_AVAILABLE or self._running:
            return self._running
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="tts-worker")
        self._thread.start()
        return True

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._queue.put(None)  # sentinel
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def speak(self, text: str):
        """Queue text to be spoken."""
        if self._running:
            self._queue.put(text)

    def _worker(self):
        """Background thread: initializes engine and speaks queued items."""
        try:
            self._engine = pyttsx3.init()  # type: ignore[union-attr]
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)
        except Exception:
            self._running = False
            return

        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass  # TTS failures shouldn't crash the pipeline

        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
