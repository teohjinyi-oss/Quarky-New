"""
Tests for v2 Session and Orchestrator
"""

import pytest
from core.session.session_v2 import SessionV2
from core.orchestrator import Orchestrator


class TestSessionV2:
    def test_add_turn(self):
        s = SessionV2()
        turn = s.add_turn("hello", "Hi there!", "analytical")
        assert turn.turn_number == 1
        assert s.turn_count == 1

    def test_get_history(self):
        s = SessionV2()
        s.add_turn("a", "b", "analytical")
        s.add_turn("c", "d", "creative")
        hist = s.get_history(count=10)
        assert len(hist) == 2

    def test_check_duplicate(self):
        s = SessionV2()
        s.add_turn("hello", "Hi!", "analytical")
        dup = s.check_duplicate("hello")
        assert dup is not None
        assert dup.user_text == "hello"

    def test_format_replay(self):
        s = SessionV2()
        s.add_turn("hi", "hello!", "analytical")
        replay = s.format_replay()
        assert "hi" in replay
        assert "hello!" in replay

    def test_get_stats(self):
        s = SessionV2()
        s.add_turn("test", "reply", "analytical")
        stats = s.get_stats()
        assert stats["turn_count"] == 1


class TestOrchestrator:
    def test_boot_all_green(self):
        o = Orchestrator()
        log = o.boot()
        greens = [l for l in log if l.startswith("[+]")]
        assert len(greens) >= 6  # at least intelligence, memory, brain, learning, session, habits

    def test_process_identity(self):
        o = Orchestrator()
        o.boot()
        response = o.process("who are you")
        assert "quarky" in response.lower() or "ai" in response.lower()

    def test_process_time(self):
        o = Orchestrator()
        o.boot()
        response = o.process("what time is it")
        assert ":" in response or "time" in response.lower() or "PM" in response or "AM" in response

    def test_session_tracking(self):
        o = Orchestrator()
        o.boot()
        o.process("hello")
        o.process("who are you")
        assert o.session.turn_count >= 2

    def test_process_fallback(self):
        o = Orchestrator()
        o.boot()
        response = o.process("xkcd quantum entanglement banana")
        assert isinstance(response, str)
        assert len(response) > 0
