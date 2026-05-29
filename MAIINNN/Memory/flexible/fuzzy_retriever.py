"""
Flexible Memory: Fuzzy Retriever Department

Keyword-based fuzzy search across summaries.
Returns entries ranked by keyword overlap + recency + access frequency.
"""

import time

from MAIINNN.Memory.flexible import store
from MAIINNN.Memory.flexible.intake import FlexEntry


def search(query_keywords: list[str], max_results: int = 10) -> list[FlexEntry]:
    """
    Search flexible memory by keyword overlap against entry keywords
    and summary text.
    """
    entries = store.load_all()
    query_set = set(k.lower() for k in query_keywords)
    now = time.time()

    scored: list[tuple[float, FlexEntry]] = []
    for entry in entries:
        entry_kw = set(k.lower() for k in entry.keywords)

        # Keyword overlap
        overlap = len(query_set & entry_kw)

        # Also check if query words appear in summary text
        summary_lower = entry.summary.lower()
        text_hits = sum(1 for kw in query_set if kw in summary_lower)

        combined = overlap + (text_hits * 0.5)
        if combined == 0:
            continue

        # Recency bonus (decays over 7 days)
        age = now - entry.created_at
        recency = max(0.0, 1.0 - (age / (7 * 86400)))

        # Access frequency bonus
        access_bonus = min(entry.access_count * 0.1, 1.0)

        score = combined + (recency * 0.3) + (access_bonus * 0.2)
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Update access counts on retrieved entries
    results = []
    for _, entry in scored[:max_results]:
        entry.access_count += 1
        entry.last_accessed = now
        store.update_entry(entry)
        results.append(entry)

    return results


def get_recent(n: int = 5) -> list[FlexEntry]:
    """Get the N most recent entries."""
    entries = store.load_all()
    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries[:n]


def get_by_id(entry_id: str) -> FlexEntry | None:
    for entry in store.load_all():
        if entry.id == entry_id:
            return entry
    return None
