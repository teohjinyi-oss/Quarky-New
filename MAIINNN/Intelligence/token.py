"""
Intelligence: Token Dataclass

A Token represents a scored piece of information or concept.
Multi-dimensional values drive all downstream decisions:
  - Memory: what to keep, what to evict
  - Retrieval: ranking results
  - Response: which brain path to use
  - Learning: what to prioritize absorbing

Specificity tiers (SS > GS > SG > GG) determine response routing.
Confirmation tiers track trust level of the information.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SpecificityTier(Enum):
    """
    How specific is the query × answer pair?
    Determines response routing priority.

    SS = Specific question, Specific answer → TOP priority (exact match)
    GS = General question, Specific answer → HIGH (good knowledge)
    SG = Specific question, General answer → MID (needs more learning)
    GG = General question, General answer → LOW (fallback)
    """
    SS = "specific_specific"
    GS = "general_specific"
    SG = "specific_general"
    GG = "general_general"


class ConfirmationTier(Enum):
    """
    How confirmed is this token's value?

    USER_CONFIRMED = User explicitly verified (highest trust)
    INFERRED       = System inferred from patterns/context
    UNVERIFIED     = Raw input, not yet validated
    """
    USER_CONFIRMED = "user_confirmed"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


# Trust multipliers for scoring
CONFIRMATION_WEIGHTS: dict[ConfirmationTier, float] = {
    ConfirmationTier.USER_CONFIRMED: 1.0,
    ConfirmationTier.INFERRED: 0.7,
    ConfirmationTier.UNVERIFIED: 0.4,
}

# Specificity priority multipliers
SPECIFICITY_WEIGHTS: dict[SpecificityTier, float] = {
    SpecificityTier.SS: 1.0,
    SpecificityTier.GS: 0.8,
    SpecificityTier.SG: 0.5,
    SpecificityTier.GG: 0.3,
}


@dataclass
class Token:
    """
    A scored unit of information in Quarky's intelligence system.

    Every concept, fact, query, or response fragment becomes a Token.
    The multi-dimensional scores drive ALL downstream decisions.
    """

    # ── Identity ──────────────────────────────────────────
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str = ""                          # the actual content

    # ── Value Dimensions ──────────────────────────────────
    specificity: SpecificityTier = SpecificityTier.GG
    confirmation: ConfirmationTier = ConfirmationTier.UNVERIFIED
    importance: float = 0.5                 # 0.0–1.0 how critical
    frequency: int = 1                      # access count
    recency: float = field(default_factory=time.time)  # last access timestamp
    context_relevance: float = 0.5          # 0.0–1.0 how relevant to current context

    # ── Embedding ─────────────────────────────────────────
    embedding: Optional[list[float]] = None  # sentence embedding vector

    # ── Metadata ──────────────────────────────────────────
    source: str = ""                        # where this came from (user, web, inference)
    topic: str = ""                         # topic cluster
    related_ids: list[str] = field(default_factory=list)  # links to related tokens
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    # ── Composite Score (computed, not stored) ────────────
    _composite: Optional[float] = field(default=None, repr=False)

    def touch(self) -> None:
        """Record an access: bump frequency and recency."""
        self.frequency += 1
        self.recency = time.time()
        self._composite = None  # invalidate cached score

    def confirm(self, tier: ConfirmationTier = ConfirmationTier.USER_CONFIRMED) -> None:
        """Upgrade confirmation tier."""
        self.confirmation = tier
        self._composite = None

    def set_specificity(self, tier: SpecificityTier) -> None:
        """Update specificity tier."""
        self.specificity = tier
        self._composite = None

    def boost_importance(self, amount: float = 0.1) -> None:
        """Increase importance, capped at 1.0."""
        self.importance = min(1.0, self.importance + amount)
        self._composite = None

    def decay_importance(self, amount: float = 0.05) -> None:
        """Decrease importance, floored at 0.0."""
        self.importance = max(0.0, self.importance - amount)
        self._composite = None

    def age_seconds(self) -> float:
        """Seconds since last access."""
        return time.time() - self.recency

    def age_hours(self) -> float:
        """Hours since last access."""
        return self.age_seconds() / 3600.0

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "id": self.id,
            "text": self.text,
            "specificity": self.specificity.value,
            "confirmation": self.confirmation.value,
            "importance": self.importance,
            "frequency": self.frequency,
            "recency": self.recency,
            "context_relevance": self.context_relevance,
            "source": self.source,
            "topic": self.topic,
            "related_ids": self.related_ids,
            "tags": self.tags,
            "created_at": self.created_at,
            # embedding excluded from JSON (stored in vector DB)
        }

    @classmethod
    def from_dict(cls, data: dict) -> Token:
        """Deserialize from dict."""
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            text=data.get("text", ""),
            specificity=SpecificityTier(data.get("specificity", "general_general")),
            confirmation=ConfirmationTier(data.get("confirmation", "unverified")),
            importance=data.get("importance", 0.5),
            frequency=data.get("frequency", 1),
            recency=data.get("recency", time.time()),
            context_relevance=data.get("context_relevance", 0.5),
            source=data.get("source", ""),
            topic=data.get("topic", ""),
            related_ids=data.get("related_ids", []),
            tags=data.get("tags", []),
            created_at=data.get("created_at", time.time()),
        )

    def __repr__(self) -> str:
        return (
            f"Token(id={self.id!r}, text={self.text[:40]!r}, "
            f"spec={self.specificity.name}, conf={self.confirmation.name}, "
            f"imp={self.importance:.2f}, freq={self.frequency})"
        )
