"""
Tests for v2 Voice Pipeline (unit-level, no audio hardware needed)
"""

import pytest
from interfaces.voice.microphone import Microphone
from interfaces.voice.wake_detector import WakeDetector, WAKE_PHRASES
from interfaces.voice.stt import STTEngine
from interfaces.voice.tts import TTSEngine
from interfaces.voice.pipeline import VoicePipeline, VoiceState


class TestMicrophone:
    def test_init(self):
        mic = Microphone()
        assert not mic.is_running

    def test_get_chunk_timeout(self):
        mic = Microphone()
        # Without starting, get_chunk should timeout
        result = mic.get_chunk(timeout=0.1)
        assert result is None


class TestWakeDetector:
    def test_init(self):
        wd = WakeDetector()
        assert not wd.is_active

    def test_wake_phrases(self):
        assert "quarky" in WAKE_PHRASES
        assert "hey quarky" in WAKE_PHRASES


class TestSTTEngine:
    def test_init(self):
        stt = STTEngine()
        assert not stt._ready


class TestTTSEngine:
    def test_init(self):
        tts = TTSEngine()
        assert not tts.is_running


class TestVoicePipeline:
    def test_init_state(self):
        vp = VoicePipeline()
        assert vp.state == VoiceState.OFF
        assert not vp.is_running()

    def test_get_status(self):
        vp = VoicePipeline()
        status = vp.get_status()
        assert status["state"] == "off"
        assert not status["running"]

    def test_set_process_fn(self):
        vp = VoicePipeline()
        vp.set_process_fn(lambda x: f"echo: {x}")
        assert vp._process_fn is not None

    def test_set_state_callback(self):
        vp = VoicePipeline()
        states = []
        vp.set_state_callback(lambda s: states.append(s))
        assert vp._on_state_change is not None

    def test_stop_when_not_running_is_safe(self):
        vp = VoicePipeline()
        vp.stop()  # Should not raise even when never started
        assert vp.state == VoiceState.OFF


class TestWakeDetectorFeed:
    """Verify wake detection logic without real audio."""

    def test_feed_without_vosk_returns_None(self):
        """When Vosk is unavailable, feed() should return gracefully."""
        wd = WakeDetector()
        # _recognizer is None since start() was not called; feed should be silent
        wd.feed(b'\x00' * 3200)  # no-op, no exception

    def test_wake_callback_registered(self):
        wd = WakeDetector()
        fired = []
        wd.set_on_wake(lambda: fired.append(True))
        assert wd._on_wake is not None

    def test_is_wake_true_for_basic_phrase(self):
        wd = WakeDetector()
        assert wd._is_wake("hey quarky are you there")
        assert wd._is_wake("quarky")
        assert wd._is_wake("ok quarky this is a test")

    def test_is_wake_false_for_irrelevant(self):
        wd = WakeDetector()
        assert not wd._is_wake("hello computer")
        assert not wd._is_wake("open chrome")
        assert not wd._is_wake("")


class TestVoicePipelineWakeFlow:
    """Simulate wake → listening state transition without audio."""

    def test_on_wake_transitions_idle_to_listening(self):
        vp = VoicePipeline()
        # Manually set state to IDLE (simulating running pipeline)
        vp._state = VoiceState.IDLE
        vp._on_wake()
        assert vp._state == VoiceState.LISTENING

    def test_on_wake_ignored_if_not_idle(self):
        """Wake should not override LISTENING/PROCESSING state."""
        vp = VoicePipeline()
        vp._state = VoiceState.PROCESSING
        vp._on_wake()
        assert vp._state == VoiceState.PROCESSING  # unchanged


class TestBrowserConfirmationIntegration:
    """Regression — browser app launches must never silently auto-execute."""

    def test_resolve_chrome_requires_confirmation(self):
        from core.decision.action_resolver import resolve, _get_risk_level
        from core.decision.evaluator import EvalScores

        # Verify the risk level function itself
        risk = _get_risk_level("app_launch", "chrome", "open chrome")
        assert risk == "HIGH", "Chrome must be HIGH risk"

    def test_resolve_returns_high_risk_for_browsers(self):
        """All common browsers resolve to HIGH risk."""
        from core.decision.action_resolver import _get_risk_level
        for browser in ("chrome", "firefox", "edge", "brave", "opera", "browser"):
            risk = _get_risk_level("app_launch", browser, f"open {browser}")
            assert risk == "HIGH", f"{browser} should be HIGH risk"
