"""
Memory v2: Importance Scorer

Scores memory entries for retrieval ranking and eviction decisions.
Wraps the intelligence TokenScorer with memory-specific boosts:
- Recency boost for hot cache items
- Graph connectivity boost (more edges = more important)
- Access pattern boost (frequently accessed = important)
- Confirmation tier bonus (USER_CONFIRMED > INFERRED > UNVERIFIED)
"""

from __future__ import annotations

from core.intelligence.token import Token, ConfirmationTier
from core.intelligence.scorer import TokenScorer, ScoringWeights


# Bonus added to base score based on confirmation tier
_CONFIRMATION_BONUS = {
    ConfirmationTier.USER_CONFIRMED: 0.15,
    ConfirmationTier.INFERRED: 0.0,
    ConfirmationTier.UNVERIFIED: -0.05,
}


class MemoryScorer:
    """
    Memory-specific scoring that wraps the core TokenScorer
    with additional memory-layer signals.
    """

    def __init__(self, base_scorer: TokenScorer | None = None):
        self._base = base_scorer or TokenScorer()

    def score(self, token: Token, graph_edges: int = 0) -> float:
        """
        Score a token for memory ranking.

        Args:
            token: The token to score
            graph_edges: Number of graph edges this token has (connectivity boost)
        """
        base_score = self._base.score(token)

        # Confirmation tier boost: user-confirmed > inferred
        conf_bonus = _CONFIRMATION_BONUS.get(
            getattr(token, "confirmation", ConfirmationTier.UNVERIFIED), 0.0
        )
        base_score = min(1.0, base_score + conf_bonus)

        # Graph connectivity boost: more connected = more important
        if graph_edges > 0:
            # Logarithmic boost, capped at 0.1 extra
            import math
            connectivity_boost = min(0.1, math.log1p(graph_edges) * 0.03)
            base_score = min(1.0, base_score + connectivity_boost)

        return round(base_score, 4)

    def rank_for_retrieval(self, tokens: list[Token], top_k: int = 10) -> list[Token]:
        """Rank tokens for retrieval — importance-first with confirmation bonus."""
        scored = [(t, self.score(t)) for t in tokens]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:top_k]]

    def rank_for_eviction(self, tokens: list[Token], count: int = 10) -> list[Token]:
        """Rank tokens for eviction (lowest value first)."""
        scored = self._base.score_batch(tokens)
        scored.reverse()
        return [t for t, _ in scored[:count]]
