"""
Voice: Pipeline

Orchestrates the full voice pipeline v2:
  IDLE → LISTENING → PROCESSING → SPEAKING → IDLE

Integrates with the GUI via protocol messages and notification callbacks.
"""

from __future__ import annotations

import enum
import threading
import time
from typing import Any, Callable

from AppStudio.Voice.microphone import Microphone
from AppStudio.Voice.wake_detector import WakeDetector
from AppStudio.Voice.stt import STTEngine
from AppStudio.Voice.tts import TTSEngine
from AppStudio.Voice.session_guard import is_session_unlocked


class VoiceState(enum.Enum):
    OFF = "off"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class VoicePipeline:
    """
    Full voice pipeline v2.

    Changes from v1:
    - Class-based (no module-level state)
    - GUI state callback for JavaFX overlay
    - Pluggable process_fn for brain integration
    """

    def __init__(self):
        self._mic = Microphone()
        self._wake = WakeDetector()
        self._stt = STTEngine()
        self._tts = TTSEngine()
        self._state = VoiceState.OFF
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._watchdog_thread: threading.Thread | None = None
        self._last_error = ""
        self._tts_enabled = True  # talk-back mode on by default
        # Callbacks
        self._on_state_change: Callable[[VoiceState], None] | None = None
        self._process_fn: Callable[[str], str] | None = None

    # ── configuration ────────────────────────────────────────

    def set_process_fn(self, fn: Callable[[str], str]):
        """Set the function that processes transcribed text and returns a response."""
        self._process_fn = fn

    def set_state_callback(self, cb: Callable[[VoiceState], None]):
        """Register callback invoked on every state change (for GUI updates)."""
        self._on_state_change = cb

    # ── lifecycle ────────────────────────────────────────────

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self) -> bool:
        """Start the voice pipeline. Returns False if deps missing."""
        if self._running.is_set():
            return True

        if not self._mic.start():
            self._set_state(VoiceState.ERROR)
            self._last_error = "Microphone unavailable"
            return False

        if not self._stt.start():
            self._mic.stop()
            self._set_state(VoiceState.ERROR)
            self._last_error = "Vosk STT unavailable"
            return False

        if not self._wake.start():
            self._mic.stop()
            self._set_state(VoiceState.ERROR)
            self._last_error = "Wake detector unavailable"
            return False

        self._tts.start()
        self._wake.set_on_wake(self._on_wake)

        self._running.set()
        self._set_state(VoiceState.IDLE)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="voice-pipeline")
        self._thread.start()

        # Watchdog: auto-restart if pipeline thread dies unexpectedly
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="voice-watchdog"
        )
        self._watchdog_thread.start()

        self._speak("Quarky is listening.")
        return True

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=2.0)
            self._watchdog_thread = None
        self._wake.stop()
        self._mic.stop()
        self._tts.stop()
        self._set_state(VoiceState.OFF)

    def is_running(self) -> bool:
        return self._running.is_set()

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "running": self._running.is_set(),
            "mic": self._mic.is_running,
            "stt": self._stt.available,
            "tts": self._tts.is_running,
            "wake": self._wake.is_active,
            "error": self._last_error,
        }

    # ── state management ─────────────────────────────────────

    def _set_state(self, new_state: VoiceState):
        with self._lock:
            self._state = new_state
        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception:
                pass

    # ── silence / talk mode ─────────────────────────────────────

    @property
    def tts_enabled(self) -> bool:
        return self._tts_enabled

    def set_tts_enabled(self, enabled: bool):
        self._tts_enabled = enabled

    def _speak(self, text: str):
        """Speak text only if talk-back mode is on."""
        if self._tts_enabled:
            self._tts.speak(text)

    # ── wake callback ────────────────────────────────────────

    def _on_wake(self):
        with self._lock:
            if self._state == VoiceState.IDLE:
                self._state = VoiceState.LISTENING

    # ── main loop ────────────────────────────────────────────

    def _loop(self):
        while self._running.is_set():
            # PC-unlock gating: pause when session is locked
            if not is_session_unlocked():
                time.sleep(1.0)
                continue

            state = self._state
            if state == VoiceState.IDLE:
                chunk = self._mic.get_chunk(timeout=0.3)
                if chunk:
                    try:
                        self._wake.feed(chunk)
                    except Exception:
                        # Keep loop alive if wake detector is stopping/resetting.
                        time.sleep(0.02)
            elif state == VoiceState.LISTENING:
                self._do_listen()
            else:
                time.sleep(0.05)

    # ── watchdog ───────────────────────────────────────────

    def _watchdog_loop(self):
        """Monitor the pipeline thread; restart if it dies while we're running."""
        while self._running.is_set():
            time.sleep(3.0)
            if not self._running.is_set():
                break
            if self._thread is not None and not self._thread.is_alive():
                # Thread died unexpectedly — restart it
                self._thread = threading.Thread(
                    target=self._loop, daemon=True, name="voice-pipeline"
                )
                self._set_state(VoiceState.IDLE)
                self._thread.start()

    def _do_listen(self):
        self._set_state(VoiceState.LISTENING)
        self._mic.drain()
        self._speak("Yes?")
        time.sleep(0.4)

        text = self._stt.transcribe_stream(
            get_chunk=lambda: self._mic.get_chunk(timeout=0.5),
            timeout=30.0,
            silence_limit=2.0,
        )

        if text and self._process_fn:
            # Check for silence/talk mode toggle commands
            lower = text.lower().strip()
            if "silence mode" in lower:
                self._tts_enabled = False
                self._set_state(VoiceState.IDLE)
                self._wake.reset()
                return
            if "talk mode" in lower:
                self._tts_enabled = True
                self._speak("Talk mode is on.")
                self._set_state(VoiceState.IDLE)
                self._wake.reset()
                return

            self._set_state(VoiceState.PROCESSING)
            response = self._process_fn(text)
            self._set_state(VoiceState.SPEAKING)
            self._speak(response)
            time.sleep(0.5)
        elif text:
            self._set_state(VoiceState.SPEAKING)
            self._speak("I heard you but I have no brain connected.")
            time.sleep(0.5)

        self._set_state(VoiceState.IDLE)
        self._wake.reset()
