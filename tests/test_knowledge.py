"""
Tests for the Phase 3 local knowledge cache (core/knowledge/).
"""

import pytest

from core.knowledge import KnowledgeEntry, KnowledgeStore


@pytest.fixture
def store():
    kb = KnowledgeStore()
    kb.add("The capital of France is Paris.", source="wikipedia")
    kb.add("Water boils at 100 degrees Celsius at sea level.", source="textbook")
    kb.add("The Python language was created by Guido van Rossum.", source="docs")
    return kb


class TestStore:
    def test_add_and_len(self, store):
        assert len(store) == 3

    def test_add_rejects_empty(self, store):
        with pytest.raises(ValueError):
            store.add("   ")

    def test_add_dedupes_by_content(self):
        kb = KnowledgeStore()
        kb.add("same fact")
        kb.add("same fact")
        assert len(kb) == 1

    def test_remove(self, store):
        entry = store.all()[0]
        assert store.remove(entry.entry_id)
        assert len(store) == 2


class TestRetrieval:
    def test_search_finds_relevant(self, store):
        hits = store.search("What is the capital of France?")
        assert hits
        assert "Paris" in hits[0].entry.text

    def test_search_ranks_correct_entry_first(self, store):
        hits = store.search("who created python language")
        assert "Guido" in hits[0].entry.text

    def test_answer_includes_citation(self, store):
        ans = store.answer("capital of France")
        assert "Paris" in ans
        assert "[source: wikipedia]" in ans

    def test_answer_unknown_returns_none(self, store):
        assert store.answer("how do black holes evaporate") is None

    def test_empty_query(self, store):
        assert store.search("") == []

    def test_score_boosts_high_confidence(self):
        kb = KnowledgeStore()
        kb.add("alpha beta gamma fact", score=0.1, entry_id="low")
        kb.add("alpha beta gamma fact too", score=1.0, entry_id="high")
        hits = kb.search("alpha beta gamma")
        assert hits[0].entry.entry_id == "high"


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path, store):
        path = tmp_path / "kb.json"
        store.save(path)
        assert path.exists()

        reloaded = KnowledgeStore(path)
        assert len(reloaded) == len(store)
        assert reloaded.answer("capital of France")

    def test_save_without_path_raises(self, store):
        with pytest.raises(ValueError):
            store.save()

    def test_load_missing_file_is_noop(self, tmp_path):
        kb = KnowledgeStore(tmp_path / "missing.json")
        assert len(kb) == 0
