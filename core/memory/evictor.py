"""
Memory v2: Smart Evictor

Manages memory capacity by evicting lowest-value tokens.
Works across all three tiers with configurable strategies:
- Hot cache: evict when over max (fast, score-based)
- Vector store: evict old low-value entries periodically
- Graph store: prune disconnected low-value nodes
"""

from __future__ import annotations

import time
import threading
from typing import Optional

from core.intelligence.token import Token
from core.intelligence.scorer import TokenScorer


class Evictor:
    """
    Manages capacity across memory tiers by evicting low-value tokens.
    """

    def __init__(
        self,
        scorer: TokenScorer | None = None,
        check_interval: float = 600.0,
        batch_size: int = 50,
    ):
        self._scorer = scorer or TokenScorer()
        self._interval = check_interval
        self._batch_size = batch_size
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._on_evict_callbacks: list = []

    def evict_from_list(
        self,
        tokens: list[Token],
        max_keep: int,
    ) -> list[Token]:
        """
        Given a list of tokens and a capacity limit, return
        the tokens that should be evicted (lowest scored).
        """
        if len(tokens) <= max_keep:
            return []

        scored = self._scorer.score_batch(tokens)
        # Keep top max_keep, evict the rest
        to_evict = [t for t, _ in scored[max_keep:]]
        return to_evict

    def candidates(
        self,
        tokens: list[Token],
        threshold: float = 0.10,
    ) -> list[Token]:
        """Return tokens below the score threshold."""
        return self._scorer.eviction_candidates(tokens, threshold=threshold)

    def on_evict(self, callback) -> None:
        """Register a callback for eviction events."""
        self._on_evict_callbacks.append(callback)

    def start_periodic(self, evict_fn) -> None:
        """Start periodic eviction checks."""
        if self._running:
            return
        self._running = True
        self._schedule(evict_fn)

    def stop_periodic(self) -> None:
        """Stop periodic eviction."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule(self, evict_fn) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._tick, args=[evict_fn])
        self._timer.daemon = True
        self._timer.start()

    def _tick(self, evict_fn) -> None:
        if not self._running:
            return
        try:
            evicted = evict_fn()
            for cb in self._on_evict_callbacks:
                cb(evicted)
        except Exception:
            pass
        self._schedule(evict_fn)
