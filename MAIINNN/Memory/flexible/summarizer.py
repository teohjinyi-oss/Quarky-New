"""
Flexible Memory: Summarizer Department

Compresses original text to a summary using the NLP summarizer.
Can operate in batch with worker pool.
"""

from AppStudio.Config import MEMORY
from MAIINNN.Memory.flexible.intake import FlexEntry
from MAIINNN.NLP.summarizer import summarize, extract_key_phrases


def summarize_entry(entry: FlexEntry) -> FlexEntry:
    """
    Fill in the summary field of a FlexEntry.
    Summary ratio from config controls compression.
    """
    text = entry.original
    if not text.strip():
        entry.summary = ""
        return entry

    # Estimate max sentences from ratio
    sentences_approx = max(1, text.count(".") + text.count("!") + text.count("?"))
    ratio = MEMORY["flexible_summary_ratio"]
    max_sentences = max(1, int(sentences_approx * ratio))

    entry.summary = summarize(text, max_sentences=max_sentences)

    # Merge key phrases into keywords
    phrases = extract_key_phrases(text, top_n=10)
    existing = set(entry.keywords)
    for p in phrases:
        if p not in existing:
            entry.keywords.append(p)

    return entry


def summarize_batch(entries: list[FlexEntry]) -> list[FlexEntry]:
    """
    Summarize a list of entries. Could be dispatched to worker pool
    for parallel processing on large batches.
    """
    return [summarize_entry(e) for e in entries]
