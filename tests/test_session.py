"""Tests for session tracking — history, replay, duplicate detection."""

import pytest
import time


class TestSession:
    """Test the Session class."""

    def test_create_session(self):
        from core.session.session import Session
        s = Session()
        assert s.turn_count == 0
        assert len(s.turns) == 0

    def test_add_turn(self):
        from core.session.session import Session
        s = Session()
        turn = s.add_turn("hello", "hi there", "analytical", confidence=0.8)
        assert turn.turn_number == 1
        assert turn.user_text == "hello"
        assert turn.response == "hi there"
        assert s.turn_count == 1

    def test_multiple_turns(self):
        from core.session.session import Session
        s = Session()
        s.add_turn("one", "resp one", "analytical")
        s.add_turn("two", "resp two", "creative")
        s.add_turn("three", "resp three", "merged")
        assert s.turn_count == 3
        assert len(s.turns) == 3

    def test_get_history(self):
        from core.session.session import Session
        s = Session()
        for i in range(10):
            s.add_turn(f"msg {i}", f"resp {i}", "analytical")
        history = s.get_history(count=5)
        assert len(history) == 5

    def test_search_history(self):
        from core.session.session import Session
        s = Session()
        s.add_turn("what is python", "a programming language", "analytical")
        s.add_turn("open chrome", "opening chrome", "analytical")
        results = s.get_history(search="python")
        assert len(results) == 1
        assert "python" in results[0].user_text

    def test_duplicate_detection(self):
        from core.session.session import Session
        s = Session()
        s.add_turn("hello quarky", "hi there", "analytical")
        s.add_turn("something else", "okay", "analytical")

        dup = s.check_duplicate("hello quarky")
        assert dup is not None
        assert dup.response == "hi there"

        no_dup = s.check_duplicate("never asked this")
        assert no_dup is None

    def test_format_replay(self):
        from core.session.session import Session
        s = Session()
        s.add_turn("hello", "hi", "analytical")
        replay = s.format_replay()
        assert "hello" in replay
        assert "hi" in replay

    def test_empty_replay(self):
        from core.session.session import Session
        s = Session()
        replay = s.format_replay()
        assert "no conversation" in replay.lower()

    def test_get_stats(self):
        from core.session.session import Session
        s = Session()
        s.add_turn("test", "response", "analytical", action_performed="opened chrome")
        stats = s.get_stats()
        assert stats["turn_count"] == 1
        assert stats["actions_performed"] == 1
        assert "uptime" in stats

    def test_recent_context(self):
        from core.session.session import Session
        s = Session()
        for i in range(10):
            s.add_turn(f"q{i}", f"a{i}", "analytical")
        ctx = s.get_recent_context(3)
        assert len(ctx) == 3
        assert ctx[-1]["user"] == "q9"


class TestSessionGlobal:
    """Test the global session functions."""

    def test_get_session(self):
        from core.session.session import get_session, Session
        s = get_session()
        assert isinstance(s, Session)

    def test_new_session(self):
        from core.session.session import new_session
        s = new_session()
        assert s.turn_count == 0

    def test_end_session(self):
        from core.session.session import get_session, end_session
        get_session().add_turn("test", "resp", "analytical")
        stats = end_session()
        assert "turn_count" in stats
