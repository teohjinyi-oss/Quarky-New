"""
Voice: Wake Word Detector

Listens for the wake word ("hey quarky" / "quarky") via Vosk partial results.
Invokes a callback when detected.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from runtime.config.config import CONFIG

_VOSK_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer  # type: ignore[import-untyped]
    _VOSK_AVAILABLE = True
except ImportError:
    Model = None  # type: ignore[assignment]
    KaldiRecognizer = None  # type: ignore[assignment]

WAKE_PHRASES = {"quarky", "hey quarky", "ok quarky", "what's up quarky", "whats up quarky"}

# Debounce period: ignore re-triggers within this window (seconds)
_DEBOUNCE_SECONDS = 2.0


class WakeDetector:
    """Detects the wake word from raw audio chunks."""

    def __init__(self):
        self._recognizer: Any = None
        self._on_wake: Callable[[], None] | None = None
        self._active = False
        self._last_wake_time: float = 0.0

    @property
    def available(self) -> bool:
        return _VOSK_AVAILABLE

    def set_on_wake(self, callback: Callable[[], None]):
        self._on_wake = callback

    def start(self) -> bool:
        """Initialize Vosk model. Returns False if unavailable."""
        if not _VOSK_AVAILABLE:
            return False
        start_cfg = CONFIG.get("START", {})
        model_path = str(start_cfg.get("vosk_model_path", "models/vosk-model-small-en-us-0.15"))
        try:
            model = Model(model_path)  # type: ignore[misc]
            self._recognizer = KaldiRecognizer(model, 16000)  # type: ignore[misc]
            self._recognizer.SetWords(True)
            self._active = True
            return True
        except Exception:
            return False

    def stop(self):
        self._active = False
        self._recognizer = None

    def reset(self):
        """Reset the recognizer state for a new detection cycle."""
        if self._recognizer:
            self._recognizer.Reset()

    @property
    def is_active(self) -> bool:
        return self._active

    def feed(self, chunk: bytes):
        """Feed an audio chunk. Fires callback if wake word detected."""
        recognizer = self._recognizer
        if not recognizer or not self._active:
            return
        if recognizer.AcceptWaveform(chunk):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").lower().strip()
            if self._is_wake(text):
                self._fire()
            if self._recognizer is recognizer:
                recognizer.Reset()
        else:
            # Stop/reset can flip recognizer to None mid-cycle.
            if self._recognizer is not recognizer:
                return
            partial = json.loads(recognizer.PartialResult())
            text = partial.get("partial", "").lower().strip()
            if self._is_wake(text):
                self._fire()
                if self._recognizer is recognizer:
                    recognizer.Reset()

    def _is_wake(self, text: str) -> bool:
        return any(w in text for w in WAKE_PHRASES)

    def _fire(self):
        now = time.monotonic()
        if now - self._last_wake_time < _DEBOUNCE_SECONDS:
            return  # debounce: too soon after last wake
        self._last_wake_time = now
        if self._on_wake:
            self._on_wake()
