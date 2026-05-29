"""
NLP: Intent Classifier (v2)

Hybrid classifier: rules fast-path + TF-IDF/NaiveBayes for ambiguous inputs.

Flow:
1. Score against rule-based patterns (v1 engine)
2. If confidence is HIGH (>0.7), return immediately (fast path)
3. If ambiguous, run TF-IDF vectorizer + Naive Bayes
4. Merge rule and ML scores
5. Return ClassifiedInput with combined confidence

The ML classifier retrains periodically as new labeled examples accumulate.
"""

from __future__ import annotations

import os
import pickle
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.nlp.tokenizer import tokenize_words, keyword_tokens
from core.nlp.patterns import (
    INTENT_BANK, score_intent, extract_all_entities,
)


@dataclass
class ClassifiedInput:
    """Result of classifying user input."""
    raw: str                              # original cleaned text
    intent: str                           # command | question | task | creative
    confidence: float                     # 0.0–1.0 normalized
    entities: dict[str, list[str]]        # extracted entities
    tokens: list[str]                     # full word tokens
    keywords: list[str]                   # tokens minus stop words
    method: str = "rules"                 # "rules" | "ml" | "hybrid"


# ── ML classifier (lazy loaded) ─────────────────────────────
_ml_classifier = None
_ml_vectorizer = None
_ml_lock = threading.Lock()
_ML_AVAILABLE = True

# Fast-path threshold: above this confidence, rules are enough
_FAST_PATH_THRESHOLD = 0.7


def _load_ml_model(model_path: Path | None = None):
    """Lazy-load the TF-IDF + NaiveBayes model if available."""
    global _ml_classifier, _ml_vectorizer, _ML_AVAILABLE

    if _ml_classifier is not None:
        return

    with _ml_lock:
        if _ml_classifier is not None:
            return

        if model_path and model_path.exists():
            try:
                with open(model_path, "rb") as f:
                    data = pickle.load(f)
                _ml_vectorizer = data["vectorizer"]
                _ml_classifier = data["classifier"]
                return
            except Exception:
                pass

        # Try to build a minimal model from built-in examples
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB

            # Seed training data (built-in examples)
            examples = _get_seed_examples()
            if len(examples) < 10:
                _ML_AVAILABLE = False
                return

            texts, labels = zip(*examples)
            _ml_vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
            X = _ml_vectorizer.fit_transform(texts)
            _ml_classifier = MultinomialNB()
            _ml_classifier.fit(X, labels)
        except ImportError:
            _ML_AVAILABLE = False


def _get_seed_examples() -> list[tuple[str, str]]:
    """Built-in training examples for bootstrapping the ML classifier."""
    return [
        # Commands
        ("open chrome", "command"),
        ("close the window", "command"),
        ("launch spotify", "command"),
        ("turn off the lights", "command"),
        ("set volume to 50", "command"),
        ("mute audio", "command"),
        ("start the timer", "command"),
        ("kill that process", "command"),
        ("minimize everything", "command"),
        ("restart the computer", "command"),
        ("open file explorer", "command"),
        ("shut down", "command"),
        # Questions
        ("what is python", "question"),
        ("how does gravity work", "question"),
        ("who invented the telephone", "question"),
        ("why is the sky blue", "question"),
        ("when was the moon landing", "question"),
        ("what time is it in tokyo", "question"),
        ("what's the weather like", "question"),
        ("how many planets are there", "question"),
        ("where is the eiffel tower", "question"),
        ("who is the president", "question"),
        ("is water wet", "question"),
        ("can cats swim", "question"),
        # Tasks
        ("remind me to call mom at 5pm", "task"),
        ("create a new folder called projects", "task"),
        ("find all pdf files", "task"),
        ("calculate 15 percent of 200", "task"),
        ("search for python tutorials", "task"),
        ("save this note", "task"),
        ("send an email to john", "task"),
        ("set a reminder for tomorrow", "task"),
        ("organize my desktop", "task"),
        ("check my schedule", "task"),
        ("find my documents", "task"),
        ("list all running processes", "task"),
        # Creative
        ("write me a poem about rain", "creative"),
        ("tell me a joke", "creative"),
        ("imagine a world without gravity", "creative"),
        ("come up with a name for my cat", "creative"),
        ("write a short story", "creative"),
        ("brainstorm ideas for a birthday party", "creative"),
        ("what if dinosaurs were still alive", "creative"),
        ("suggest a new hobby", "creative"),
        ("think of a creative solution", "creative"),
        ("invent something useful", "creative"),
    ]


def classify(text: str) -> ClassifiedInput:
    """
    Classify cleaned user input.

    Hybrid approach:
    1. Rule-based scoring (fast path if confident)
    2. ML scoring for ambiguous cases
    3. Merged result
    """
    if not text or not text.strip():
        return ClassifiedInput(
            raw=text,
            intent="task",
            confidence=0.0,
            entities={},
            tokens=[],
            keywords=[],
            method="rules",
        )

    lower = text.lower()

    # ── Rule-based scoring ──────────────────────────────────
    scores: dict[str, float] = {}
    for intent_name, patterns in INTENT_BANK.items():
        scores[intent_name] = score_intent(lower, patterns)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score == 0.0:
        rule_intent = "task"
        rule_confidence = 0.1
    else:
        rule_intent = best_intent
        # Normalize: if no competition (second=0), confidence = full score capped at 1.0
        # If there is competition, reduce by how much the runner-up scored
        if second_score == 0.0:
            rule_confidence = min(best_score, 1.0)
        else:
            rule_confidence = best_score / (best_score + second_score)
        rule_confidence = min(rule_confidence, 1.0)

    # ── Fast path: rules are confident enough ───────────────
    if rule_confidence >= _FAST_PATH_THRESHOLD:
        entities = extract_all_entities(text)
        tokens = tokenize_words(lower)
        keywords = keyword_tokens(lower)
        return ClassifiedInput(
            raw=text,
            intent=rule_intent,
            confidence=round(rule_confidence, 3),
            entities=entities,
            tokens=tokens,
            keywords=keywords,
            method="rules",
        )

    # ── ML scoring for ambiguous cases ──────────────────────
    ml_intent = None
    ml_confidence = 0.0

    if _ML_AVAILABLE:
        try:
            from runtime.config.config import NLP_V2
            model_path = NLP_V2.get("tfidf_model_path")
            _load_ml_model(model_path if model_path else None)
        except Exception:
            _load_ml_model()

        if _ml_classifier is not None and _ml_vectorizer is not None:
            X = _ml_vectorizer.transform([lower])
            ml_intent = _ml_classifier.predict(X)[0]
            probs = _ml_classifier.predict_proba(X)[0]
            ml_confidence = float(max(probs))

    # ── Merge ───────────────────────────────────────────────
    if ml_intent and ml_confidence > rule_confidence:
        final_intent = ml_intent
        final_confidence = (rule_confidence * 0.4 + ml_confidence * 0.6)
        method = "ml"
    elif ml_intent and ml_intent == rule_intent:
        final_intent = rule_intent
        final_confidence = (rule_confidence + ml_confidence) / 2
        method = "hybrid"
    else:
        final_intent = rule_intent
        final_confidence = rule_confidence
        method = "rules"

    entities = extract_all_entities(text)
    tokens = tokenize_words(lower)
    keywords = keyword_tokens(lower)

    return ClassifiedInput(
        raw=text,
        intent=final_intent,
        confidence=round(min(final_confidence, 1.0), 3),
        entities=entities,
        tokens=tokens,
        keywords=keywords,
        method=method,
    )


def is_command(result: ClassifiedInput) -> bool:
    return result.intent == "command"


def is_question(result: ClassifiedInput) -> bool:
    return result.intent == "question"


def is_creative(result: ClassifiedInput) -> bool:
    return result.intent == "creative"


def quick_intent(text: str) -> str:
    """Shortcut: returns just the intent string."""
    return classify(text).intent


def retrain(examples: list[tuple[str, str]], model_path: Path | None = None) -> bool:
    """
    Retrain the ML classifier with new examples.
    Returns True if successful, False if sklearn unavailable.
    """
    global _ml_classifier, _ml_vectorizer

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
    except ImportError:
        return False

    all_examples = _get_seed_examples() + examples
    texts, labels = zip(*all_examples)

    _ml_vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X = _ml_vectorizer.fit_transform(texts)
    _ml_classifier = MultinomialNB()
    _ml_classifier.fit(X, labels)

    # Save model
    if model_path:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, "wb") as f:
            pickle.dump({
                "vectorizer": _ml_vectorizer,
                "classifier": _ml_classifier,
            }, f)

    return True
