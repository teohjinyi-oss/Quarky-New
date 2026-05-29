"""
Priority Memory: Promoter Department

Auto-promotes entries to Permanent memory when importance stays
above threshold for N consecutive days.
"""

import time

from runtime.config.config import MEMORY
from core.memory.priority.intake import PriorityEntry
from core.memory.priority import store as priority_store


def check_promotions() -> list[PriorityEntry]:
    """
    Scan priority entries. Promote to permanent if importance > threshold
    for at least priority_promote_days.

    Returns list of entries that were promoted (and removed from priority).
    """
    threshold = MEMORY["priority_promote_threshold"]
    required_days = MEMORY["priority_promote_days"]
    now = time.time()

    entries = priority_store.load_all()
    promoted: list[PriorityEntry] = []
    remaining: list[PriorityEntry] = []

    for entry in entries:
        if entry.importance >= threshold:
            age_days = (now - entry.created_at) / 86400
            if age_days >= required_days:
                promoted.append(entry)
                continue
        remaining.append(entry)

    if promoted:
        priority_store.save_all(remaining)

    return promoted
