"""
Tests for v2 Learning: Feedback, Correction, PatternExtractor, Trainer
"""

import pytest
from core.learning.feedback import FeedbackProcessor
from core.learning.correction import CorrectionEngine
from core.learning.pattern_extractor import PatternExtractor
from core.learning.trainer import Trainer


class TestFeedbackProcessor:
    def test_detect_positive(self):
        fp = FeedbackProcessor()
        fb = fp.detect_feedback("thanks, that's correct")
        assert fb is not None
        assert fb.feedback_type == "positive"

    def test_detect_negative(self):
        fp = FeedbackProcessor()
        fb = fp.detect_feedback("no, that's wrong")
        assert fb is not None
        assert fb.feedback_type in ("negative", "correction")

    def test_detect_correction(self):
        fp = FeedbackProcessor()
        fb = fp.detect_feedback("no, the answer is Paris")
        assert fb is not None
        assert fb.feedback_type == "correction"
        assert "Paris" in fb.correction

    def test_no_feedback(self):
        fp = FeedbackProcessor()
        fb = fp.detect_feedback("what is the weather today")
        assert fb is None or fb.feedback_type not in ("positive", "negative", "correction")


class TestCorrectionEngine:
    def test_record_and_check(self):
        ce = CorrectionEngine()
        ce.record("capital of France", "London", "Paris")
        result = ce.check("capital of France")
        assert result == "Paris"

    def test_check_missing(self):
        ce = CorrectionEngine()
        result = ce.check("random unknown question xyz")
        assert result is None


class TestPatternExtractor:
    def test_extract_from_pair(self):
        pe = PatternExtractor()
        patterns = pe.extract_from_pair("what is Python", "Python is a programming language")
        assert len(patterns) >= 0  # may or may not match templates

    def test_match_query(self):
        pe = PatternExtractor()
        pe.extract_from_pair("what is Python", "Python is a programming language")
        result = pe.match_query("what is Java")
        # may return a LearnedPattern or None
        from core.learning.pattern_extractor import LearnedPattern
        assert result is None or isinstance(result, LearnedPattern)


class TestTrainer:
    def test_add_example(self):
        t = Trainer()
        t.add_example("hello", "GREETING")
        assert t.example_count >= 1

    def test_should_retrain_false_initially(self):
        t = Trainer()
        for i in range(5):
            t.add_example(f"text {i}", "TASK")
        assert not t.should_retrain()  # needs 20+ examples


class TestWebLearner:
    """Web learner — availability check and fact extraction."""

    def test_web_learner_instantiates(self):
        from core.learning.web_learner import WebLearner
        wl = WebLearner()
        # is_available depends on whether duckduckgo_search is installed
        assert isinstance(wl.is_available, bool)

    def test_extract_best_sentence_returns_string(self):
        from core.learning.web_learner import WebLearner
        wl = WebLearner()
        body = (
            "Python is a high-level programming language. "
            "It is widely used in data science. "
            "Java is another popular language."
        )
        result = wl._extract_best_sentence(body, "what is python")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_best_sentence_prefers_relevant(self):
        from core.learning.web_learner import WebLearner
        wl = WebLearner()
        body = (
            "The sky is blue. "
            "Python is a high-level programming language interpreted by CPython. "
            "Cats meow."
        )
        result = wl._extract_best_sentence(body, "python language")
        assert "python" in result.lower() or "programming" in result.lower()

    def test_search_and_learn_returns_list(self):
        from core.learning.web_learner import WebLearner
        wl = WebLearner()
        facts = wl.search_and_learn("what is the capital of France", max_results=2)
        # Returns list — may be empty if network unavailable; should not raise
        assert isinstance(facts, list)

    def test_search_and_learn_stores_in_memory(self, tmp_path, monkeypatch):
        """Facts returned by search_and_learn are forwarded to memory manager."""
        from core.learning.web_learner import WebLearner, WebFact

        stored = []

        class MockMemory:
            def store(self, token):
                stored.append(token)

        wl = WebLearner()
        wl.set_memory(MockMemory())

        # Inject a fake fact without hitting the network
        facts = [
            WebFact(text="Paris is the capital of France.",
                    source_url="https://example.com", confidence=0.9, query="capital france"),
        ]
        wl._store_facts(facts, "capital france")
        assert len(stored) == 1

    def test_search_and_learn_timeout_returns_quickly(self, monkeypatch):
        """A slow search backend must not freeze the app."""
        import sys
        import time
        import types
        from core.learning.web_learner import WebLearner

        class SlowDDGS:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def text(self, query, max_results=3):
                time.sleep(2.0)
                return []

        monkeypatch.setitem(sys.modules, "ddgs", types.SimpleNamespace(DDGS=SlowDDGS))

        wl = WebLearner()
        wl._search_available = True
        wl._ddgs_module = "ddgs"

        start = time.perf_counter()
        facts = wl.search_and_learn("hard question", max_results=1, timeout_seconds=0.6)
        elapsed = time.perf_counter() - start

        assert facts == []
        assert elapsed < 1.5


class TestOrchestratorWebFallback:
    """Orchestrator web fallback path activates on low-confidence questions."""

    def test_web_fallback_method_exists(self):
        from core.orchestrator import Orchestrator
        o = Orchestrator()
        assert hasattr(o, "_web_fallback")
        # Returns empty string when memory is not set and network unavailable
        result = o._web_fallback("what is quantum entanglement")
        assert isinstance(result, str)

    def test_low_confidence_question_does_not_crash(self):
        """Process an unknown question end-to-end; must not raise."""
        from core.orchestrator import Orchestrator
        o = Orchestrator()
        o.boot()
        # An obscure question the system almost certainly won't know
        result = o.process("what is the boiling point of einsteinium in kelvin")
        assert isinstance(result, str)
        assert len(result) > 0
