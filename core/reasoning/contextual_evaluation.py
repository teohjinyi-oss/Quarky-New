"""
Multi-Agent Reasoning: Contextual Evaluation Layer (Value-Based Selection)

Instead of selecting outputs purely by confidence, this layer evaluates each
reasoning path by its *usefulness for the current objective*:

  - task_fit          how well the agent suits the detected task type
  - usefulness        richness of the path (claims / evidence produced)
  - downstream_value  contribution to downstream understanding

It first classifies the task type, then applies a routing policy profile:

  verification → prioritise logic + evidence
  exploration  → prioritise creativity (+ memory for analogies)
  explanation  → balanced
  mixed        → preserve multiple paths

This signal is kept independent of correctness and coherence.
"""

from __future__ import annotations

import re

from core.reasoning.types import (
    AgentOutput,
    ContextualScore,
    ContextualEvaluation,
    TaskType,
)

# Cue words that hint at the objective behind a query.
_VERIFY_CUES = re.compile(
    r"\b(is|are|does|did|was|were|verify|confirm|check|true|false|correct|prove)\b",
    re.I,
)
_EXPLORE_CUES = re.compile(
    r"\b(what if|imagine|brainstorm|idea|ideas|could|might|hypothes|explore|invent|suppose)\b",
    re.I,
)
_EXPLAIN_CUES = re.compile(
    r"\b(why|how|explain|describe|what is|define|meaning|tell me about)\b",
    re.I,
)

# Per-task agent affinities (task_fit weights).
_PROFILES: dict[TaskType, dict[str, float]] = {
    TaskType.VERIFICATION: {"logic": 1.0, "evidence": 1.0, "memory": 0.5, "creativity": 0.2},
    TaskType.EXPLORATION: {"creativity": 1.0, "memory": 0.6, "logic": 0.4, "evidence": 0.4},
    TaskType.EXPLANATION: {"logic": 0.8, "evidence": 0.8, "memory": 0.7, "creativity": 0.6},
    TaskType.MIXED: {"logic": 0.7, "evidence": 0.7, "creativity": 0.7, "memory": 0.7},
}

_PROFILE_NAME = {
    TaskType.VERIFICATION: "logic+evidence",
    TaskType.EXPLORATION: "creativity+exploration",
    TaskType.EXPLANATION: "balanced",
    TaskType.MIXED: "preserve-multi-path",
}


def detect_task_type(query: str) -> TaskType:
    """Classify the objective behind a query from lexical cues."""
    verify = bool(_VERIFY_CUES.search(query))
    explore = bool(_EXPLORE_CUES.search(query))
    explain = bool(_EXPLAIN_CUES.search(query))

    # Exploration combined with another objective is genuinely mixed.
    if explore and (verify or explain):
        return TaskType.MIXED
    if explore:
        return TaskType.EXPLORATION
    # Explanation cues ("why/how/explain") dominate bare verification cues
    # like "does" so "Why does ice float?" reads as an explanation.
    if explain:
        return TaskType.EXPLANATION
    if verify:
        return TaskType.VERIFICATION
    return TaskType.EXPLANATION


class ContextualEvaluator:
    """Scores reasoning paths by task-dependent value, not raw confidence."""

    def __init__(self, selection_threshold: float = 0.5):
        self.selection_threshold = selection_threshold

    def evaluate(
        self,
        query: str,
        outputs: list[AgentOutput],
        task_type: TaskType | None = None,
    ) -> ContextualEvaluation:
        task = task_type or detect_task_type(query)
        affinities = _PROFILES[task]

        scores: list[ContextualScore] = []
        for out in outputs:
            task_fit = affinities.get(out.agent, 0.3)
            usefulness = self._usefulness(out)
            downstream = self._downstream_value(out, task)
            score = ContextualScore(
                agent=out.agent,
                task_fit=round(task_fit, 4),
                usefulness=round(usefulness, 4),
                downstream_value=round(downstream, 4),
            )
            scores.append(score)

        # Rank by contextual value and mark the selected paths.
        scores.sort(key=lambda s: s.total, reverse=True)
        for s in scores:
            s.selected = s.total >= self.selection_threshold

        # For mixed tasks always keep at least the top two paths so multiple
        # perspectives survive into synthesis.
        if task == TaskType.MIXED:
            for s in scores[:2]:
                s.selected = True
        elif scores and not any(s.selected for s in scores):
            scores[0].selected = True

        return ContextualEvaluation(
            task_type=task,
            profile=_PROFILE_NAME[task],
            scores=scores,
            prioritized_agents=[s.agent for s in scores if s.selected],
        )

    def _usefulness(self, out: AgentOutput) -> float:
        """Richer paths (more claims / evidence) are more useful."""
        signal = 0.15 * len(out.claims) + 0.2 * len(out.evidence)
        return min(1.0, signal)

    def _downstream_value(self, out: AgentOutput, task: TaskType) -> float:
        """Contribution to downstream understanding for this task type."""
        base = 0.5 * out.confidence
        if task == TaskType.EXPLORATION and out.metadata.get("exploratory"):
            base += 0.3
        if task == TaskType.VERIFICATION and out.evidence:
            base += 0.3
        return min(1.0, base)
