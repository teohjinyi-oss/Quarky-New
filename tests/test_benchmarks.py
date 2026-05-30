"""
Tests for the Phase 0 benchmark harness (benchmarks/).
"""

import json

import pytest

from benchmarks import (
    Scorecard,
    default_dataset,
    intent_accuracy,
    latency_ms,
    reasoning_signal_quality,
    run_benchmark,
)
from benchmarks.dataset import all_cases, IntentCase, ReasoningCase
from benchmarks.scorecard import REFERENCE_PROFILE


class TestDataset:
    def test_default_dataset_has_suites(self):
        ds = default_dataset()
        assert "intent" in ds and "reasoning" in ds
        assert all(isinstance(c, IntentCase) for c in ds["intent"])
        assert all(isinstance(c, ReasoningCase) for c in ds["reasoning"])

    def test_all_cases_flattens(self):
        ds = default_dataset()
        flat = all_cases(ds)
        assert len(flat) == sum(len(v) for v in ds.values())

    def test_case_ids_unique(self):
        ids = [c.case_id for c in all_cases()]
        assert len(ids) == len(set(ids))


class TestMetrics:
    def test_intent_accuracy_in_range(self):
        m = intent_accuracy(all_cases())
        assert 0.0 <= m.score <= 1.0
        assert m.detail["total"] > 0

    def test_intent_accuracy_high(self):
        # The curated intent set is designed to be detected correctly.
        m = intent_accuracy(all_cases())
        assert m.score >= 0.8

    def test_reasoning_signal_quality_in_range(self):
        m = reasoning_signal_quality(all_cases())
        assert 0.0 <= m.score <= 1.0

    def test_latency_metric(self):
        m = latency_ms(all_cases())
        assert 0.0 <= m.score <= 1.0
        assert m.raw >= 0.0

    def test_metric_result_clamps(self):
        from benchmarks.metrics import MetricResult
        assert MetricResult("x", 5.0).score == 1.0
        assert MetricResult("x", -5.0).score == 0.0


class TestScorecard:
    def test_run_benchmark_returns_scorecard(self):
        card = run_benchmark()
        assert isinstance(card, Scorecard)
        assert len(card.entries) == 3
        assert 0.0 <= card.overall <= 1.0

    def test_scorecard_entry_verdict(self):
        from benchmarks.scorecard import ScorecardEntry
        assert ScorecardEntry("m", 0.9, 0.5).verdict == "ahead"
        assert ScorecardEntry("m", 0.3, 0.5).verdict == "behind"
        assert ScorecardEntry("m", 0.5, 0.5).verdict == "tied"

    def test_render_is_string(self):
        card = run_benchmark()
        text = card.render()
        assert "Quarky Benchmark Scorecard" in text
        assert "OVERALL" in text

    def test_to_dict_is_json_serialisable(self):
        card = run_benchmark()
        blob = json.dumps(card.to_dict())
        loaded = json.loads(blob)
        assert "overall" in loaded
        assert len(loaded["entries"]) == 3

    def test_reference_profile_keys_match_metrics(self):
        card = run_benchmark()
        for e in card.entries:
            assert e.metric in REFERENCE_PROFILE

    def test_custom_reference(self):
        card = run_benchmark(reference={"intent_accuracy": 0.0,
                                        "reasoning_signal_quality": 0.0,
                                        "latency": 0.0})
        # Against a zero bar Quarky should be at or ahead everywhere.
        assert all(e.delta >= 0.0 for e in card.entries)


class TestCLI:
    def test_main_table_output(self, capsys):
        from benchmarks.__main__ import main
        rc = main([])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Quarky Benchmark Scorecard" in out

    def test_main_json_output(self, capsys):
        from benchmarks.__main__ import main
        rc = main(["--json"])
        out = capsys.readouterr().out
        assert rc == 0
        loaded = json.loads(out)
        assert "overall" in loaded and "entries" in loaded
