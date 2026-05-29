"""
Flexible Memory: Degrader Department

Further compresses entries over time (lossy).
Drops the original text after a threshold, keeping only the summary.
Runs on decay tick.
"""

import time

from MAIINNN.Memory.flexible import store
from MAIINNN.Memory.flexible.intake import FlexEntry

# After 3 days, drop original text and keep only summary
_DEGRADE_AGE_SECONDS = 3 * 24 * 3600


def run_degradation() -> int:
    """
    Scan all flexible entries. Entries older than threshold
    have their original text stripped (lossy compression).
    Returns number of entries degraded.
    """
    entries = store.load_all()
    now = time.time()
    degraded = 0

    for entry in entries:
        age = now - entry.created_at
        if age > _DEGRADE_AGE_SECONDS and entry.original:
            entry.original = ""
            degraded += 1

    if degraded > 0:
        store.save_all(entries)

    return degraded
