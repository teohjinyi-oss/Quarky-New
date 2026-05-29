"""
Start System: Text-to-Speech Engine

Speaks Quarky's responses aloud using pyttsx3.
Runs on a dedicated thread to avoid blocking the main loop.
Supports voice selection, rate, and volume control.
"""

import threading
import queue

_engine = None
_tts_queue: queue.Queue[str | None] = queue.Queue()
_worker_thread: threading.Thread | None = None
_running = threading.Event()


def _init_engine():
    """Lazy-initialize the pyttsx3 engine."""
    global _engine
    if _engine is not None:
        return True

    try:
        import pyttsx3
    except ImportError:
        return False

    _engine = pyttsx3.init()

    # Set default properties
    _engine.setProperty("rate", 175)     # words per minute
    _engine.setProperty("volume", 0.9)   # 0.0 to 1.0

    # Pick a voice (prefer female if available, fall back to first)
    voices = _engine.getProperty("voices")
    if voices:
        # Try to find a female English voice
        for v in voices:  # type: ignore[union-attr]
            if "female" in (v.name or "").lower() or "zira" in (v.id or "").lower():
                _engine.setProperty("voice", v.id)
                break

    return True


def _worker() -> None:
    """Background thread that processes the TTS queue."""
    while _running.is_set():
        try:
            text = _tts_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if text is None:
            break

        if _engine is not None:
            try:
                _engine.say(text)
                _engine.runAndWait()
            except Exception:
                pass


def start() -> bool:
    """
    Start the TTS engine and background worker.
    Returns True if started, False if pyttsx3 unavailable.
    """
    global _worker_thread

    if _running.is_set():
        return True

    if not _init_engine():
        return False

    _running.set()
    _worker_thread = threading.Thread(target=_worker, daemon=True, name="tts-worker")
    _worker_thread.start()
    return True


def stop() -> None:
    """Stop the TTS engine and worker thread."""
    global _worker_thread
    _running.clear()
    # Signal worker to exit
    try:
        _tts_queue.put_nowait(None)
    except queue.Full:
        pass
    if _worker_thread is not None:
        _worker_thread.join(timeout=3.0)
        _worker_thread = None
    # Drain remaining
    while not _tts_queue.empty():
        try:
            _tts_queue.get_nowait()
        except queue.Empty:
            break


def speak(text: str) -> None:
    """
    Queue text for speech.
    Non-blocking — returns immediately, speech happens in background.
    """
    if not text or not text.strip():
        return
    if not _running.is_set():
        start()
    _tts_queue.put(text.strip())


def speak_sync(text: str) -> None:
    """Speak text synchronously (blocks until done)."""
    if not text or not text.strip():
        return
    if not _init_engine():
        return
    if _engine is not None:
        _engine.say(text.strip())
        _engine.runAndWait()


def is_running() -> bool:
    """Check if the TTS engine is active."""
    return _running.is_set()


def set_rate(wpm: int) -> None:
    """Set speech rate in words per minute."""
    if _engine is not None:
        _engine.setProperty("rate", max(50, min(400, wpm)))


def set_volume(level: float) -> None:
    """Set volume (0.0 to 1.0)."""
    if _engine is not None:
        _engine.setProperty("volume", max(0.0, min(1.0, level)))


def list_voices() -> list[dict]:
    """Return available voice names and IDs."""
    if not _init_engine():
        return []
    if _engine is None:
        return []
    voices = _engine.getProperty("voices")
    return [{"id": v.id, "name": v.name} for v in (voices or [])]  # type: ignore[union-attr]


def set_voice(voice_id: str) -> bool:
    """Set the TTS voice by ID. Returns True on success."""
    if _engine is None:
        return False
    try:
        _engine.setProperty("voice", voice_id)
        return True
    except Exception:
        return False
