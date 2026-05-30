"""
Multi-Agent Reasoning: Belief State Layer

Maintains a structured, evolving belief representation across turns. Beliefs are
keyed by a normalised proposition string. Confidence is revised *gradually*
(exponential moving update) rather than flipped in a single binary step, and is
pulled down when contradictions accumulate.
"""

from __future__ import annotations

import time

from core.nlp.tokenizer import keyword_tokens
from core.reasoning.types import AgentOutput, CoherenceReport, BeliefState


def _normalise(proposition: str) -> str:
    """Canonical key for a proposition (order-independent content words)."""
    return " ".join(sorted(set(keyword_tokens(proposition))))


class BeliefStateTracker:
    """Tracks and gradually revises beliefs over multiple reasoning turns."""

    def __init__(self, learning_rate: float = 0.3):
        # How much each new observation moves the stored confidence.
        self.learning_rate = learning_rate
        self._beliefs: dict[str, BeliefState] = {}

    # ── update ───────────────────────────────────────────────

    def update(
        self,
        outputs: list[AgentOutput],
        coherence: CoherenceReport | None = None,
    ) -> list[BeliefState]:
        """Fold a round of agent outputs into the belief store.

        Returns the belief states touched by this update.
        """
        contradicted_agents = set()
        if coherence is not None:
            for flag in coherence.contradictions:
                contradicted_agents.add(flag.agent_a)
                contradicted_agents.add(flag.agent_b)

        touched: dict[str, BeliefState] = {}
        for out in outputs:
            claims = out.claims or ([out.response] if out.response else [])
            for claim in claims:
                key = _normalise(claim)
                if not key:
                    continue
                state = self._beliefs.get(key)
                if state is None:
                    state = BeliefState(proposition=claim, confidence=0.5)
                    self._beliefs[key] = state

                is_contradicted = out.agent in contradicted_agents
                # Target confidence: the agent's own confidence, dampened if the
                # path is involved in a contradiction.
                target = out.confidence * (0.5 if is_contradicted else 1.0)
                state.confidence = self._revise(state.confidence, target)
                state.history.append(round(state.confidence, 4))
                if is_contradicted:
                    state.contradiction_count += 1
                else:
                    state.support_count += 1
                state.last_updated = time.time()
                touched[key] = state

        return list(touched.values())

    def _revise(self, current: float, target: float) -> float:
        """Gradual (not binary) confidence revision toward the new evidence."""
        revised = current + self.learning_rate * (target - current)
        return round(min(1.0, max(0.0, revised)), 4)

    # ── access ───────────────────────────────────────────────

    def get(self, proposition: str) -> BeliefState | None:
        """Look up the belief state for a proposition, if tracked."""
        return self._beliefs.get(_normalise(proposition))

    def all_beliefs(self) -> list[BeliefState]:
        """Return all tracked beliefs, most confident first."""
        return sorted(
            self._beliefs.values(), key=lambda b: b.confidence, reverse=True
        )

    def reset(self) -> None:
        """Clear all tracked beliefs (e.g. on a new session)."""
        self._beliefs.clear()
