"""
Start System: Microphone Listener

Captures raw audio from the default microphone using sounddevice.
Provides a callback-driven stream that feeds audio chunks to consumers
(wake detector, STT engine).
"""

import threading
import queue
from typing import Callable

from runtime.config.config import START

_SAMPLE_RATE: int = START["sample_rate"]
_BLOCK_SIZE: int = int(_SAMPLE_RATE * 0.1)  # 100ms chunks

# Shared audio queue — wake detector / STT read from here
_audio_queue: queue.Queue = queue.Queue(maxsize=300)
_stream = None
_running = threading.Event()
_callbacks: list[Callable[[bytes], None]] = []


def _audio_callback(indata, frames, time_info, status) -> None:
    """sounddevice callback — pushes raw audio bytes to queue + callbacks."""
    raw = bytes(indata)
    try:
        _audio_queue.put_nowait(raw)
    except queue.Full:
        # Drop oldest to prevent lag
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            pass
        _audio_queue.put_nowait(raw)

    for cb in _callbacks:
        try:
            cb(raw)
        except Exception:
            pass


def start() -> bool:
    """
    Start the microphone stream.
    Returns True if started, False if already running or sounddevice unavailable.
    """
    global _stream
    if _running.is_set():
        return False

    try:
        import sounddevice as sd
    except ImportError:
        return False

    _stream = sd.RawInputStream(
        samplerate=_SAMPLE_RATE,
        blocksize=_BLOCK_SIZE,
        dtype="int16",
        channels=1,
        callback=_audio_callback,
    )
    _stream.start()
    _running.set()
    return True


def stop() -> None:
    """Stop the microphone stream."""
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
    _running.clear()
    # Drain the queue
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break


def is_running() -> bool:
    """Check if the mic stream is active."""
    return _running.is_set()


def get_chunk(timeout: float = 0.5) -> bytes | None:
    """
    Get the next audio chunk from the queue.
    Returns None on timeout.
    """
    try:
        return _audio_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def register_callback(cb: Callable[[bytes], None]) -> None:
    """Register a function to receive every audio chunk in real time."""
    if cb not in _callbacks:
        _callbacks.append(cb)


def unregister_callback(cb: Callable[[bytes], None]) -> None:
    """Remove a previously registered callback."""
    if cb in _callbacks:
        _callbacks.remove(cb)


def drain() -> list[bytes]:
    """Drain and return all pending audio chunks."""
    chunks: list[bytes] = []
    while not _audio_queue.empty():
        try:
            chunks.append(_audio_queue.get_nowait())
        except queue.Empty:
            break
    return chunks
