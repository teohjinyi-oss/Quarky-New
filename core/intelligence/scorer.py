"""
Intelligence: Token Scorer

Computes composite scores for tokens using configurable weighted dimensions.
The composite score is a single float (0.0–1.0) that represents the
overall value of a token. Used for:
  - Memory retrieval ranking
  - Eviction decisions (lowest scores get evicted)
  - Response routing priority
  - Learning priority (high-value gaps get filled first)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from core.intelligence.token import (
    Token,
    ConfirmationTier,
    SpecificityTier,
    CONFIRMATION_WEIGHTS,
    SPECIFICITY_WEIGHTS,
)


@dataclass(slots=True)
class ScoringWeights:
    """
    Configurable weights for each dimension in the composite score.
    All weights should sum to ~1.0 for a normalized output.
    """
    specificity: float = 0.25
    confirmation: float = 0.20
    importance: float = 0.20
    frequency: float = 0.10
    recency: float = 0.15
    context_relevance: float = 0.10

    def total(self) -> float:
        return (
            self.specificity + self.confirmation + self.importance
            + self.frequency + self.recency + self.context_relevance
        )


# ── Default weights ──────────────────────────────────────────
DEFAULT_WEIGHTS = ScoringWeights()


class TokenScorer:
    """
    Computes multi-factor composite scores for tokens.

    The score combines:
    - Specificity tier weight
    - Confirmation tier weight
    - Raw importance value
    - Frequency (log-scaled, diminishing returns)
    - Recency (exponential decay)
    - Context relevance

    All are weighted and summed into a single 0.0–1.0 composite.
    """

    def __init__(
        self,
        weights: ScoringWeights | None = None,
        recency_halflife_hours: float = 24.0,
        frequency_scale: float = 5.0,
    ):
        self.weights = weights or DEFAULT_WEIGHTS
        self.recency_halflife = recency_halflife_hours * 3600.0  # convert to seconds
        self.frequency_scale = frequency_scale

    def score(self, token: Token) -> float:
        """
        Compute composite score for a token.
        Returns a float in [0.0, 1.0].
        """
        w = self.weights

        # Specificity dimension
        spec_score = SPECIFICITY_WEIGHTS.get(token.specificity, 0.3)

        # Confirmation dimension
        conf_score = CONFIRMATION_WEIGHTS.get(token.confirmation, 0.4)

        # Importance (already 0.0–1.0)
        imp_score = token.importance

        # Frequency: log-scaled with diminishing returns
        # log(1 + freq) / log(1 + scale) → capped at 1.0
        freq_score = min(1.0, math.log1p(token.frequency) / math.log1p(self.frequency_scale))

        # Recency: exponential decay based on halflife
        age = time.time() - token.recency
        recency_score = math.exp(-0.693 * age / self.recency_halflife) if self.recency_halflife > 0 else 0.0

        # Context relevance (already 0.0–1.0)
        ctx_score = token.context_relevance

        # Weighted sum
        total = w.total()
        if total <= 0:
            return 0.0

        composite = (
            w.specificity * spec_score
            + w.confirmation * conf_score
            + w.importance * imp_score
            + w.frequency * freq_score
            + w.recency * recency_score
            + w.context_relevance * ctx_score
        ) / total

        # Cache on token
        token._composite = round(composite, 4)
        return token._composite

    def score_batch(self, tokens: list[Token]) -> list[tuple[Token, float]]:
        """Score multiple tokens and return sorted (highest first)."""
        scored = [(t, self.score(t)) for t in tokens]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def rank(self, tokens: list[Token], top_k: int = 10) -> list[Token]:
        """Return top-k tokens by composite score."""
        scored = self.score_batch(tokens)
        return [t for t, _ in scored[:top_k]]

    def eviction_candidates(self, tokens: list[Token], threshold: float = 0.15) -> list[Token]:
        """Return tokens with composite score below threshold (eviction candidates)."""
        return [t for t in tokens if self.score(t) < threshold]

    def dimension_breakdown(self, token: Token) -> dict[str, float]:
        """
        Return per-dimension weighted contributions for debugging/UI.
        Shows exactly why a token scored what it scored.
        """
        w = self.weights
        total = w.total()
        if total <= 0:
            return {}

        age = time.time() - token.recency
        recency_raw = math.exp(-0.693 * age / self.recency_halflife) if self.recency_halflife > 0 else 0.0

        return {
            "specificity": round(w.specificity * SPECIFICITY_WEIGHTS.get(token.specificity, 0.3) / total, 4),
            "confirmation": round(w.confirmation * CONFIRMATION_WEIGHTS.get(token.confirmation, 0.4) / total, 4),
            "importance": round(w.importance * token.importance / total, 4),
            "frequency": round(w.frequency * min(1.0, math.log1p(token.frequency) / math.log1p(self.frequency_scale)) / total, 4),
            "recency": round(w.recency * recency_raw / total, 4),
            "context_relevance": round(w.context_relevance * token.context_relevance / total, 4),
        }
