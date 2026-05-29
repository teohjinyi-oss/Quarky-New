"""
Start System: Speech-to-Text Engine

Records audio after wake word detection and transcribes it using Vosk.
Stops recording after silence_timeout seconds of silence.
Returns the transcribed text.
"""

import json
import time
from typing import Any

from AppStudio.Config import START

_SAMPLE_RATE: int = START["sample_rate"]
_SILENCE_TIMEOUT: float = START["silence_timeout"]

_recognizer: Any = None
_model: Any = None


def _init_vosk() -> bool:
    """Lazy-load Vosk model + recognizer for full transcription."""
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


def transcribe_stream(get_chunk_fn, timeout: float | None = None) -> str:
    """
    Transcribe audio from a chunk-providing function.

    get_chunk_fn: callable that returns bytes or None (on timeout).
    timeout: overall max recording time in seconds (None = unlimited).

    Stops on silence_timeout seconds of no speech, or overall timeout.
    Returns the transcribed text (empty string on failure).
    """
    if not _init_vosk():
        return ""

    _recognizer.Reset()

    silence_start: float | None = None
    overall_start = time.time()
    has_speech = False

    while True:
        # Overall timeout check
        if timeout and (time.time() - overall_start) > timeout:
            break

        chunk = get_chunk_fn()
        if chunk is None:
            # No audio available — count as silence
            if silence_start is None:
                silence_start = time.time()
            if time.time() - silence_start >= _SILENCE_TIMEOUT:
                break
            continue

        accepted = _recognizer.AcceptWaveform(chunk)

        # Check if there's speech happening
        partial = json.loads(_recognizer.PartialResult())
        partial_text = partial.get("partial", "").strip()

        if partial_text:
            has_speech = True
            silence_start = None  # Reset silence timer
        else:
            if has_speech and silence_start is None:
                silence_start = time.time()
            if has_speech and silence_start and (time.time() - silence_start >= _SILENCE_TIMEOUT):
                break

        if accepted:
            result = json.loads(_recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                return text

    # Finalize remaining audio
    final = json.loads(_recognizer.FinalResult())
    return final.get("text", "").strip()


def transcribe_bytes(audio_data: bytes) -> str:
    """
    Transcribe a complete audio buffer (16-bit PCM, mono, 16kHz).
    Useful for testing or pre-recorded audio.
    """
    if not _init_vosk():
        return ""

    _recognizer.Reset()

    # Feed in chunks
    chunk_size = _SAMPLE_RATE * 2  # 1 second of 16-bit audio
    offset = 0
    while offset < len(audio_data):
        end = min(offset + chunk_size, len(audio_data))
        _recognizer.AcceptWaveform(audio_data[offset:end])
        offset = end

    final = json.loads(_recognizer.FinalResult())
    return final.get("text", "").strip()


def reset() -> None:
    """Reset the STT recognizer state."""
    if _recognizer is not None:
        _recognizer.Reset()
