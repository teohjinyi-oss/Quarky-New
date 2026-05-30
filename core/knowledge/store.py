"""
Local Knowledge Cache (Phase 3)

Closes part of the world-knowledge gap *without* the cloud. When Quarky learns a
fact (e.g. from a web search), it can cache it locally so the next time the same
question comes up it answers **offline** and **with a citation** — turning the
thin `web/`-only knowledge path into a growing, private knowledge base.

The retrieval is a lightweight, dependency-free BM25-ish keyword ranker over the
cached entries, so it runs anywhere and is fully deterministic for testing. A
heavier vector index can be layered behind the same :class:`KnowledgeStore` API
later without changing callers.

Persistence is plain JSON under the configured data directory, keeping with
Quarky's "everything on your machine" principle.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from core.nlp.tokenizer import keyword_tokens


@dataclass
class KnowledgeEntry:
    """A single cached fact with provenance for citation."""

    entry_id: str
    text: str
    source: str = "local"             # where the fact came from (URL, "user", ...)
    timestamp: float = field(default_factory=time.time)
    score: float = 1.0                # confidence / importance
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeHit:
    """A retrieved entry with its relevance and a ready-to-show citation."""

    entry: KnowledgeEntry
    relevance: float

    @property
    def citation(self) -> str:
        return f"[source: {self.entry.source}]"

    def cited_text(self) -> str:
        return f"{self.entry.text.strip()} {self.citation}"


class KnowledgeStore:
    """A persistent, offline, keyword-searchable knowledge cache."""

    def __init__(self, path: str | Path | None = None):
        self._entries: dict[str, KnowledgeEntry] = {}
        self.path = Path(path) if path else None
        if self.path and self.path.exists():
            self.load()

    # ── mutation ──────────────────────────────────────────────
    def add(
        self,
        text: str,
        source: str = "local",
        entry_id: str | None = None,
        score: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEntry:
        """Cache a fact. If ``entry_id`` collides, the entry is updated."""
        if not text or not text.strip():
            raise ValueError("Knowledge text must be non-empty.")
        eid = entry_id or self._make_id(text)
        entry = KnowledgeEntry(
            entry_id=eid,
            text=text.strip(),
            source=source,
            score=score,
            metadata=metadata or {},
        )
        self._entries[eid] = entry
        return entry

    def remove(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    def __len__(self) -> int:
        return len(self._entries)

    def all(self) -> list[KnowledgeEntry]:
        return list(self._entries.values())

    # ── retrieval ─────────────────────────────────────────────
    def search(self, query: str, top_k: int = 3,
               min_relevance: float = 0.0) -> list[KnowledgeHit]:
        """Rank cached entries against the query with a TF–IDF keyword score."""
        q_tokens = keyword_tokens(query)
        if not q_tokens or not self._entries:
            return []

        idf = self._idf()
        hits: list[KnowledgeHit] = []
        for entry in self._entries.values():
            doc_tokens = keyword_tokens(entry.text)
            if not doc_tokens:
                continue
            relevance = self._score(q_tokens, doc_tokens, idf)
            # Nudge by the entry's own confidence so trusted facts rank higher.
            relevance *= (0.75 + 0.25 * entry.score)
            if relevance > min_relevance:
                hits.append(KnowledgeHit(entry, round(relevance, 4)))

        hits.sort(key=lambda h: h.relevance, reverse=True)
        return hits[:top_k]

    def answer(self, query: str) -> str | None:
        """Return the best cached answer *with a citation*, or None if unknown."""
        hits = self.search(query, top_k=1)
        return hits[0].cited_text() if hits else None

    # ── persistence ───────────────────────────────────────────
    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("No path configured for KnowledgeStore.save().")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"entries": [asdict(e) for e in self._entries.values()]}
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self.path
        if target is None or not target.exists():
            return
        data = json.loads(target.read_text(encoding="utf-8"))
        self._entries = {
            e["entry_id"]: KnowledgeEntry(**e) for e in data.get("entries", [])
        }

    # ── helpers ───────────────────────────────────────────────
    def _idf(self) -> dict[str, float]:
        n = len(self._entries)
        df: dict[str, int] = {}
        for entry in self._entries.values():
            for tok in set(keyword_tokens(entry.text)):
                df[tok] = df.get(tok, 0) + 1
        return {
            tok: math.log(1 + n / (1 + count))
            for tok, count in df.items()
        }

    @staticmethod
    def _score(q_tokens: list[str], doc_tokens: list[str],
               idf: dict[str, float]) -> float:
        doc_set = set(doc_tokens)
        return sum(idf.get(tok, 0.0) for tok in set(q_tokens) if tok in doc_set)

    @staticmethod
    def _make_id(text: str) -> str:
        import hashlib
        # Non-security identifier; blake2b is fast and modern.
        return hashlib.blake2b(
            text.strip().lower().encode("utf-8"), digest_size=8
        ).hexdigest()
