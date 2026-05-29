"""
Permanent Memory: Retriever Department

Full-text keyword + tag-based search in SQLite.
Boosts access count on retrieval.
"""

import json
import time

from core.memory.permanent import store as permanent_store
from core.memory.permanent.intake import PermanentEntry


def search(query_keywords: list[str], max_results: int = 10) -> list[PermanentEntry]:
    """
    Search permanent memory by keyword overlap against stored keywords
    and content. Ranked by overlap score.
    """
    entries = permanent_store.load_all()
    query_set = set(k.lower() for k in query_keywords)

    scored: list[tuple[float, PermanentEntry]] = []
    for entry in entries:
        entry_kw = set(k.lower() for k in entry.keywords)
        overlap = len(query_set & entry_kw)

        # Also check content text match
        content_lower = entry.content.lower()
        text_hits = sum(1 for kw in query_set if kw in content_lower)

        combined = overlap + (text_hits * 0.5)
        if combined == 0:
            continue

        scored.append((combined, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    now = time.time()
    for _, entry in scored[:max_results]:
        entry.access_count += 1
        entry.last_accessed = now
        permanent_store.update_entry(entry)
        results.append(entry)

    return results


def search_by_tags(tags: list[str], max_results: int = 10) -> list[PermanentEntry]:
    """Search entries that contain any of the given tags."""
    entries = permanent_store.load_all()
    tag_set = set(t.lower() for t in tags)

    results = []
    for entry in entries:
        entry_tags = set(t.lower() for t in entry.tags)
        if tag_set & entry_tags:
            results.append(entry)
        if len(results) >= max_results:
            break

    return results


def get_by_id(entry_id: str) -> PermanentEntry | None:
    for entry in permanent_store.load_all():
        if entry.id == entry_id:
            return entry
    return None
