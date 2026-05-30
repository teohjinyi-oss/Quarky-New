"""
Benchmark Metrics

Each metric takes the relevant benchmark cases, runs Quarky's real subsystems,
and returns a normalised :class:`MetricResult` in the 0.0–1.0 range (higher is
better) plus the raw measurement for transparency.

The metrics deliberately exercise the *actual* shipping code paths
(``core.reasoning`` for task typing and signals) so the numbers reflect real
behaviour rather than a mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from benchmarks.dataset import (
    BenchmarkCase,
    IntentCase,
    ReasoningCase,
)


@dataclass
class MetricResult:
    """A single normalised metric measurement."""

    name: str
    score: float                     # 0.0–1.0, higher is better
    raw: float = 0.0                 # underlying measurement (units vary)
    unit: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.score = round(max(0.0, min(1.0, self.score)), 4)


def intent_accuracy(cases: list[BenchmarkCase]) -> MetricResult:
    """Fraction of intent cases whose detected task type matches expectation."""
    from core.reasoning.contextual_evaluation import detect_task_type

    intent_cases = [c for c in cases if isinstance(c, IntentCase)]
    if not intent_cases:
        return MetricResult("intent_accuracy", 0.0, unit="ratio")

    correct = 0
    misses: list[str] = []
    for case in intent_cases:
        detected = detect_task_type(case.query).value
        if detected == case.expected_task_type:
            correct += 1
        else:
            misses.append(f"{case.case_id}: expected {case.expected_task_type}, got {detected}")

    ratio = correct / len(intent_cases)
    return MetricResult(
        "intent_accuracy",
        score=ratio,
        raw=ratio,
        unit="ratio",
        detail={"total": len(intent_cases), "correct": correct, "misses": misses},
    )


def reasoning_signal_quality(cases: list[BenchmarkCase], engine: Any = None) -> MetricResult:
    """Fraction of reasoning cases whose signals clear their per-case minimums."""
    from core.reasoning.engine import MultiAgentReasoningEngine

    reasoning_cases = [c for c in cases if isinstance(c, ReasoningCase)]
    if not reasoning_cases:
        return MetricResult("reasoning_signal_quality", 0.0, unit="ratio")

    engine = engine or MultiAgentReasoningEngine()
    passed = 0
    failures: list[str] = []
    for case in reasoning_cases:
        outcome = engine.reason(case.query)
        ok = True
        for signal, minimum in case.min_signals.items():
            if outcome.signals.get(signal, 0.0) < minimum:
                ok = False
                failures.append(
                    f"{case.case_id}: {signal}={outcome.signals.get(signal, 0.0):.2f} < {minimum}"
                )
        if ok:
            passed += 1

    ratio = passed / len(reasoning_cases)
    return MetricResult(
        "reasoning_signal_quality",
        score=ratio,
        raw=ratio,
        unit="ratio",
        detail={"total": len(reasoning_cases), "passed": passed, "failures": failures},
    )


def latency_ms(cases: list[BenchmarkCase], engine: Any = None,
               target_ms: float = 250.0) -> MetricResult:
    """Average reasoning latency, normalised against a target budget.

    A run at or under ``target_ms`` scores 1.0; latency above the budget scales
    the score down linearly (never below 0.0).
    """
    from core.reasoning.engine import MultiAgentReasoningEngine

    reasoning_cases = [c for c in cases if isinstance(c, ReasoningCase)]
    if not reasoning_cases:
        return MetricResult("latency", 1.0, unit="ms")

    engine = engine or MultiAgentReasoningEngine()
    durations: list[float] = []
    for case in reasoning_cases:
        start = time.perf_counter()
        engine.reason(case.query)
        durations.append((time.perf_counter() - start) * 1000.0)

    avg = sum(durations) / len(durations)
    score = target_ms / avg if avg > target_ms else 1.0
    return MetricResult(
        "latency",
        score=score,
        raw=round(avg, 2),
        unit="ms",
        detail={"target_ms": target_ms, "samples": len(durations)},
    )
