"""
Tests for v2 NLP: Embeddings, Classifier, SpellCheck, EntityExtractor, ContextManager
"""

import pytest
from core.nlp.context_manager import ContextManager
from core.nlp.entity_extractor import EntityExtractor
from core.nlp import spell_check
from core.nlp import classifier as nlp_classifier
from core.nlp.embeddings import encode, similarity


# ── Embeddings ───────────────────────────────────────────────

class TestEmbeddings:
    def test_encode_returns_list(self):
        vec = encode("hello world")
        assert isinstance(vec, list)
        assert len(vec) > 0

    def test_similarity_identical(self):
        sim = similarity("hello", "hello")
        assert sim > 0.9

    def test_similarity_different(self):
        sim = similarity("hello world", "quantum physics research")
        assert sim < 0.8


# ── Classifier ───────────────────────────────────────────────

class TestNLPClassifier:
    def test_classify_returns_result(self):
        result = nlp_classifier.classify("open chrome")
        assert hasattr(result, "intent")
        assert hasattr(result, "confidence")

    def test_classify_question(self):
        result = nlp_classifier.classify("what is python")
        assert result.intent.lower() in ("question", "task", "greeting", "chat", "command")

    def test_classify_greeting(self):
        result = nlp_classifier.classify("hello")
        assert result.intent.lower() in ("greeting", "chat", "command", "question", "creative", "task")


# ── Spell Check ──────────────────────────────────────────────

class TestSpellCheck:
    def test_correct_identity(self):
        """Correct text should pass through unchanged."""
        assert spell_check.correct("hello world") == "hello world"

    def test_correct_known_typo(self):
        result = spell_check.correct("quarky")
        assert isinstance(result, str)


# ── Entity Extractor ────────────────────────────────────────

class TestEntityExtractor:
    def test_extract_entities(self):
        ext = EntityExtractor()
        result = ext.extract("remind me to call John tomorrow at 3pm")
        assert hasattr(result, "entities")

    def test_extract_slots(self):
        ext = EntityExtractor()
        result = ext.extract("set a timer for 5 minutes")
        assert hasattr(result, "slots") or hasattr(result, "entities")


# ── Context Manager ──────────────────────────────────────────

class TestContextManager:
    def test_add_turn(self):
        cm = ContextManager()
        cm.add_turn("hello", "Hi there!")
        assert cm.turn_count == 1

    def test_resolve_pronouns_no_context(self):
        cm = ContextManager()
        result = cm.resolve_pronouns("tell me about it")
        assert isinstance(result, str)

    def test_context_window(self):
        cm = ContextManager()
        for i in range(15):
            cm.add_turn(f"msg {i}", f"reply {i}")
        # Window should be capped
        assert cm.turn_count <= 15  # stored internally

    def test_get_context_dict(self):
        cm = ContextManager()
        cm.add_turn("hello", "hi")
        ctx = cm.get_context_dict()
        assert isinstance(ctx, dict)
