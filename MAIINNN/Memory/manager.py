"""
Memory Manager — Coordinator

Routes store/recall/forget to the correct layer.
Cross-layer search (permanent first → temporary last).
Decay engine runs cleanup, pruner, and degrader on a periodic tick.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Config import MEMORY

# Layer imports — temporary
from MAIINNN.Memory.temporary import intake as temp_intake
from MAIINNN.Memory.temporary import store as temp_store
from MAIINNN.Memory.temporary import cleanup as temp_cleanup
from MAIINNN.Memory.temporary import retriever as temp_retriever

# Layer imports — flexible
from MAIINNN.Memory.flexible import intake as flex_intake
from MAIINNN.Memory.flexible import summarizer as flex_summarizer
from MAIINNN.Memory.flexible import store as flex_store
from MAIINNN.Memory.flexible import fuzzy_retriever as flex_retriever
from MAIINNN.Memory.flexible import degrader as flex_degrader

# Layer imports — priority
from MAIINNN.Memory.priority import intake as prio_intake
from MAIINNN.Memory.priority import store as prio_store
from MAIINNN.Memory.priority import scorer as prio_scorer
from MAIINNN.Memory.priority import promoter as prio_promoter
from MAIINNN.Memory.priority import pruner as prio_pruner
from MAIINNN.Memory.priority import retriever as prio_retriever

# Layer imports — permanent
from MAIINNN.Memory.permanent import intake as perm_intake
from MAIINNN.Memory.permanent import store as perm_store
from MAIINNN.Memory.permanent import retriever as perm_retriever
from MAIINNN.Memory.permanent import guard as perm_guard


# ── Data Classes ─────────────────────────────────────────────

@dataclass
class MemoryResult:
    """Result from a memory operation (store, recall, forget)."""
    success: bool
    layer: str           # "temporary" | "flexible" | "priority" | "permanent"
    action: str          # "store" | "recall" | "forget"
    data: Any = None
    message: str = ""


@dataclass
class SearchResult:
    """Aggregated cross-layer search result."""
    permanent: list = field(default_factory=list)
    priority: list = field(default_factory=list)
    flexible: list = field(default_factory=list)
    temporary: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return (len(self.permanent) + len(self.priority)
                + len(self.flexible) + len(self.temporary))

    @property
    def best(self) -> Any | None:
        """Return the single best result (permanent > priority > flex > temp)."""
        for layer in [self.permanent, self.priority,
                      self.flexible, self.temporary]:
            if layer:
                return layer[0]
        return None


# ── Router ───────────────────────────────────────────────────

def store_temporary(content: str, source: str = "",
                    ttl_hours: float | None = None,
                    metadata: dict | None = None) -> MemoryResult:
    """Store in temporary layer (auto-expires)."""
    entry = temp_intake.create_entry(
        content=content, source=source,
        ttl_hours=ttl_hours, metadata=metadata,
    )
    temp_store.save_entry(entry)
    return MemoryResult(True, "temporary", "store", entry.id,
                        "Stored in temporary memory")


def store_flexible(content: str, source: str = "",
                   metadata: dict | None = None) -> MemoryResult:
    """Store in flexible layer (summarized)."""
    entry = flex_intake.create_entry(content=content, source=source,
                                     metadata=metadata)
    entry = flex_summarizer.summarize_entry(entry)
    flex_store.save_entry(entry)
    return MemoryResult(True, "flexible", "store", entry.id,
                        "Stored in flexible memory (summarized)")


def store_priority(content: str, source: str = "",
                   importance: float | None = None,
                   metadata: dict | None = None) -> MemoryResult:
    """Store in priority layer (importance-scored)."""
    entry = prio_intake.create_entry(
        content=content, source=source,
        importance=importance, metadata=metadata,
    )
    prio_store.save_entry(entry)
    return MemoryResult(True, "priority", "store", entry.id,
                        "Stored in priority memory")


def store_permanent(content: str, tags: list[str] | None = None,
                    source: str = "",
                    metadata: dict | None = None) -> MemoryResult:
    """Store in permanent layer (locked, no auto-delete)."""
    entry = perm_intake.create_entry(
        content=content, tags=tags,
        source=source, metadata=metadata,
    )
    perm_store.save_entry(entry)
    return MemoryResult(True, "permanent", "store", entry.id,
                        "Stored in permanent memory")


# ── Cross-Layer Search ───────────────────────────────────────

def recall(keywords: list[str], max_per_layer: int = 5) -> SearchResult:
    """
    Search all 4 layers. Returns results organized by layer.
    Priority order: permanent → priority → flexible → temporary.
    """
    result = SearchResult()
    result.permanent = perm_retriever.search(keywords, max_per_layer)
    result.priority = prio_retriever.search(keywords, max_per_layer)
    result.flexible = flex_retriever.search(keywords, max_per_layer)
    result.temporary = temp_retriever.search(keywords, max_per_layer)
    return result


def recall_best(keywords: list[str]) -> Any | None:
    """Return the single best match across all layers."""
    return recall(keywords, max_per_layer=1).best


# ── Forget ───────────────────────────────────────────────────

def forget_temporary(entry_id: str) -> MemoryResult:
    ok = temp_store.delete_entry(entry_id)
    return MemoryResult(ok, "temporary", "forget",
                        message="Deleted" if ok else "Not found")


def forget_flexible(entry_id: str) -> MemoryResult:
    ok = flex_store.delete_entry(entry_id)
    return MemoryResult(ok, "flexible", "forget",
                        message="Deleted" if ok else "Not found")


def forget_priority(entry_id: str) -> MemoryResult:
    ok = prio_store.delete_entry(entry_id)
    return MemoryResult(ok, "priority", "forget",
                        message="Deleted" if ok else "Not found")


def forget_permanent(entry_id: str, user_confirmed: bool = False) -> MemoryResult:
    """Permanent deletion REQUIRES user confirmation."""
    if not perm_guard.can_delete(user_confirmed):
        return MemoryResult(False, "permanent", "forget",
                            message=perm_guard.block_auto_delete())
    ok = perm_store.delete_entry(entry_id, user_confirmed=True)
    return MemoryResult(ok, "permanent", "forget",
                        message="Deleted" if ok else "Not found")


# ── Decay Engine ─────────────────────────────────────────────

_decay_thread: threading.Thread | None = None
_decay_running = False


@dataclass
class DecayReport:
    """Summary of a single decay tick."""
    temporary_cleaned: int = 0
    flexible_degraded: int = 0
    priority_decayed: int = 0
    priority_pruned: int = 0
    priority_promoted: int = 0


def _run_decay_tick() -> DecayReport:
    """Execute one decay cycle across all layers."""
    report = DecayReport()

    # 1. Temporary: remove expired
    report.temporary_cleaned = temp_cleanup.run_cleanup()

    # 2. Flexible: degrade old entries
    report.flexible_degraded = flex_degrader.run_degradation()

    # 3. Priority: decay importance + prune + promote
    prio_entries = prio_store.load_all()
    prio_scorer.decay_all(prio_entries)
    prio_store.save_all(prio_entries)
    report.priority_decayed = len(prio_entries)

    report.priority_pruned = prio_pruner.run_prune()

    promoted = prio_promoter.check_promotions()
    report.priority_promoted = len(promoted)

    # Move promoted entries to permanent
    for p_entry in promoted:
        perm_entry = perm_intake.create_entry(
            content=p_entry.content,
            tags=["auto-promoted"],
            keywords=p_entry.keywords,
            source="priority_promotion",
        )
        perm_store.save_entry(perm_entry)

    return report


def _decay_loop() -> None:
    """Background loop that runs decay at configured interval."""
    global _decay_running
    interval = MEMORY["decay_interval_seconds"]

    while _decay_running:
        _run_decay_tick()
        # Sleep in small increments so we can stop quickly
        for _ in range(int(interval)):
            if not _decay_running:
                break
            time.sleep(1)


def start_decay_engine() -> None:
    """Start the background decay engine thread."""
    global _decay_thread, _decay_running

    if _decay_running:
        return

    _decay_running = True
    _decay_thread = threading.Thread(target=_decay_loop, daemon=True,
                                     name="MemoryDecayEngine")
    _decay_thread.start()


def stop_decay_engine() -> None:
    """Stop the background decay engine."""
    global _decay_running
    _decay_running = False


def run_decay_once() -> DecayReport:
    """Run a single decay tick (for manual / testing use)."""
    return _run_decay_tick()


# ── Stats ────────────────────────────────────────────────────

def stats() -> dict[str, int]:
    """Get entry counts across all layers."""
    return {
        "temporary": temp_store.count(),
        "flexible": flex_store.count(),
        "priority": prio_store.count(),
        "permanent": perm_store.count(),
    }
