"""
Benchmark Runner

Wires the dataset, metrics and scorecard together into one ``run_benchmark()``
call. Reuses a single reasoning engine across metrics so a run is fast and the
numbers are internally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmarks.dataset import all_cases, default_dataset
from benchmarks.metrics import (
    MetricResult,
    intent_accuracy,
    latency_ms,
    reasoning_signal_quality,
)
from benchmarks.scorecard import REFERENCE_PROFILE, Scorecard


@dataclass
class BenchmarkRunner:
    """Runs the full benchmark suite and builds a scorecard."""

    dataset: dict[str, list] = None  # type: ignore[assignment]
    reference: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.dataset is None:
            self.dataset = default_dataset()
        if self.reference is None:
            self.reference = REFERENCE_PROFILE

    def run(self) -> Scorecard:
        """Execute every metric and return a populated scorecard."""
        cases = all_cases(self.dataset)

        # Share one engine so latency + quality measure the same instance.
        engine = None
        try:
            from core.reasoning.engine import MultiAgentReasoningEngine
            engine = MultiAgentReasoningEngine()
        except Exception:
            engine = None

        metrics: list[MetricResult] = [
            intent_accuracy(cases),
            reasoning_signal_quality(cases, engine=engine),
            latency_ms(cases, engine=engine),
        ]

        return Scorecard.from_metrics(
            metrics,
            reference=self.reference,
            metadata={"case_count": len(cases), "suites": list(self.dataset.keys())},
        )


def run_benchmark(
    dataset: dict[str, list] | None = None,
    reference: dict[str, float] | None = None,
) -> Scorecard:
    """Convenience entry point: run the default benchmark and return a scorecard."""
    return BenchmarkRunner(dataset=dataset, reference=reference).run()
