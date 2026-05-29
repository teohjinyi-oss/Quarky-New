"""
NLP: Custom Tokenizer

Word and sentence splitting — zero external dependencies.
Used by classifier, pattern matcher, summarizer, and brain modules.
"""

import re
from typing import Optional


# Sentence-ending patterns
_SENTENCE_SPLITTER = re.compile(
    r'(?<=[.!?])\s+(?=[A-Za-z])'  # split after .!? followed by space + letter
)

# Word boundary pattern — split on whitespace and punctuation boundaries
_WORD_SPLITTER = re.compile(r'\s+')

# Punctuation to strip from word edges (keep internal like apostrophes)
_EDGE_PUNCT = re.compile(r"^[^\w]+|[^\w]+$")

# Contraction patterns (don't split these)
_CONTRACTIONS = {
    "don't", "doesn't", "won't", "can't", "isn't", "aren't",
    "wasn't", "weren't", "shouldn't", "couldn't", "wouldn't",
    "haven't", "hasn't", "hadn't", "i'm", "i've", "i'll", "i'd",
    "you're", "you've", "you'll", "you'd", "he's", "she's", "it's",
    "we're", "we've", "we'll", "we'd", "they're", "they've", "they'll",
    "that's", "there's", "here's", "what's", "who's", "let's",
}


def tokenize_words(text: str) -> list[str]:
    """
    Split text into word tokens.

    Rules:
    - Split on whitespace
    - Strip edge punctuation
    - Preserve contractions (don't → "don't")
    - Lowercase (input should already be cleaned)
    - Filter empty tokens
    """
    if not text:
        return []

    raw_tokens = _WORD_SPLITTER.split(text)
    tokens = []

    for raw in raw_tokens:
        if not raw:
            continue

        # Check if it's a known contraction before stripping
        lower = raw.lower()
        if lower in _CONTRACTIONS:
            tokens.append(lower)
            continue

        # Strip edge punctuation
        cleaned = _EDGE_PUNCT.sub('', raw)
        if cleaned:
            tokens.append(cleaned.lower())

    return tokens


def tokenize_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Simple rule-based: split on .!? followed by space and capital letter.
    Falls back to full text as single sentence if no splits found.
    """
    if not text:
        return []

    sentences = _SENTENCE_SPLITTER.split(text)
    result = [s.strip() for s in sentences if s.strip()]

    return result if result else [text.strip()]


def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    """Generate n-grams from a token list."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def bigrams(tokens: list[str]) -> list[tuple[str, ...]]:
    return ngrams(tokens, 2)


def trigrams(tokens: list[str]) -> list[tuple[str, ...]]:
    return ngrams(tokens, 3)


def word_count(text: str) -> int:
    """Quick word count without full tokenization."""
    return len(text.split())


def char_count(text: str) -> int:
    """Character count excluding whitespace."""
    return len(text.replace(" ", ""))


# ─── Stop Words ─────────────────────────────────────────────
# Minimal stop word list — used by summarizer and pattern matcher
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "but", "and", "or",
    "if", "because", "until", "while", "about", "up", "down", "it",
    "its", "this", "that", "these", "those", "i", "me", "my", "we",
    "our", "you", "your", "he", "him", "his", "she", "her", "they",
    "them", "their", "what", "which", "who", "whom",
})


def remove_stop_words(tokens: list[str]) -> list[str]:
    """Filter out stop words from token list."""
    return [t for t in tokens if t not in STOP_WORDS]


def keyword_tokens(text: str) -> list[str]:
    """Tokenize and remove stop words — returns meaningful keywords only."""
    return remove_stop_words(tokenize_words(text))
