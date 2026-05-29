"""
Tests for v2 Intelligence Core: Token, Scorer, Classifier, Tracker
"""

import pytest
from core.intelligence.token import Token, SpecificityTier, ConfirmationTier
from core.intelligence.scorer import TokenScorer
from core.intelligence.classifier import SpecificityClassifier
from core.intelligence.tracker import TokenTracker


# ── Token ────────────────────────────────────────────────────

class TestToken:
    def test_create_default(self):
        t = Token(id="t1", text="hello")
        assert t.id == "t1"
        assert t.specificity == SpecificityTier.GG
        assert t.confirmation == ConfirmationTier.UNVERIFIED

    def test_touch_increments_frequency(self):
        t = Token(id="t1", text="hello")
        old_freq = t.frequency
        t.touch()
        assert t.frequency == old_freq + 1

    def test_confirm_sets_tier(self):
        t = Token(id="t1", text="hello")
        t.confirm()
        assert t.confirmation == ConfirmationTier.USER_CONFIRMED

    def test_boost_and_cap(self):
        t = Token(id="t1", text="hello", importance=0.9)
        t.boost_importance(0.2)
        assert t.importance == 1.0  # capped at 1

    def test_decay(self):
        t = Token(id="t1", text="hello", importance=0.5)
        t.decay_importance(0.1)
        assert t.importance == pytest.approx(0.4)

    def test_decay_floor(self):
        t = Token(id="t1", text="hello", importance=0.05)
        t.decay_importance(0.1)
        assert t.importance == 0.0

    def test_to_dict_roundtrip(self):
        t = Token(id="t1", text="hello", specificity=SpecificityTier.SS)
        d = t.to_dict()
        t2 = Token.from_dict(d)
        assert t2.id == t.id
        assert t2.specificity == SpecificityTier.SS


# ── Scorer ───────────────────────────────────────────────────

class TestTokenScorer:
    def test_score_range(self):
        s = TokenScorer()
        t = Token(id="t1", text="hello", importance=0.5, frequency=5)
        score = s.score(t)
        assert 0 <= score <= 1

    def test_rank_order(self):
        s = TokenScorer()
        t1 = Token(id="t1", text="a", importance=0.9, frequency=10)
        t2 = Token(id="t2", text="b", importance=0.1, frequency=1)
        ranked = s.rank([t1, t2])
        assert ranked[0].id == "t1"

    def test_eviction_candidates(self):
        s = TokenScorer()
        tokens = [
            Token(id=f"t{i}", text=f"w{i}", importance=0.01 * i)
            for i in range(10)
        ]
        evict = s.eviction_candidates(tokens, threshold=0.15)
        assert isinstance(evict, list)


# ── Classifier ───────────────────────────────────────────────

class TestSpecificityClassifier:
    def test_classify_query_returns_float(self):
        c = SpecificityClassifier()
        score = c.classify_query("what is the capital of France")
        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_classify_pair_returns_tier(self):
        c = SpecificityClassifier()
        tier = c.classify_pair("what is 2+2", "4")
        assert isinstance(tier, SpecificityTier)


# ── Tracker ──────────────────────────────────────────────────

class TestTokenTracker:
    def test_add_and_get(self):
        tr = TokenTracker()
        t = Token(id="t1", text="hello")
        tr.register(t)
        got = tr.get("t1")
        assert got is not None
        assert got.text == "hello"

    def test_search(self):
        tr = TokenTracker()
        tr.register(Token(id="t1", text="python programming"))
        tr.register(Token(id="t2", text="java basics"))
        results = tr.search_text("python")
        assert any(t.id == "t1" for t in results)

    def test_remove(self):
        tr = TokenTracker()
        tr.register(Token(id="t1", text="hello"))
        tr.remove("t1")
        assert tr.get("t1") is None
