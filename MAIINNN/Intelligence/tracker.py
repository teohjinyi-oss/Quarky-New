"""
Intelligence: Token Tracker

Manages the lifecycle of tokens — creation, updates, access tracking,
decay, and eviction. Acts as the central registry for all active tokens.

The tracker owns the in-memory token store. Memory systems persist
tokens to their respective backends; the tracker manages the hot set.
"""

from __future__ import annotations

import time
import threading
from typing import Optional

from MAIINNN.Intelligence.token import (
    Token,
    SpecificityTier,
    ConfirmationTier,
)
from MAIINNN.Intelligence.scorer import TokenScorer, ScoringWeights


class TokenTracker:
    """
    Central registry for active tokens.

    Responsibilities:
    - Create and register tokens
    - Track access patterns (touch on read)
    - Run periodic decay on importance
    - Identify eviction candidates
    - Provide ranked retrieval
    """

    def __init__(
        self,
        scorer: TokenScorer | None = None,
        max_tokens: int = 5000,
        decay_amount: float = 0.02,
        decay_interval_seconds: float = 300.0,
    ):
        self._tokens: dict[str, Token] = {}     # id → Token
        self._scorer = scorer or TokenScorer()
        self._max_tokens = max_tokens
        self._decay_amount = decay_amount
        self._decay_interval = decay_interval_seconds
        self._lock = threading.Lock()
        self._decay_timer: Optional[threading.Timer] = None
        self._running = False

    # ── Token CRUD ──────────────────────────────────────────

    def create(
        self,
        text: str,
        source: str = "user",
        importance: float = 0.5,
        specificity: SpecificityTier = SpecificityTier.GG,
        confirmation: ConfirmationTier = ConfirmationTier.UNVERIFIED,
        topic: str = "",
        tags: list[str] | None = None,
    ) -> Token:
        """Create and register a new token."""
        token = Token(
            text=text,
            source=source,
            importance=importance,
            specificity=specificity,
            confirmation=confirmation,
            topic=topic,
            tags=tags or [],
        )
        with self._lock:
            self._tokens[token.id] = token
            self._enforce_capacity()
        return token

    def register(self, token: Token) -> None:
        """Register an existing token (e.g., loaded from storage)."""
        with self._lock:
            self._tokens[token.id] = token

    def register_batch(self, tokens: list[Token]) -> None:
        """Register multiple tokens at once."""
        with self._lock:
            for t in tokens:
                self._tokens[t.id] = t

    def get(self, token_id: str) -> Optional[Token]:
        """Retrieve a token by ID. Records an access (touch)."""
        with self._lock:
            token = self._tokens.get(token_id)
            if token:
                token.touch()
            return token

    def peek(self, token_id: str) -> Optional[Token]:
        """Retrieve a token by ID WITHOUT recording an access."""
        with self._lock:
            return self._tokens.get(token_id)

    def remove(self, token_id: str) -> Optional[Token]:
        """Remove a token from the tracker."""
        with self._lock:
            return self._tokens.pop(token_id, None)

    def contains(self, token_id: str) -> bool:
        return token_id in self._tokens

    @property
    def count(self) -> int:
        return len(self._tokens)

    # ── Search & Ranking ────────────────────────────────────

    def search_text(self, query: str, top_k: int = 10) -> list[Token]:
        """
        Simple text search: tokens whose text contains the query.
        Results ranked by composite score.
        """
        query_lower = query.lower()
        with self._lock:
            matches = [t for t in self._tokens.values() if query_lower in t.text.lower()]
        return self._scorer.rank(matches, top_k=top_k)

    def search_topic(self, topic: str, top_k: int = 10) -> list[Token]:
        """Find tokens by topic, ranked by score."""
        topic_lower = topic.lower()
        with self._lock:
            matches = [t for t in self._tokens.values() if t.topic.lower() == topic_lower]
        return self._scorer.rank(matches, top_k=top_k)

    def search_tags(self, tags: list[str], top_k: int = 10) -> list[Token]:
        """Find tokens that have ANY of the given tags."""
        tag_set = {t.lower() for t in tags}
        with self._lock:
            matches = [
                t for t in self._tokens.values()
                if any(tag.lower() in tag_set for tag in t.tags)
            ]
        return self._scorer.rank(matches, top_k=top_k)

    def top_tokens(self, k: int = 20) -> list[Token]:
        """Return the top-k highest-scoring tokens overall."""
        with self._lock:
            all_tokens = list(self._tokens.values())
        return self._scorer.rank(all_tokens, top_k=k)

    def all_tokens(self) -> list[Token]:
        """Return all tokens (unordered). Use for batch operations."""
        with self._lock:
            return list(self._tokens.values())

    # ── Decay & Eviction ────────────────────────────────────

    def decay_pass(self) -> int:
        """
        Run one decay pass: reduce importance of all tokens slightly.
        User-confirmed tokens decay slower.
        Returns count of tokens decayed.
        """
        decayed = 0
        with self._lock:
            for token in self._tokens.values():
                amount = self._decay_amount
                # User-confirmed tokens decay at half rate
                if token.confirmation == ConfirmationTier.USER_CONFIRMED:
                    amount *= 0.5
                if token.importance > 0.0:
                    token.decay_importance(amount)
                    decayed += 1
        return decayed

    def evict(self, threshold: float = 0.10) -> list[Token]:
        """
        Remove tokens below the score threshold.
        Returns the evicted tokens (for persistence/logging).
        """
        with self._lock:
            all_tokens = list(self._tokens.values())

        candidates = self._scorer.eviction_candidates(all_tokens, threshold=threshold)

        evicted = []
        with self._lock:
            for token in candidates:
                if token.id in self._tokens:
                    del self._tokens[token.id]
                    evicted.append(token)
        return evicted

    def _enforce_capacity(self) -> None:
        """If over max capacity, evict lowest-scoring tokens. Must hold lock."""
        if len(self._tokens) <= self._max_tokens:
            return

        overage = len(self._tokens) - self._max_tokens
        all_tokens = list(self._tokens.values())
        scored = self._scorer.score_batch(all_tokens)

        # Remove lowest-scored tokens
        to_remove = scored[-overage:]
        for token, _ in to_remove:
            del self._tokens[token.id]

    # ── Background Decay Service ────────────────────────────

    def start_decay_service(self) -> None:
        """Start background periodic decay."""
        if self._running:
            return
        self._running = True
        self._schedule_decay()

    def stop_decay_service(self) -> None:
        """Stop background periodic decay."""
        self._running = False
        if self._decay_timer:
            self._decay_timer.cancel()
            self._decay_timer = None

    def _schedule_decay(self) -> None:
        if not self._running:
            return
        self._decay_timer = threading.Timer(self._decay_interval, self._decay_tick)
        self._decay_timer.daemon = True
        self._decay_timer.start()

    def _decay_tick(self) -> None:
        if not self._running:
            return
        self.decay_pass()
        self._schedule_decay()

    # ── Stats ───────────────────────────────────────────────

    def stats(self) -> dict:
        """Return tracker statistics for monitoring."""
        with self._lock:
            tokens = list(self._tokens.values())

        if not tokens:
            return {"count": 0, "avg_score": 0.0, "avg_importance": 0.0}

        scores = [self._scorer.score(t) for t in tokens]
        return {
            "count": len(tokens),
            "avg_score": round(sum(scores) / len(scores), 4),
            "avg_importance": round(sum(t.importance for t in tokens) / len(tokens), 4),
            "confirmed_count": sum(1 for t in tokens if t.confirmation == ConfirmationTier.USER_CONFIRMED),
            "topics": len({t.topic for t in tokens if t.topic}),
        }
