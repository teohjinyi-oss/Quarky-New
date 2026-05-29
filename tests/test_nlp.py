"""Tests for the NLP pipeline — cleaner + tokenizer + classifier."""

import pytest


class TestCleaner:
    """Test NLP input cleaner."""

    def test_clean_basic(self):
        from core.nlp.cleaner import clean
        assert clean("  Hello   World  ") == "hello world"

    def test_clean_html(self):
        from core.nlp.cleaner import clean
        result = clean("<script>alert('xss')</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_clean_shell_chars(self):
        from core.nlp.cleaner import clean
        result = clean("hello; rm -rf /")
        assert ";" not in result
        assert "hello" in result

    def test_clean_empty(self):
        from core.nlp.cleaner import clean
        assert clean("") == ""
        assert clean("   ") == ""

    def test_clean_max_length(self):
        from core.nlp.cleaner import clean, MAX_INPUT_LENGTH
        long_text = "a" * (MAX_INPUT_LENGTH + 100)
        result = clean(long_text)
        assert len(result) <= MAX_INPUT_LENGTH


class TestTokenizer:
    """Test NLP tokenizer."""

    def test_tokenize_words(self):
        from core.nlp.tokenizer import tokenize_words
        tokens = tokenize_words("hello world foo")
        assert "hello" in tokens
        assert "world" in tokens

    def test_keyword_tokens(self):
        from core.nlp.tokenizer import keyword_tokens
        keywords = keyword_tokens("what is the weather today")
        # Stop words like "is", "the" should be filtered
        assert "weather" in keywords
        assert "today" in keywords


class TestClassifier:
    """Test NLP intent classifier."""

    def test_classify_question(self):
        from core.nlp.classifier import classify
        result = classify("what is the capital of france")
        assert result.intent in ("question", "task")
        assert result.confidence > 0

    def test_classify_command(self):
        from core.nlp.classifier import classify
        result = classify("open chrome")
        assert result.intent in ("command", "task")

    def test_classify_empty(self):
        from core.nlp.classifier import classify
        result = classify("")
        assert result.intent == "task"
        assert result.confidence == 0.0

    def test_quick_intent(self):
        from core.nlp.classifier import quick_intent
        intent = quick_intent("what is 5 plus 3")
        assert isinstance(intent, str)
        assert len(intent) > 0
