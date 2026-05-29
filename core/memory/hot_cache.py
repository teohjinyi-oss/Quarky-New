"""
Memory v2: Hot Cache (Tier 1)

Fast in-memory JSON store for recent/active tokens.
The hot cache is the first place Quarky checks for information.
Backed by a JSON file for persistence between restarts.

Features:
- O(1) lookup by token ID
- Automatic capacity enforcement
- Token-value-aware eviction (lowest scores evicted first)
- JSON persistence
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

from core.intelligence.token import Token
from core.intelligence.scorer import TokenScorer


class HotCache:
    """
    Tier 1: Fast in-memory cache for recent and frequently accessed tokens.
    """

    def __init__(
        self,
        max_entries: int = 500,
        persist_path: Path | None = None,
        scorer: TokenScorer | None = None,
    ):
        self._data: dict[str, Token] = {}
        self._max = max_entries
        self._path = persist_path
        self._scorer = scorer or TokenScorer()
        self._lock = threading.Lock()
        self._dirty = False

        if self._path and self._path.exists():
            self._load()

    def get(self, token_id: str) -> Optional[Token]:
        """Get token by ID. Touches it (bumps recency/frequency)."""
        with self._lock:
            token = self._data.get(token_id)
            if token:
                token.touch()
                self._dirty = True
            return token

    def peek(self, token_id: str) -> Optional[Token]:
        """Get token without touching."""
        with self._lock:
            return self._data.get(token_id)

    def put(self, token: Token) -> None:
        """Store a token. Evicts lowest if over capacity."""
        with self._lock:
            self._data[token.id] = token
            self._dirty = True
            if len(self._data) > self._max:
                self._evict_lowest()

    def put_batch(self, tokens: list[Token]) -> None:
        """Store multiple tokens."""
        with self._lock:
            for t in tokens:
                self._data[t.id] = t
            self._dirty = True
            while len(self._data) > self._max:
                self._evict_lowest()

    def remove(self, token_id: str) -> Optional[Token]:
        """Remove a token from cache."""
        with self._lock:
            token = self._data.pop(token_id, None)
            if token:
                self._dirty = True
            return token

    def contains(self, token_id: str) -> bool:
        return token_id in self._data

    def search_text(self, query: str, top_k: int = 10) -> list[Token]:
        """Text search within cached tokens."""
        query_lower = query.lower()
        with self._lock:
            matches = [t for t in self._data.values() if query_lower in t.text.lower()]
        return self._scorer.rank(matches, top_k=top_k)

    def all_tokens(self) -> list[Token]:
        with self._lock:
            return list(self._data.values())

    @property
    def count(self) -> int:
        return len(self._data)

    # ── Persistence ─────────────────────────────────────────

    def save(self) -> None:
        """Persist cache to JSON file."""
        if not self._path or not self._dirty:
            return

        with self._lock:
            data = [t.to_dict() for t in self._data.values()]
            self._dirty = False

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load cache from JSON file."""
        if not self._path or not self._path.exists():
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                token = Token.from_dict(entry)
                self._data[token.id] = token
        except (json.JSONDecodeError, KeyError):
            pass  # corrupt file — start fresh

    def _evict_lowest(self) -> None:
        """Remove lowest-scored token. Must hold lock."""
        if not self._data:
            return
        tokens = list(self._data.values())
        scored = self._scorer.score_batch(tokens)
        if scored:
            worst_token, _ = scored[-1]
            del self._data[worst_token.id]

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._data.clear()
            self._dirty = True
