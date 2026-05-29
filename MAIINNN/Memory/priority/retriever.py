"""
Priority Memory: Retriever Department

Ranked retrieval by importance score + keyword match.
Boosts importance on access.
"""

import time

from MAIINNN.Memory.priority import store as priority_store
from MAIINNN.Memory.priority.intake import PriorityEntry
from MAIINNN.Memory.priority.scorer import boost_on_access


def search(query_keywords: list[str], max_results: int = 10) -> list[PriorityEntry]:
    """
    Search priority memory by keyword overlap.
    Results ranked by (keyword_overlap * importance).
    Boosts importance on each accessed entry.
    """
    entries = priority_store.load_all()
    query_set = set(k.lower() for k in query_keywords)

    scored: list[tuple[float, PriorityEntry]] = []
    for entry in entries:
        entry_kw = set(k.lower() for k in entry.keywords)
        overlap = len(query_set & entry_kw)
        if overlap == 0:
            continue

        score = overlap * (0.5 + entry.importance)
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, entry in scored[:max_results]:
        entry = boost_on_access(entry)
        priority_store.update_entry(entry)
        results.append(entry)

    return results


def get_top(n: int = 5) -> list[PriorityEntry]:
    """Get top N entries by importance."""
    entries = priority_store.load_all()
    entries.sort(key=lambda e: e.importance, reverse=True)
    return entries[:n]


def get_by_id(entry_id: str) -> PriorityEntry | None:
    for entry in priority_store.load_all():
        if entry.id == entry_id:
            return entry
    return None
