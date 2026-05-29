"""
Tests for v2 Decision Engine: Evaluator, Merger, OutputGate
"""

import pytest
from core.decision.evaluator import evaluate, EvalScores
from core.decision.merger import merge, MergedResult
from core.decision.collector import DecisionContext, collect
from runtime.infrastructure.base import SpinalResult, BrainResult


def _make_context(text: str, response: str) -> DecisionContext:
    """Build a minimal DecisionContext for testing."""
    analytical = BrainResult(source="analytical", response=response, confidence=0.8)
    from core.memory.manager import SearchResult as V1SearchResult
    return DecisionContext(
        spinal=SpinalResult(input_text=text, input_intent="question", analytical=analytical),
        memory=V1SearchResult(),
        user_text=text,
        intent="question",
        analytical=analytical,
    )


class TestEvaluator:
    def test_evaluate_returns_scores(self):
        ctx = _make_context("who are you", "I am Quarky")
        scores = evaluate(ctx)
        assert isinstance(scores, EvalScores)

    def test_scores_in_range(self):
        ctx = _make_context("hello", "Hi there!")
        scores = evaluate(ctx)
        assert 0 <= scores.analytical_score <= 1


class TestMerger:
    def test_merge_returns_result(self):
        ctx = _make_context("hello", "Hi there!")
        scores = evaluate(ctx)
        result = merge(ctx, scores)
        assert isinstance(result, MergedResult)

    def test_merge_has_text(self):
        ctx = _make_context("who are you", "I am Quarky")
        scores = evaluate(ctx)
        result = merge(ctx, scores)
        assert result.response
        assert len(result.response) > 0
