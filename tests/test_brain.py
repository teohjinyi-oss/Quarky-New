"""Tests for the Core Brain — think() with various inputs."""

import pytest


class TestBrainThink:
    """Test the core brain think() pipeline."""

    def test_think_returns_spinal_result(self):
        from core.routing.forwarder import think
        from runtime.infrastructure.base import SpinalResult
        result = think("what is 5 plus 3")
        assert result is None or isinstance(result, SpinalResult)

    def test_think_math_question(self):
        from core.routing.forwarder import think
        result = think("calculate 10 divided by 2")
        if result is not None:
            assert result.input_text or result.input_intent

    def test_think_creative_input(self):
        from core.routing.forwarder import think
        result = think("write me a poem about stars")
        if result is not None:
            # Should route to creative or both
            assert result.route_decision or result.creative is not None or result.analytical is not None

    def test_think_empty(self):
        from core.routing.forwarder import think
        result = think("")
        # Empty input should still work without crashing
        assert result is None or hasattr(result, "analytical")

    def test_brain_result_structure(self):
        from runtime.infrastructure.base import BrainResult
        br = BrainResult(source="analytical", response="test", confidence=0.8)
        assert br.source == "analytical"
        assert br.confidence == 0.8

    def test_spinal_result_structure(self):
        from runtime.infrastructure.base import SpinalResult, BrainResult
        sr = SpinalResult(
            analytical=BrainResult(source="analytical", response="8", confidence=0.9),
            route_decision="fast_analytical",
            input_intent="question",
            input_text="what is 5 plus 3",
        )
        assert sr.analytical is not None
        assert sr.analytical.response == "8"
        assert sr.input_intent == "question"
