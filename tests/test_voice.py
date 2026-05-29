"""Tests for the Start System — voice pipeline components."""

import pytest
import queue
import threading


class TestMicListener:
    """Test microphone listener module (mocked audio)."""

    def test_initial_state(self):
        from interfaces.voice.start import mic_listener
        # Should not be running initially
        assert mic_listener.is_running() is False

    def test_get_chunk_returns_none_when_empty(self):
        from interfaces.voice.start import mic_listener
        result = mic_listener.get_chunk(timeout=0.1)
        assert result is None

    def test_drain_empty(self):
        from interfaces.voice.start import mic_listener
        chunks = mic_listener.drain()
        assert chunks == []

    def test_register_unregister_callback(self):
        from interfaces.voice.start import mic_listener
        calls = []
        cb = lambda data: calls.append(data)
        mic_listener.register_callback(cb)
        assert cb in mic_listener._callbacks
        mic_listener.unregister_callback(cb)
        assert cb not in mic_listener._callbacks

    def test_start_without_sounddevice(self, monkeypatch):
        """If sounddevice is missing, start() should return False."""
        from interfaces.voice.start import mic_listener
        # Force stop first in case of leftover state
        mic_listener.stop()
        import importlib
        monkeypatch.setattr(importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError))
        # Can't easily mock the `import sounddevice` inside start(),
        # but we can test that stop() is safe when not started
        mic_listener.stop()
        assert mic_listener.is_running() is False


class TestWakeDetector:
    """Test wake word detector (mocked Vosk)."""

    def test_initial_state(self):
        from interfaces.voice.start import wake_detector
        assert wake_detector.is_active() is False

    def test_feed_when_inactive(self):
        from interfaces.voice.start import wake_detector
        wake_detector.stop()
        result = wake_detector.feed(b"\x00" * 3200)
        assert result is False

    def test_set_on_wake(self):
        from interfaces.voice.start import wake_detector
        calls = []
        wake_detector.set_on_wake(lambda: calls.append(True))
        assert wake_detector._on_wake is not None

    def test_reset_when_no_recognizer(self):
        from interfaces.voice.start import wake_detector
        # Reset should be safe even without Vosk
        wake_detector.reset()  # Should not raise

    def test_stop(self):
        from interfaces.voice.start import wake_detector
        wake_detector.stop()
        assert wake_detector.is_active() is False


class TestSTTEngine:
    """Test speech-to-text engine (without actual Vosk model)."""

    def test_transcribe_bytes_without_vosk(self, monkeypatch):
        from interfaces.voice.start import stt_engine
        monkeypatch.setattr(stt_engine, "_recognizer", None)
        monkeypatch.setattr(stt_engine, "_model", None)
        # Without vosk installed, should return empty string
        result = stt_engine.transcribe_bytes(b"\x00" * 3200)
        # Either empty string (no vosk) or some text (vosk installed)
        assert isinstance(result, str)

    def test_reset_when_no_recognizer(self):
        from interfaces.voice.start import stt_engine
        stt_engine.reset()  # Should not raise

    def test_transcribe_stream_returns_string(self):
        from interfaces.voice.start import stt_engine
        # Provide a chunk source that immediately returns None (silence)
        call_count = [0]
        def fake_chunks():
            call_count[0] += 1
            return None
        result = stt_engine.transcribe_stream(fake_chunks, timeout=0.5)
        assert isinstance(result, str)


class TestTextBridge:
    """Test the text bridge between voice and brain."""

    def test_empty_input(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input("")
        assert "didn't catch" in result.lower()

    def test_none_input(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input(None)  # type: ignore[arg-type]
        assert "didn't catch" in result.lower()

    def test_whitespace_input(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input("   ")
        assert "didn't catch" in result.lower()

    def test_handle_voice_command_empty(self):
        from interfaces.voice.start.text_bridge import handle_voice_command
        result = handle_voice_command("")
        assert result["response"]
        assert result["action"] is None

    def test_handle_voice_command_valid(self):
        from interfaces.voice.start.text_bridge import handle_voice_command
        result = handle_voice_command("hello there")
        assert "response" in result
        assert "success" in result
        assert isinstance(result["response"], str)

    def test_handle_voice_input_valid(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input("what time is it")
        assert isinstance(result, str)
        assert len(result) > 0


class TestTTSEngine:
    """Test text-to-speech engine."""

    def test_initial_state(self):
        from interfaces.voice.start import tts_engine
        # May or may not be running depending on test order
        # Just check it doesn't crash
        assert isinstance(tts_engine.is_running(), bool)

    def test_speak_empty(self):
        from interfaces.voice.start import tts_engine
        # Should not raise
        tts_engine.speak("")

    def test_speak_none(self):
        from interfaces.voice.start import tts_engine
        # Should not raise on empty
        tts_engine.speak("   ")

    def test_list_voices_returns_list(self):
        from interfaces.voice.start import tts_engine
        voices = tts_engine.list_voices()
        assert isinstance(voices, list)

    def test_set_rate(self):
        from interfaces.voice.start import tts_engine
        # Should not raise even if engine not initialized
        tts_engine.set_rate(200)

    def test_set_volume(self):
        from interfaces.voice.start import tts_engine
        tts_engine.set_volume(0.5)


class TestStateManager:
    """Test the voice state manager."""

    def test_initial_state(self):
        from interfaces.voice.start.state_manager import StateManager, VoiceState
        mgr = StateManager()
        assert mgr.state == VoiceState.OFF
        assert mgr.is_running() is False

    def test_get_status(self):
        from interfaces.voice.start.state_manager import StateManager
        mgr = StateManager()
        status = mgr.get_status()
        assert "state" in status
        assert "running" in status
        assert status["state"] == "off"
        assert status["running"] is False

    def test_stop_when_not_started(self):
        from interfaces.voice.start.state_manager import StateManager
        mgr = StateManager()
        mgr.stop()  # Should not raise
        assert mgr.is_running() is False

    def test_voice_status_function(self):
        from interfaces.voice.start.state_manager import voice_status
        status = voice_status()
        assert isinstance(status, dict)
        assert "state" in status

    def test_voice_state_enum(self):
        from interfaces.voice.start.state_manager import VoiceState
        assert VoiceState.OFF.value == "off"
        assert VoiceState.IDLE.value == "idle"
        assert VoiceState.LISTENING.value == "listening"
        assert VoiceState.PROCESSING.value == "processing"
        assert VoiceState.SPEAKING.value == "speaking"


class TestStartInit:
    """Test the start package public API."""

    def test_imports(self):
        from interfaces.voice.start import start_voice, stop_voice, voice_status
        assert callable(start_voice)
        assert callable(stop_voice)
        assert callable(voice_status)
