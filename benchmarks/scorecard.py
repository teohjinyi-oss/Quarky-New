"""
Benchmark Scorecard

Collects metric results into a single comparable artifact and renders a
head-to-head table against a *reference profile*.

The reference profile is **not** a claim about any specific competitor's real
numbers — it is a documented, honest yardstick representing the qualities a
strong general assistant is expected to have, so Quarky's progress can be
tracked against a fixed bar. Quarky's win condition is the *private/local
personal-assistant* category: the profile reflects that framing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from benchmarks.metrics import MetricResult


# A fixed yardstick. Values are deliberately conservative reference bars (0–1),
# documenting what "good" looks like for each measured capability. They are a
# target to beat, not a measurement of a third-party product.
REFERENCE_PROFILE: dict[str, float] = {
    "intent_accuracy": 0.85,
    "reasoning_signal_quality": 0.80,
    "latency": 0.70,
}


@dataclass
class ScorecardEntry:
    """A single metric compared against the reference bar."""

    metric: str
    quarky: float
    reference: float

    @property
    def delta(self) -> float:
        """Quarky minus the reference bar (positive = Quarky ahead)."""
        return round(self.quarky - self.reference, 4)

    @property
    def verdict(self) -> str:
        if self.delta > 0.001:
            return "ahead"
        if self.delta < -0.001:
            return "behind"
        return "tied"


@dataclass
class Scorecard:
    """The full result of a benchmark run."""

    entries: list[ScorecardEntry] = field(default_factory=list)
    metrics: list[MetricResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_metrics(
        cls,
        metrics: list[MetricResult],
        reference: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Scorecard":
        ref = reference or REFERENCE_PROFILE
        entries = [
            ScorecardEntry(m.name, m.score, ref.get(m.name, 0.0))
            for m in metrics
        ]
        return cls(entries=entries, metrics=list(metrics), metadata=metadata or {})

    @property
    def overall(self) -> float:
        """Mean of Quarky's normalised metric scores."""
        if not self.entries:
            return 0.0
        return round(sum(e.quarky for e in self.entries) / len(self.entries), 4)

    @property
    def reference_overall(self) -> float:
        """Mean of the reference bars for the measured metrics."""
        if not self.entries:
            return 0.0
        return round(sum(e.reference for e in self.entries) / len(self.entries), 4)

    def entry(self, metric: str) -> ScorecardEntry | None:
        for e in self.entries:
            if e.metric == metric:
                return e
        return None

    def render(self) -> str:
        """Human-readable scorecard table."""
        lines = [
            "Quarky Benchmark Scorecard",
            "=" * 52,
            f"{'metric':<26}{'quarky':>8}{'ref':>8}{'verdict':>10}",
            "-" * 52,
        ]
        for e in self.entries:
            lines.append(
                f"{e.metric:<26}{e.quarky:>8.2f}{e.reference:>8.2f}{e.verdict:>10}"
            )
        lines.append("-" * 52)
        lines.append(
            f"{'OVERALL':<26}{self.overall:>8.2f}{self.reference_overall:>8.2f}"
        )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable summary (for persistence / regression tracking)."""
        return {
            "overall": self.overall,
            "reference_overall": self.reference_overall,
            "entries": [
                {
                    "metric": e.metric,
                    "quarky": e.quarky,
                    "reference": e.reference,
                    "delta": e.delta,
                    "verdict": e.verdict,
                }
                for e in self.entries
            ],
            "metadata": self.metadata,
        }
