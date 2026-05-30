"""
Quarky Local Knowledge Cache (Phase 3)

A private, offline, citation-aware knowledge store that grows as Quarky learns,
so repeat questions are answered locally instead of re-hitting the web.

Public API::

    from core.knowledge import KnowledgeStore

    kb = KnowledgeStore()
    kb.add("The capital of France is Paris.", source="wikipedia")
    print(kb.answer("What is the capital of France?"))
    # → "The capital of France is Paris. [source: wikipedia]"
"""

from core.knowledge.store import (
    KnowledgeEntry,
    KnowledgeHit,
    KnowledgeStore,
)

__all__ = [
    "KnowledgeEntry",
    "KnowledgeHit",
    "KnowledgeStore",
]
