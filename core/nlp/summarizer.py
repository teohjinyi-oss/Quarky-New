"""
NLP: Rule-Based Summarizer

Extracts the most important sentences from text using keyword frequency.
Used by flexible memory to compress conversation history.
"""

from core.nlp.tokenizer import (
    tokenize_words, tokenize_sentences, remove_stop_words,
)


def summarize(text: str, max_sentences: int = 3) -> str:
    """
    Extract top-N sentences by keyword density.

    Algorithm:
    1. Tokenize entire text → word frequencies (minus stop words)
    2. Split into sentences
    3. Score each sentence = sum of word frequencies it contains
    4. Return top N sentences in original order
    """
    if not text or not text.strip():
        return ""

    sentences = tokenize_sentences(text)
    if len(sentences) <= max_sentences:
        return text.strip()

    # Build word frequency map (no stop words)
    all_tokens = remove_stop_words(tokenize_words(text))
    freq: dict[str, int] = {}
    for token in all_tokens:
        freq[token] = freq.get(token, 0) + 1

    # Score each sentence
    scored: list[tuple[int, float]] = []  # (original_index, score)
    for i, sentence in enumerate(sentences):
        words = tokenize_words(sentence)
        score = sum(freq.get(w, 0) for w in words)
        # Normalize by sentence length to avoid bias toward long sentences
        if words:
            score /= len(words)
        scored.append((i, score))

    # Pick top N by score
    scored.sort(key=lambda x: x[1], reverse=True)
    top_indices = sorted([idx for idx, _ in scored[:max_sentences]])

    # Rebuild in original order
    return " ".join(sentences[i] for i in top_indices)


def extract_key_phrases(text: str, top_n: int = 5) -> list[str]:
    """
    Return the top-N most frequent meaningful words.
    Lightweight keyword extraction for memory tagging.
    """
    tokens = remove_stop_words(tokenize_words(text))
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1

    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]
