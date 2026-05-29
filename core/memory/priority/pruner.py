"""
Priority Memory: Pruner Department

Deletes entries that have decayed below the prune threshold.
Runs on decay tick.
"""

from runtime.config.config import MEMORY
from core.memory.priority import store as priority_store


def run_prune() -> int:
    """
    Remove all entries with importance below prune threshold.
    Returns number of entries pruned.
    """
    threshold = MEMORY["priority_prune_threshold"]
    entries = priority_store.load_all()

    alive = [e for e in entries if e.importance >= threshold]
    pruned = len(entries) - len(alive)

    if pruned > 0:
        priority_store.save_all(alive)

    return pruned
