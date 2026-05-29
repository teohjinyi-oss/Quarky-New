"""
Priority Memory: Scorer Department

Adjusts importance on access (+boost) and decays over time (-per day).
"""

import time

from AppStudio.Config import MEMORY
from MAIINNN.Memory.priority.intake import PriorityEntry


def boost_on_access(entry: PriorityEntry) -> PriorityEntry:
    """Increase importance when the entry is accessed."""
    cap = MEMORY["priority_importance_cap"]
    boost = MEMORY["priority_access_boost"]
    entry.importance = min(cap, entry.importance + boost)
    entry.access_count += 1
    entry.last_accessed = time.time()
    return entry


def boost_user_mark(entry: PriorityEntry) -> PriorityEntry:
    """Extra importance boost when user explicitly marks as important."""
    cap = MEMORY["priority_importance_cap"]
    boost = MEMORY["priority_user_boost"]
    entry.importance = min(cap, entry.importance + boost)
    return entry


def decay(entry: PriorityEntry) -> PriorityEntry:
    """
    Apply time-based importance decay.
    Decays proportionally to number of days since last decay.
    """
    now = time.time()
    elapsed_days = (now - entry.last_decayed) / 86400
    if elapsed_days < 0.01:
        return entry  # too soon, skip

    decay_amount = MEMORY["priority_decay_per_day"] * elapsed_days
    entry.importance = max(0.0, entry.importance - decay_amount)
    entry.last_decayed = now
    return entry


def decay_all(entries: list[PriorityEntry]) -> list[PriorityEntry]:
    """Apply decay to all entries."""
    return [decay(e) for e in entries]
