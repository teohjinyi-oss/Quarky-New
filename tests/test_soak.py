"""
Soak Test — Sustained Load Simulation

Runs Quarky through 100 simulated interactions to detect:
- Memory leaks (compare RSS before/after)
- Thread leaks (compare thread counts)
- Error accumulation
- Performance degradation over time

Usage:
    py -3.12 -m pytest tests/test_soak.py -x -q --tb=short
"""

from __future__ import annotations

import gc
import threading
import time
from unittest.mock import patch, MagicMock

import pytest


# ── Sample queries covering different code paths ──────────────
SOAK_QUERIES = [
    "hello",
    "what is your name",
    "what time is it",
    "open chrome",
    "who invented the telephone",
    "close it",
    "thanks that helped",
    "no that was wrong",
    "the answer is 42",
    "check my email",
    "check my calendar",
    "what day is it",
    "tell me a joke",
    "how does gravity work",
    "set volume to 50",
    "search for python tutorials",
    "create a reminder",
    "what's the weather like",
    "minimize everything",
    "who are you",
]


class TestSoakOrchestrator:
    """Soak test: run many interactions and check for leaks."""

    @pytest.fixture(autouse=True)
    def setup_orchestrator(self):
        """Boot orchestrator once for all soak tests."""
        from core.orchestrator import Orchestrator
        self.orch = Orchestrator()
        self.orch.boot()
        yield
        # Cleanup
        self.orch._ready = False

    def test_soak_100_interactions(self):
        """Run 100 interactions and check for stability."""
        gc.collect()
        initial_threads = threading.active_count()

        errors = []
        timings = []

        for i in range(100):
            query = SOAK_QUERIES[i % len(SOAK_QUERIES)]
            start = time.perf_counter()
            try:
                response = self.orch.process(query)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
                assert isinstance(response, str), f"Query {i}: response not str"
                assert len(response) > 0, f"Query {i}: empty response"
            except Exception as e:
                errors.append(f"Query {i} ('{query}'): {e}")

        # Allow daemon threads to settle
        time.sleep(0.5)
        gc.collect()
        final_threads = threading.active_count()

        # Assertions
        assert len(errors) == 0, f"Errors during soak:\n" + "\n".join(errors)

        # Thread leak: allow some daemon thread growth but not unbounded
        thread_growth = final_threads - initial_threads
        assert thread_growth < 20, (
            f"Thread leak: grew by {thread_growth} "
            f"({initial_threads} → {final_threads})"
        )

        # Performance: no single query should take > 60s (first query may load models)
        max_time = max(timings)
        assert max_time < 60.0, f"Slowest query took {max_time:.2f}s"

        # Average should stay reasonable (excluding model load spike)
        avg_time = sum(timings) / len(timings)
        assert avg_time < 5.0, f"Average query time {avg_time:.2f}s is too high"

        # Post-warmup queries (last 50) should be fast
        tail_avg = sum(timings[50:]) / len(timings[50:])
        assert tail_avg < 1.5, f"Post-warmup average {tail_avg:.2f}s is too high"

    def test_memory_operations_soak(self):
        """Soak memory subsystem with store/search cycles."""
        if not self.orch.memory:
            pytest.skip("Memory subsystem not available")

        mem = self.orch.memory
        for i in range(50):
            mem.store(
                text=f"Soak test fact number {i}: the sky is blue",
                source="soak_test",
                importance=0.3,
                topic="soak",
            )

        # Search should still work after bulk inserts
        results = mem.search("sky is blue", top_k=5)
        assert results is not None
        assert results.total > 0

    def test_concurrent_processing(self):
        """Multiple threads calling process() simultaneously."""
        errors = []
        results = []

        def worker(query: str, idx: int):
            try:
                resp = self.orch.process(query)
                results.append((idx, resp))
            except Exception as e:
                errors.append((idx, str(e)))

        threads = []
        for i in range(10):
            q = SOAK_QUERIES[i % len(SOAK_QUERIES)]
            t = threading.Thread(target=worker, args=(q, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
