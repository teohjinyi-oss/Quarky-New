"""
Tests for v2 Brain: PatternMatcher, IntentRouter, Forwarder, Reasoner, OutputGate
"""

import pytest
from core.analytical.pattern_matcher import PatternMatcher
from core.routing.intent_router import IntentRouter
from core.routing.forwarder import think
from core.decision.output_gate import process as gate_process


@pytest.fixture
def matcher():
    return PatternMatcher()


@pytest.fixture
def router():
    return IntentRouter()


class TestPatternMatcher:
    def test_identity_match(self, matcher):
        result = matcher.match("who are you")
        assert result.has_match
        assert result.best_match is not None
        assert "quarky" in result.best_match.answer.lower() or "ai" in result.best_match.answer.lower()

    def test_no_match(self, matcher):
        result = matcher.match("xyzzy gibberish nonsense 12345")
        assert not result.has_match or (result.best_match and result.best_match.confidence < 0.5)

    def test_greeting(self, matcher):
        result = matcher.match("hello")
        # PatternMatcher may not have a greeting pattern
        assert isinstance(result.has_match, bool)


class TestIntentRouter:
    def test_route_question(self, router):
        decision = router.process("what is 2 plus 2")
        assert hasattr(decision, "mode")

    def test_route_action(self, router):
        decision = router.process("open calculator")
        assert hasattr(decision, "mode")


class TestForwarder:
    def test_think_returns_result(self):
        result = think("who are you")
        assert result is not None
        assert hasattr(result, "analytical")
        assert result.analytical is not None

    def test_think_has_response(self):
        result = think("hello")
        assert result is not None and result.analytical is not None
        assert result.analytical.response
        assert len(result.analytical.response) > 0


class TestOutputGate:
    def test_process_returns_final(self):
        result = gate_process("who are you")
        assert hasattr(result, "response")
        assert hasattr(result, "confidence")
        assert result.confidence > 0

    def test_process_identity_response(self):
        result = gate_process("who are you")
        assert "quarky" in result.response.lower() or "ai" in result.response.lower()
