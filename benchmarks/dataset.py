"""
Benchmark Dataset

A small, fixed task set used to measure Quarky's behaviour over time. The set is
intentionally curated (not random) so scores are comparable across runs and
across versions. Each case carries an expected value so metrics can be computed
without any human in the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    """Base class for a single evaluation case."""

    case_id: str
    query: str
    category: str = "general"


@dataclass(frozen=True)
class IntentCase(BenchmarkCase):
    """A case that checks the detected task type / intent of a query."""

    expected_task_type: str = "explanation"


@dataclass(frozen=True)
class ReasoningCase(BenchmarkCase):
    """A case that checks the reasoning engine's signal quality.

    ``min_signals`` maps a signal name (correctness / coherence /
    contextual_value) to the minimum acceptable value for this query.
    """

    min_signals: dict[str, float] = field(default_factory=dict)


def default_dataset() -> dict[str, list[BenchmarkCase]]:
    """Return the fixed benchmark task set, grouped by suite name."""
    intent_cases: list[BenchmarkCase] = [
        IntentCase("intent-verify-1", "Is the sky blue?", "verification",
                   expected_task_type="verification"),
        IntentCase("intent-verify-2", "Confirm that 2 plus 2 equals 4.",
                   "verification", expected_task_type="verification"),
        IntentCase("intent-explore-1", "Imagine new uses for an old phone.",
                   "exploration", expected_task_type="exploration"),
        IntentCase("intent-explore-2", "Brainstorm names for a coffee shop.",
                   "exploration", expected_task_type="exploration"),
        IntentCase("intent-explain-1", "Why does ice float on water?",
                   "explanation", expected_task_type="explanation"),
        IntentCase("intent-explain-2", "Explain how a rainbow forms.",
                   "explanation", expected_task_type="explanation"),
    ]

    reasoning_cases: list[BenchmarkCase] = [
        ReasoningCase("reason-1", "Is water wet?", "verification",
                      min_signals={"coherence": 0.5}),
        ReasoningCase("reason-2", "Compare cats and dogs as pets.", "mixed",
                      min_signals={"coherence": 0.4}),
        ReasoningCase("reason-3", "Explain why the sun rises in the east.",
                      "explanation", min_signals={"coherence": 0.5}),
    ]

    return {
        "intent": intent_cases,
        "reasoning": reasoning_cases,
    }


def all_cases(dataset: dict[str, list[BenchmarkCase]] | None = None) -> list[BenchmarkCase]:
    """Flatten a dataset into a single ordered list of cases."""
    ds = dataset or default_dataset()
    flat: list[BenchmarkCase] = []
    for suite in ds.values():
        flat.extend(suite)
    return flat
