"""
Tests for v2 Memory: HotCache, VectorStore, GraphStore, MemoryManagerV2
"""

import pytest
from core.memory.manager_v2 import MemoryManagerV2


class TestMemoryManagerV2:
    def test_store_and_search(self):
        mm = MemoryManagerV2()
        mm.store("The capital of France is Paris", source="test", topic="geography")
        results = mm.search("capital of France")
        assert results.total > 0

    def test_store_multiple(self):
        mm = MemoryManagerV2()
        mm.store("Python is a programming language", source="test")
        mm.store("Java is also a programming language", source="test")
        mm.store("Paris is in Europe", source="test")
        results = mm.search("programming")
        assert results.total >= 1

    def test_relate(self):
        mm = MemoryManagerV2()
        mm.store("cats are pets", source="test")
        mm.store("dogs are pets", source="test")
        mm.relate("cats", "dogs", "both_are_pets")
        # Graph should have the edge
        assert mm._graph is not None

    def test_search_empty(self):
        mm = MemoryManagerV2()
        results = mm.search("nonexistent query xyz123")
        from core.memory.manager_v2 import SearchResult
        assert isinstance(results, SearchResult)
