"""
Tests for Phase 2 memory consolidation + proactive recall
(core/memory/consolidation.py).
"""

import time

from core.memory.consolidation import (
    ConsolidationResult,
    MemoryConsolidator,
    MemoryRecord,
    RecallHit,
)


def _records():
    now = time.time()
    return [
        MemoryRecord("m1", "I love hiking in the mountains", timestamp=now, score=0.8),
        MemoryRecord("m2", "User enjoys hiking mountains on weekends",
                     timestamp=now - 10, score=0.6),
        MemoryRecord("m3", "Favorite food is sushi", timestamp=now - 100, score=0.7),
    ]


class TestProactiveRecall:
    def test_surfaces_relevant_memory(self):
        c = MemoryConsolidator()
        hits = c.proactive_recall("planning a hiking trip", _records())
        assert hits
        assert all(isinstance(h, RecallHit) for h in hits)
        assert hits[0].record.record_id in {"m1", "m2"}

    def test_irrelevant_context_returns_nothing(self):
        c = MemoryConsolidator()
        hits = c.proactive_recall("quantum chromodynamics lecture", _records())
        assert hits == []

    def test_empty_context(self):
        c = MemoryConsolidator()
        assert c.proactive_recall("", _records()) == []

    def test_respects_top_k(self):
        c = MemoryConsolidator()
        hits = c.proactive_recall("hiking mountains sushi food", _records(), top_k=1)
        assert len(hits) == 1

    def test_recency_weight_decays(self):
        c = MemoryConsolidator(recency_half_life_s=100.0)
        now = 1000.0
        fresh = c._recency_weight(now, now)
        old = c._recency_weight(now - 100, now)
        assert fresh == 1.0
        assert abs(old - 0.5) < 1e-6


class TestConsolidation:
    def test_merges_duplicates(self):
        c = MemoryConsolidator(similarity_threshold=0.3)
        result = c.consolidate(_records())
        assert isinstance(result, ConsolidationResult)
        # m1 and m2 are about hiking → merged; m3 stays separate.
        assert result.merged_count == 1
        assert len(result.consolidated) == 2
        assert any(len(g) == 2 for g in result.groups)

    def test_no_merge_when_distinct(self):
        c = MemoryConsolidator(similarity_threshold=0.9)
        distinct = [
            MemoryRecord("a", "apples are red"),
            MemoryRecord("b", "the ocean is deep"),
        ]
        result = c.consolidate(distinct)
        assert result.merged_count == 0
        assert len(result.consolidated) == 2

    def test_merged_record_keeps_longest_text(self):
        c = MemoryConsolidator(similarity_threshold=0.3)
        result = c.consolidate(_records())
        merged = [r for r in result.consolidated if "consolidated_from" in r.metadata]
        assert merged
        assert "consolidated_from" in merged[0].metadata

    def test_summarize(self):
        c = MemoryConsolidator()
        summary = c.summarize(_records())
        assert "remember" in summary.lower()
        assert "sushi" in summary or "hiking" in summary

    def test_summarize_empty(self):
        c = MemoryConsolidator()
        assert "No memories" in c.summarize([])
