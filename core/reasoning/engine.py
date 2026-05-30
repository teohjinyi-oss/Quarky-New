"""
Multi-Agent Reasoning: Engine

Orchestrates the full reasoning stack and exposes a single ``reason()`` entry
point. The pipeline:

  1. Dispatch agents in parallel        → reasoning paths (AgentOutput)
  2. Coherence Layer                    → contradiction flags (paths preserved)
  3. Belief State Layer                 → gradual confidence revision over turns
  4. Contextual Evaluation Layer        → task-dependent value selection
  5. Synthesizer                        → structured final response

The three independent signals (correctness, coherence, contextual value) are
reported separately on the ``ReasoningOutcome`` rather than collapsed into one
optimisation objective.
"""

from __future__ import annotations

from typing import Any

from core.reasoning.agents import ReasoningAgent
from core.reasoning.belief_state import BeliefStateTracker
from core.reasoning.coherence import CoherenceLayer
from core.reasoning.contextual_evaluation import ContextualEvaluator
from core.reasoning.critique import CritiqueLayer
from core.reasoning.dispatcher import MultiAgentDispatcher
from core.reasoning.synthesizer import synthesize
from core.reasoning.types import AgentOutput, ReasoningOutcome, TaskType


# Agents whose confidence represents truth validation (correctness signal).
_CORRECTNESS_AGENTS = ("logic", "evidence")


class MultiAgentReasoningEngine:
    """Top-level coordinator for the multi-agent reasoning system."""

    def __init__(
        self,
        agents: list[ReasoningAgent] | None = None,
        belief_tracker: BeliefStateTracker | None = None,
    ):
        try:
            from runtime.config.config import REASONING as _R
        except Exception:
            _R = {}
        self.dispatcher = MultiAgentDispatcher(
            agents, timeout=_R.get("agent_timeout", 5.0)
        )
        self.coherence = CoherenceLayer(
            overlap_threshold=_R.get("coherence_overlap_threshold", 0.5)
        )
        self.beliefs = belief_tracker or BeliefStateTracker(
            learning_rate=_R.get("belief_learning_rate", 0.3)
        )
        self.contextual = ContextualEvaluator(
            selection_threshold=_R.get("context_selection_threshold", 0.5)
        )
        # Phase 2: optional self-critique / verification layer.
        self.self_critique_enabled = _R.get("self_critique", True)
        self.critique = CritiqueLayer(
            verification_margin=_R.get("verification_margin", 0.15)
        )

    def reason(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        task_type: TaskType | None = None,
    ) -> ReasoningOutcome:
        """Run the full reasoning stack for a single query."""
        ctx = context or {}

        # 1. Parallel agent dispatch
        outputs = self.dispatcher.dispatch(query, ctx)

        # 2. Coherence — flag contradictions, keep all paths
        coherence = self.coherence.analyze(outputs)

        # 3. Belief state — gradual revision across turns
        touched = self.beliefs.update(outputs, coherence)

        # 4. Contextual evaluation — value-based selection
        contextual = self.contextual.evaluate(query, outputs, task_type)

        # 4b. Self-critique / verification (Phase 2) — annotates paths and, for
        # verification tasks, produces an explicit verdict. Never prunes paths.
        critique = None
        if self.self_critique_enabled:
            critique = self.critique.review(outputs, coherence, contextual.task_type)

        # 5. Synthesis — preserve multiple paths for mixed tasks
        response = synthesize(outputs, coherence, contextual)

        signals = {
            "correctness": round(self._correctness_signal(outputs), 4),
            "coherence": round(coherence.coherence_score, 4),
            "contextual_value": round(self._contextual_signal(contextual), 4),
        }

        return ReasoningOutcome(
            task_type=contextual.task_type,
            response=response,
            paths=outputs,
            coherence=coherence,
            contextual=contextual,
            belief_summary=touched,
            signals=signals,
            critique=critique,
            metadata={"agent_count": len(outputs)},
        )

    def _correctness_signal(self, outputs: list[AgentOutput]) -> float:
        """Truth-validation signal from the correctness-oriented agents."""
        relevant = [o.confidence for o in outputs if o.agent in _CORRECTNESS_AGENTS]
        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)

    def _contextual_signal(self, contextual) -> float:
        """Average contextual value of the selected paths."""
        selected = [s.total for s in contextual.scores if s.selected]
        if not selected:
            return 0.0
        return sum(selected) / len(selected)
