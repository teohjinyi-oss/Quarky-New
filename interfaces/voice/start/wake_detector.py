"""
Start System: Wake Word Detector

Listens to the microphone stream and detects the wake word ("quarky")
using Vosk partial recognition. When detected, signals the state manager
to transition from IDLE → LISTENING.
"""

import json
import threading
from typing import Any, Callable

from runtime.config.config import START

_WAKE_WORD: str = START["wake_word"].lower()
_SAMPLE_RATE: int = START["sample_rate"]

_recognizer: Any = None
_model: Any = None
_on_wake: Callable[[], None] | None = None
_active = threading.Event()


def _init_vosk() -> bool:
    """Lazy-load and initialize Vosk model + recognizer."""
    global _recognizer, _model
    if _recognizer is not None:
        return True

    try:
        from vosk import Model, KaldiRecognizer
    except ImportError:
        return False

    model_path = str(START["vosk_model_path"])
    try:
        _model = Model(model_path)
    except Exception:
        return False

    _recognizer = KaldiRecognizer(_model, _SAMPLE_RATE)
    return True


def set_on_wake(callback: Callable[[], None]) -> None:
    """Register the function to call when the wake word is detected."""
    global _on_wake
    _on_wake = callback


def feed(audio_chunk: bytes) -> bool:
    """
    Feed an audio chunk for wake word detection.
    Returns True if the wake word was detected in this chunk.
    """
    if _recognizer is None:
        if not _init_vosk():
            return False

    if not _active.is_set():
        return False

    # Check partial results for wake word (faster than waiting for full result)
    _recognizer.AcceptWaveform(audio_chunk)
    partial = json.loads(_recognizer.PartialResult())
    partial_text = partial.get("partial", "").lower()

    if _WAKE_WORD in partial_text:
        # Reset recognizer to avoid re-triggering
        _recognizer.Reset()
        if _on_wake:
            _on_wake()
        return True

    return False


def start() -> bool:
    """
    Activate wake word detection.
    Returns True if ready, False if Vosk can't initialize.
    """
    if not _init_vosk():
        return False
    _active.set()
    return True


def stop() -> None:
    """Deactivate wake word detection."""
    _active.clear()


def is_active() -> bool:
    """Check if wake detection is active."""
    return _active.is_set()


def reset() -> None:
    """Reset the recognizer state (e.g. after a detection)."""
    if _recognizer is not None:
        _recognizer.Reset()
