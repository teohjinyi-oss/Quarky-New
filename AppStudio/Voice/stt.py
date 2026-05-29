"""
Voice: STT (Speech-to-Text)

Transcribes audio chunks into text using Vosk.
Supports both stream-based and single-buffer transcription.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from AppStudio.Config import CONFIG

_VOSK_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer  # type: ignore[import-untyped]
    _VOSK_AVAILABLE = True
except ImportError:
    Model = None  # type: ignore[assignment]
    KaldiRecognizer = None  # type: ignore[assignment]


class STTEngine:
    """Speech-to-text using Vosk."""

    def __init__(self):
        self._recognizer: Any = None
        self._ready = False

    @property
    def available(self) -> bool:
        return _VOSK_AVAILABLE

    def start(self) -> bool:
        """Initialize the recognizer. Returns False if Vosk unavailable."""
        if not _VOSK_AVAILABLE:
            return False
        start_cfg = CONFIG.get("START", {})
        model_path = str(start_cfg.get("vosk_model_path", "models/vosk-model-small-en-us-0.15"))
        try:
            model = Model(model_path)  # type: ignore[misc]
            self._recognizer = KaldiRecognizer(model, 16000)  # type: ignore[misc]
            self._recognizer.SetWords(True)
            self._ready = True
            return True
        except Exception:
            return False

    def transcribe_stream(
        self,
        get_chunk: Callable[[], bytes | None],
        timeout: float = 30.0,
        silence_limit: float = 2.0,
    ) -> str:
        """
        Transcribe from a live audio stream.

        get_chunk: callable returning bytes or None
        timeout: max total recording time
        silence_limit: second of silence before we stop
        """
        if not self._ready or not self._recognizer:
            return ""
        self._recognizer.Reset()

        start = time.monotonic()
        last_speech = time.monotonic()
        texts: list[str] = []

        while time.monotonic() - start < timeout:
            chunk = get_chunk()
            if chunk is None:
                if time.monotonic() - last_speech > silence_limit:
                    break
                continue
            if self._recognizer.AcceptWaveform(chunk):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    texts.append(text)
                    last_speech = time.monotonic()
            else:
                partial = json.loads(self._recognizer.PartialResult())
                if partial.get("partial", "").strip():
                    last_speech = time.monotonic()

        # Grab final segment
        final = json.loads(self._recognizer.FinalResult())
        final_text = final.get("text", "").strip()
        if final_text:
            texts.append(final_text)

        return " ".join(texts)

    def transcribe_buffer(self, audio: bytes) -> str:
        """Transcribe a single audio buffer."""
        if not self._ready or not self._recognizer:
            return ""
        self._recognizer.Reset()
        self._recognizer.AcceptWaveform(audio)
        result = json.loads(self._recognizer.FinalResult())
        return result.get("text", "").strip()
