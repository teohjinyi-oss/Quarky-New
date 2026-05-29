"""
Temporary Memory: Cleanup Department

Scans and removes expired entries. Runs on decay tick.
"""

import time

from MAIINNN.Memory.temporary import store


def run_cleanup() -> int:
    """
    Remove all expired entries.
    Returns the number of entries removed.
    """
    entries = store.load_all()
    now = time.time()

    alive = [e for e in entries if e.expires_at > now]
    removed = len(entries) - len(alive)

    if removed > 0:
        store.save_all(alive)

    return removed
