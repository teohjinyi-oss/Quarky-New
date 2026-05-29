"""
Memory v2: Token-Value-Aware Decay

Periodic decay reduces importance of tokens over time.
User-confirmed tokens decay slower. High-frequency tokens resist decay.
This ensures stale information naturally falls off.
"""

from __future__ import annotations

import time
import threading
from typing import Optional

from MAIINNN.Intelligence.token import Token, ConfirmationTier


class DecayEngine:
    """
    Runs periodic decay on token importance values.
    Confirmation tier and frequency affect decay rate.
    """

    def __init__(
        self,
        base_decay: float = 0.02,
        interval_seconds: float = 300.0,
    ):
        self._base_decay = base_decay
        self._interval = interval_seconds
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def decay_token(self, token: Token) -> float:
        """
        Apply decay to a single token.
        Returns the amount decayed.
        """
        rate = self._base_decay

        # User-confirmed tokens decay at 50% rate
        if token.confirmation == ConfirmationTier.USER_CONFIRMED:
            rate *= 0.5

        # High-frequency tokens decay slower (25% reduction per 10 accesses)
        if token.frequency > 10:
            rate *= 0.75

        if token.importance > 0:
            old = token.importance
            token.decay_importance(rate)
            return old - token.importance
        return 0.0

    def decay_batch(self, tokens: list[Token]) -> int:
        """Apply decay to a batch of tokens. Returns count decayed."""
        decayed = 0
        for token in tokens:
            if self.decay_token(token) > 0:
                decayed += 1
        return decayed

    def start(self, get_tokens_fn) -> None:
        """Start periodic decay service."""
        if self._running:
            return
        self._running = True
        self._schedule(get_tokens_fn)

    def stop(self) -> None:
        """Stop periodic decay."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule(self, get_tokens_fn) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._tick, args=[get_tokens_fn])
        self._timer.daemon = True
        self._timer.start()

    def _tick(self, get_tokens_fn) -> None:
        if not self._running:
            return
        try:
            tokens = get_tokens_fn()
            self.decay_batch(tokens)
        except Exception:
            pass
        self._schedule(get_tokens_fn)
