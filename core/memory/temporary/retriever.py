"""
Temporary Memory: Retriever Department

Searches temporary entries by keyword match or recency.
"""

import time
from core.memory.temporary import store
from core.memory.temporary.intake import TempEntry


def search(query_keywords: list[str], max_results: int = 10) -> list[TempEntry]:
    """
    Search temporary memory by keyword overlap.
    Returns entries ranked by: (keyword_overlap, recency).
    Skips expired entries.
    """
    entries = store.load_all()
    now = time.time()
    query_set = set(k.lower() for k in query_keywords)

    scored: list[tuple[float, TempEntry]] = []
    for entry in entries:
        if entry.is_expired:
            continue

        entry_set = set(k.lower() for k in entry.keywords)
        overlap = len(query_set & entry_set)
        if overlap == 0:
            continue

        # Score: overlap count + recency bonus (0–1 based on age)
        age_seconds = now - entry.created_at
        recency = max(0.0, 1.0 - (age_seconds / 86400))  # decays over 24h
        score = overlap + (recency * 0.5)

        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:max_results]]


def get_recent(n: int = 5) -> list[TempEntry]:
    """Get the N most recent non-expired entries."""
    entries = store.load_all()
    alive = [e for e in entries if not e.is_expired]
    alive.sort(key=lambda e: e.created_at, reverse=True)
    return alive[:n]


def get_by_id(entry_id: str) -> TempEntry | None:
    """Retrieve a single entry by ID."""
    for entry in store.load_all():
        if entry.id == entry_id:
            return entry
    return None
