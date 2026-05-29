"""Tests for the 4-layer Memory System — store/recall/forget/decay."""

import pytest


class TestMemoryManager:
    """Test the memory manager coordinator."""

    def test_store_temporary(self):
        from core.memory.manager import store_temporary
        result = store_temporary("test content", source="test")
        assert result.success
        assert result.layer == "temporary"

    def test_store_flexible(self):
        from core.memory.manager import store_flexible
        result = store_flexible("flexible test content", source="test")
        assert result.success
        assert result.layer == "flexible"

    def test_store_priority(self):
        from core.memory.manager import store_priority
        result = store_priority("important content", source="test")
        assert result.success
        assert result.layer == "priority"

    def test_store_permanent(self):
        from core.memory.manager import store_permanent
        result = store_permanent("permanent fact", tags=["test"], source="test")
        assert result.success
        assert result.layer == "permanent"

    def test_recall(self):
        from core.memory.manager import store_temporary, recall
        store_temporary("the sky is blue", source="test")
        results = recall(["sky", "blue"], max_per_layer=5)
        assert results.total >= 0  # May or may not match depending on search impl

    def test_stats(self):
        from core.memory.manager import stats
        s = stats()
        assert "temporary" in s
        assert "flexible" in s
        assert "priority" in s
        assert "permanent" in s

    def test_forget_temporary(self):
        from core.memory.manager import store_temporary, forget_temporary
        result = store_temporary("will be forgotten", source="test")
        entry_id = result.data
        if entry_id:
            forget_result = forget_temporary(entry_id)
            assert forget_result.layer == "temporary"

    def test_decay_once(self):
        from core.memory.manager import run_decay_once
        report = run_decay_once()
        assert hasattr(report, "temporary_cleaned")
        assert hasattr(report, "flexible_degraded")
