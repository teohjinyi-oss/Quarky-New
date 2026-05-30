"""
Multi-Agent Reasoning: Shared Types

Structured data passed between the reasoning layers. The design keeps three
signals independent rather than collapsing them into one score:

  - Correctness   (truth validation)        → AgentOutput.confidence (logic/evidence)
  - Coherence     (consistency checking)    → CoherenceReport
  - Contextual    (task-dependent value)    → ContextualEvaluation

Every layer consumes and/or produces one of the dataclasses below.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    """The kind of objective the current query serves."""
    VERIFICATION = "verification"   # check / confirm a fact → favour logic + evidence
    EXPLORATION = "exploration"     # generate hypotheses → favour creativity
    EXPLANATION = "explanation"     # explain / describe → balanced
    MIXED = "mixed"                 # ambiguous → preserve multiple paths


@dataclass
class AgentOutput:
    """
    A single reasoning path produced by one agent.

    Agents return structured reasoning rather than only a final string so the
    downstream layers can compare claims, assumptions and evidence.
    """
    agent: str                                          # "logic" | "creativity" | ...
    response: str = ""                                  # human-readable summary
    confidence: float = 0.0                             # 0.0–1.0 self-assessed
    claims: list[str] = field(default_factory=list)     # asserted statements
    assumptions: list[str] = field(default_factory=list)  # premises relied upon
    evidence: list[str] = field(default_factory=list)   # supporting references
    reasoning_trace: list[str] = field(default_factory=list)  # step-by-step trace
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class ContradictionFlag:
    """A detected disagreement between two agents."""
    agent_a: str
    agent_b: str
    kind: str                       # "claim" | "assumption"
    detail: str
    severity: float = 0.5           # 0.0 (minor) – 1.0 (direct contradiction)


@dataclass
class CoherenceReport:
    """Result of the Coherence Layer.

    Disagreement is flagged but NOT discarded — multiple valid perspectives are
    preserved so the contextual layer can decide what is useful.
    """
    contradictions: list[ContradictionFlag] = field(default_factory=list)
    preserved_paths: list[str] = field(default_factory=list)  # agents kept
    notes: list[str] = field(default_factory=list)

    @property
    def consistent(self) -> bool:
        """True when no contradictions were detected."""
        return not self.contradictions

    @property
    def coherence_score(self) -> float:
        """A 0.0–1.0 consistency signal (1.0 = fully coherent)."""
        if not self.contradictions:
            return 1.0
        penalty = sum(c.severity for c in self.contradictions)
        return max(0.0, 1.0 - penalty / max(1, len(self.contradictions)))


@dataclass
class BeliefState:
    """The evolving belief about a single proposition."""
    proposition: str
    confidence: float = 0.5
    support_count: int = 0
    contradiction_count: int = 0
    history: list[float] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


@dataclass
class ContextualScore:
    """Per-agent value-based score from the Contextual Evaluation Layer."""
    agent: str
    task_fit: float = 0.0           # how well the agent suits the task type
    usefulness: float = 0.0         # usefulness of this path for the objective
    downstream_value: float = 0.0   # contribution to downstream understanding
    selected: bool = False

    @property
    def total(self) -> float:
        """Combined contextual value (kept separate from correctness/coherence)."""
        return round(
            0.4 * self.task_fit + 0.35 * self.usefulness + 0.25 * self.downstream_value,
            4,
        )


@dataclass
class ContextualEvaluation:
    """Result of the Contextual Evaluation Layer."""
    task_type: TaskType
    profile: str                                        # routing policy applied
    scores: list[ContextualScore] = field(default_factory=list)
    prioritized_agents: list[str] = field(default_factory=list)


@dataclass
class ReasoningOutcome:
    """Final structured synthesis returned by the reasoning engine.

    The three independent signals are exposed explicitly so callers can reason
    about reliability and exploration separately.
    """
    task_type: TaskType
    response: str = ""
    paths: list[AgentOutput] = field(default_factory=list)
    coherence: CoherenceReport | None = None
    contextual: ContextualEvaluation | None = None
    belief_summary: list[BeliefState] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)  # correctness/coherence/contextual_value
    metadata: dict[str, Any] = field(default_factory=dict)
