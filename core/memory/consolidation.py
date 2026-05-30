"""
Memory Consolidation & Proactive Recall (Phase 2)

Two capabilities that make Quarky's persistent memory feel *alive* — the
differentiator cloud assistants reset between sessions:

  - **Proactive recall** — given the current conversation context, surface
    relevant past memories *unprompted* (ranked by keyword overlap and recency),
    so Quarky can volunteer "last time you mentioned X" without being asked.
  - **Consolidation** — merge near-duplicate memories accumulated over time into
    a single consolidated entry, and produce short summaries, keeping the store
    compact and the signal high.

This module is deliberately dependency-free (standard library + Quarky's own
tokenizer). It operates on lightweight :class:`MemoryRecord` objects so it can
run offline and be unit-tested without ChromaDB / NetworkX. It can be layered on
top of :class:`core.memory.manager_v2.MemoryManagerV2` by adapting stored tokens
into ``MemoryRecord`` instances.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

from core.nlp.tokenizer import keyword_tokens


@dataclass
class MemoryRecord:
    """A minimal, tier-agnostic view of a stored memory."""

    record_id: str
    text: str
    timestamp: float = field(default_factory=time.time)
    score: float = 0.5                                # base relevance / importance
    metadata: dict = field(default_factory=dict)


@dataclass
class RecallHit:
    """A proactively recalled memory with its relevance breakdown."""

    record: MemoryRecord
    relevance: float
    overlap: float
    recency: float


@dataclass
class ConsolidationResult:
    """Outcome of a consolidation pass."""

    consolidated: list[MemoryRecord]
    merged_count: int
    groups: list[list[str]] = field(default_factory=list)  # ids merged together


def _tokens(text: str) -> set[str]:
    return set(keyword_tokens(text or ""))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class MemoryConsolidator:
    """Proactive recall and consolidation over a set of memory records."""

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        recency_half_life_s: float = 7 * 24 * 3600.0,
    ):
        # Overlap above this fraction marks two memories as the "same thing".
        self.similarity_threshold = similarity_threshold
        # Age (seconds) at which a memory's recency weight halves.
        self.recency_half_life_s = recency_half_life_s

    # ── proactive recall ──────────────────────────────────────
    def proactive_recall(
        self,
        context: str,
        memories: Iterable[MemoryRecord],
        top_k: int = 3,
        min_relevance: float = 0.1,
        now: float | None = None,
    ) -> list[RecallHit]:
        """Surface the most relevant past memories for the current context.

        Relevance blends keyword overlap with the query, recency, and the
        memory's own base score, so stale or off-topic memories don't intrude.
        """
        now = time.time() if now is None else now
        ctx_tokens = _tokens(context)
        if not ctx_tokens:
            return []

        hits: list[RecallHit] = []
        for mem in memories:
            overlap = _jaccard(ctx_tokens, _tokens(mem.text))
            if overlap <= 0.0:
                continue
            recency = self._recency_weight(mem.timestamp, now)
            relevance = round(
                0.6 * overlap + 0.25 * recency + 0.15 * mem.score, 4
            )
            if relevance >= min_relevance:
                hits.append(RecallHit(mem, relevance, round(overlap, 4),
                                      round(recency, 4)))

        hits.sort(key=lambda h: h.relevance, reverse=True)
        return hits[:top_k]

    # ── consolidation ─────────────────────────────────────────
    def consolidate(
        self, memories: Iterable[MemoryRecord]
    ) -> ConsolidationResult:
        """Merge near-duplicate memories into consolidated records.

        Records are grouped greedily by overlap. Each group becomes a single
        record that keeps the most recent timestamp, the max base score, and the
        longest (most informative) text as the representative.
        """
        records = list(memories)
        used: set[int] = set()
        consolidated: list[MemoryRecord] = []
        groups: list[list[str]] = []
        merged_count = 0

        for i, base in enumerate(records):
            if i in used:
                continue
            group = [base]
            base_tokens = _tokens(base.text)
            for j in range(i + 1, len(records)):
                if j in used:
                    continue
                if _jaccard(base_tokens, _tokens(records[j].text)) >= self.similarity_threshold:
                    group.append(records[j])
                    used.add(j)
            used.add(i)

            if len(group) == 1:
                consolidated.append(base)
                continue

            merged_count += len(group) - 1
            groups.append([r.record_id for r in group])
            consolidated.append(self._merge_group(group))

        return ConsolidationResult(
            consolidated=consolidated,
            merged_count=merged_count,
            groups=groups,
        )

    def summarize(self, memories: Iterable[MemoryRecord], max_items: int = 5) -> str:
        """Produce a short textual summary of the most important memories."""
        ranked = sorted(memories, key=lambda m: m.score, reverse=True)[:max_items]
        if not ranked:
            return "No memories to summarize."
        lines = [f"- {m.text.strip()}" for m in ranked if m.text.strip()]
        return "Key things I remember:\n" + "\n".join(lines)

    # ── helpers ───────────────────────────────────────────────
    def _recency_weight(self, timestamp: float, now: float) -> float:
        age = max(0.0, now - timestamp)
        # Exponential decay with the configured half-life.
        return 0.5 ** (age / self.recency_half_life_s)

    @staticmethod
    def _merge_group(group: list[MemoryRecord]) -> MemoryRecord:
        representative = max(group, key=lambda r: len(r.text or ""))
        return MemoryRecord(
            record_id=representative.record_id,
            text=representative.text,
            timestamp=max(r.timestamp for r in group),
            score=max(r.score for r in group),
            metadata={
                **representative.metadata,
                "consolidated_from": [r.record_id for r in group],
            },
        )
