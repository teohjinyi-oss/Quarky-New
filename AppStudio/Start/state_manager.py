"""
Start System: State Manager

Orchestrates the full voice pipeline:
  IDLE (listening for wake word) → LISTENING (STT recording) → PROCESSING → SPEAKING → IDLE

Manages transitions between states, coordinates mic_listener, wake_detector,
stt_engine, text_bridge, and tts_engine.
"""

import enum
import threading
import time

from AppStudio.Start import mic_listener, wake_detector, stt_engine, text_bridge, tts_engine


class VoiceState(enum.Enum):
    """Voice pipeline states."""
    OFF = "off"
    IDLE = "idle"             # Waiting for wake word
    LISTENING = "listening"   # Recording user speech
    PROCESSING = "processing" # Thinking / running through brain
    SPEAKING = "speaking"     # TTS output
    ERROR = "error"


class StateManager:
    """
    Manages the voice pipeline lifecycle.

    Flow: IDLE → (wake word) → LISTENING → (silence) → PROCESSING → SPEAKING → IDLE
    """

    def __init__(self) -> None:
        self._state = VoiceState.OFF
        self._lock = threading.Lock()
        self._loop_thread: threading.Thread | None = None
        self._running = threading.Event()
        self._last_error: str = ""

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self) -> bool:
        """
        Start the full voice pipeline.
        Returns True if started, False if dependencies missing.
        """
        if self._running.is_set():
            return True

        # Start mic
        if not mic_listener.start():
            self._last_error = "Microphone unavailable (sounddevice not installed?)"
            self._state = VoiceState.ERROR
            return False

        # Start wake detector
        if not wake_detector.start():
            self._last_error = "Vosk model unavailable — download vosk-model-small-en-us"
            mic_listener.stop()
            self._state = VoiceState.ERROR
            return False

        # Start TTS
        tts_engine.start()

        # Wire wake word callback
        wake_detector.set_on_wake(self._on_wake_detected)

        # Start the main loop
        self._running.set()
        self._state = VoiceState.IDLE
        self._loop_thread = threading.Thread(
            target=self._main_loop, daemon=True, name="voice-state-manager"
        )
        self._loop_thread.start()

        # Announce readiness
        tts_engine.speak("Quarky is listening.")

        return True

    def stop(self) -> None:
        """Shut down the entire voice pipeline."""
        self._running.clear()
        wake_detector.stop()
        mic_listener.stop()
        tts_engine.stop()
        self._state = VoiceState.OFF
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=3.0)
            self._loop_thread = None

    def _on_wake_detected(self) -> None:
        """Called by wake_detector when the wake word is heard."""
        with self._lock:
            if self._state == VoiceState.IDLE:
                self._state = VoiceState.LISTENING

    def _main_loop(self) -> None:
        """
        Core voice loop — feeds audio to wake detector in IDLE,
        runs STT in LISTENING, processes in PROCESSING, speaks in SPEAKING.
        """
        while self._running.is_set():
            state = self._state

            if state == VoiceState.IDLE:
                self._do_idle()
            elif state == VoiceState.LISTENING:
                self._do_listening()
            elif state == VoiceState.PROCESSING:
                # Processing handled in _do_listening transition
                pass
            elif state == VoiceState.SPEAKING:
                # Speaking handled in _do_processing transition
                pass
            else:
                time.sleep(0.1)

    def _do_idle(self) -> None:
        """IDLE state: feed audio chunks to wake word detector."""
        chunk = mic_listener.get_chunk(timeout=0.3)
        if chunk is not None:
            wake_detector.feed(chunk)

    def _do_listening(self) -> None:
        """LISTENING state: run STT until silence, then process."""
        # Drain any leftover audio
        mic_listener.drain()

        # Give audible feedback
        tts_engine.speak("Yes?")
        # Brief pause for the TTS to finish
        time.sleep(0.5)

        # Transcribe from mic stream
        text = stt_engine.transcribe_stream(
            get_chunk_fn=lambda: mic_listener.get_chunk(timeout=0.5),
            timeout=30.0,  # Max 30 seconds of recording
        )

        if text:
            # Transition to PROCESSING
            with self._lock:
                self._state = VoiceState.PROCESSING

            # Process through Quarky's brain
            response = text_bridge.handle_voice_input(text)

            # Transition to SPEAKING
            with self._lock:
                self._state = VoiceState.SPEAKING

            tts_engine.speak(response)

            # Wait a bit for TTS to start processing
            time.sleep(0.5)
        else:
            # Nothing heard — back to idle
            pass

        # Back to IDLE
        with self._lock:
            self._state = VoiceState.IDLE
        wake_detector.reset()

    def is_running(self) -> bool:
        """Check if the voice pipeline is active."""
        return self._running.is_set()

    def get_status(self) -> dict:
        """Get the current status of the voice pipeline."""
        return {
            "state": self._state.value,
            "running": self._running.is_set(),
            "mic_active": mic_listener.is_running(),
            "wake_active": wake_detector.is_active(),
            "tts_active": tts_engine.is_running(),
            "last_error": self._last_error,
        }


# ─── Module-level singleton ─────────────────────────────────

_manager: StateManager | None = None


def get_manager() -> StateManager:
    """Get or create the global StateManager singleton."""
    global _manager
    if _manager is None:
        _manager = StateManager()
    return _manager


def start_voice() -> bool:
    """Start the voice pipeline. Returns True on success."""
    return get_manager().start()


def stop_voice() -> None:
    """Stop the voice pipeline."""
    get_manager().stop()


def voice_status() -> dict:
    """Get voice pipeline status."""
    return get_manager().get_status()
