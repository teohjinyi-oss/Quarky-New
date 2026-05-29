"""
Voice: Microphone

Audio capture from the system microphone using sounddevice.
Provides a thread-safe chunk queue for downstream consumers.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

_SD_AVAILABLE = False
try:
    import sounddevice as sd  # type: ignore[import-untyped]
    import numpy as np
    _SD_AVAILABLE = True
except ImportError:
    sd = None  # type: ignore[assignment]

SAMPLE_RATE = 16000
BLOCK_SIZE = 4000  # ~250ms at 16kHz


class Microphone:
    """Captures audio from the default input device."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = BLOCK_SIZE):
        self._sr = sample_rate
        self._bs = block_size
        self._q: queue.Queue[bytes] = queue.Queue(maxsize=200)
        self._stream: Any = None
        self._running = False

    @property
    def available(self) -> bool:
        return _SD_AVAILABLE

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Start capturing audio. Returns False if sounddevice unavailable."""
        if not _SD_AVAILABLE or self._running:
            return self._running
        try:
            self._stream = sd.RawInputStream(  # type: ignore[union-attr]
                samplerate=self._sr,
                blocksize=self._bs,
                dtype="int16",
                channels=1,
                callback=self._callback,
            )
            self._stream.start()
            self._running = True
            return True
        except Exception:
            return False

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False

    def get_chunk(self, timeout: float = 0.3) -> bytes | None:
        """Get an audio chunk from the queue, or None on timeout."""
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self):
        """Clear any buffered chunks."""
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def _callback(self, indata: Any, frames: int, time_info: Any, status: Any):
        if status:
            pass  # could log xruns
        try:
            self._q.put_nowait(bytes(indata))
        except queue.Full:
            pass  # drop oldest would require deque; acceptable to drop for now
