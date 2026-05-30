"""
Quarky Benchmark Harness (Phase 0)

A repeatable, offline evaluation harness that turns "is Quarky better?" into
measurable numbers. It scores Quarky on a fixed task set and produces a
head-to-head *scorecard* against a reference profile so every later upgrade can
be judged against a baseline rather than by intuition.

Design goals:
  - Zero network, zero LLM — runs entirely on the local machine.
  - Deterministic — the same inputs always yield the same metrics.
  - Pure standard library — no heavy optional dependencies required.

Public API::

    from benchmarks import run_benchmark, Scorecard

    card = run_benchmark()
    print(card.render())
"""

from benchmarks.dataset import (
    BenchmarkCase,
    IntentCase,
    ReasoningCase,
    default_dataset,
)
from benchmarks.metrics import (
    MetricResult,
    intent_accuracy,
    latency_ms,
    reasoning_signal_quality,
)
from benchmarks.scorecard import Scorecard, ScorecardEntry, REFERENCE_PROFILE
from benchmarks.runner import BenchmarkRunner, run_benchmark

__all__ = [
    "BenchmarkCase",
    "IntentCase",
    "ReasoningCase",
    "default_dataset",
    "MetricResult",
    "intent_accuracy",
    "latency_ms",
    "reasoning_signal_quality",
    "Scorecard",
    "ScorecardEntry",
    "REFERENCE_PROFILE",
    "BenchmarkRunner",
    "run_benchmark",
]
