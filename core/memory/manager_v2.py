"""
Memory v2: Unified Manager

Routes all memory operations through the 3-tier system:
  Tier 1: Hot Cache (fast JSON in-memory)
  Tier 2: Vector Store (ChromaDB semantic search)  
  Tier 3: Graph Store (NetworkX relationships)

The manager provides a single API for:
- store()   → routes to appropriate tier(s)
- recall()  → searches across tiers, ranked by token value
- forget()  → removes from all tiers
- relate()  → adds graph relationships
- search()  → semantic search across all tiers
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from runtime.config.config import MEMORY_V2, ENCRYPTION_KEY_FILE
from core.intelligence.token import Token, SpecificityTier, ConfirmationTier
from core.intelligence.scorer import TokenScorer
from core.memory.hot_cache import HotCache
from core.memory.vector_store import VectorStore
from core.memory.graph_store import GraphStore
from core.memory.memory_scorer import MemoryScorer
from core.memory.evictor import Evictor
from core.memory.decay import DecayEngine


@dataclass
class MemoryResult:
    """Result from a memory operation."""
    success: bool
    tier: str              # "hot" | "vector" | "graph" | "all"
    action: str            # "store" | "recall" | "forget" | "relate" | "search"
    data: Any = None
    message: str = ""


@dataclass
class SearchResult:
    """Aggregated search results across tiers, scored and ranked."""
    tokens: list[Token] = field(default_factory=list)
    sources: dict[str, int] = field(default_factory=dict)  # tier → count

    @property
    def total(self) -> int:
        return len(self.tokens)

    @property
    def best(self) -> Optional[Token]:
        return self.tokens[0] if self.tokens else None


class MemoryManagerV2:
    """
    Unified memory manager for the 3-tier system.
    """

    def __init__(self):
        self._scorer = TokenScorer()
        self._memory_scorer = MemoryScorer(self._scorer)

        # Tier 1: Hot Cache
        self._hot = HotCache(
            max_entries=MEMORY_V2.get("hot_cache_max_entries", 500),
            persist_path=MEMORY_V2.get("hot_cache_file"),
            scorer=self._scorer,
        )

        # Tier 2: Vector Store
        self._vector = VectorStore(
            persist_dir=MEMORY_V2.get("vector_db_path", ""),
            collection_name=MEMORY_V2.get("vector_collection", "quarky_memory"),
            max_entries=MEMORY_V2.get("vector_max_entries", 50000),
        )

        # Tier 3: Graph Store
        self._graph = GraphStore(
            persist_path=MEMORY_V2.get("graph_file"),
            max_nodes=MEMORY_V2.get("graph_max_nodes", 100000),
        )

        # Eviction engine
        self._evictor = Evictor(
            scorer=self._scorer,
            check_interval=MEMORY_V2.get("eviction_check_interval", 600),
            batch_size=MEMORY_V2.get("eviction_batch_size", 50),
        )

        # Decay engine
        self._decay = DecayEngine(
            interval_seconds=MEMORY_V2.get("decay_interval_seconds", 300),
        )

    # ── Store ───────────────────────────────────────────────

    def store(
        self,
        text: str,
        source: str = "user",
        importance: float = 0.5,
        specificity: SpecificityTier = SpecificityTier.GG,
        confirmation: ConfirmationTier = ConfirmationTier.UNVERIFIED,
        topic: str = "",
        tags: list[str] | None = None,
        related_to: list[str] | None = None,
    ) -> Token:
        """
        Store information across tiers.
        - Always goes to hot cache
        - Always goes to vector store (for semantic search)
        - If related_to is provided, creates graph edges
        """
        token = Token(
            text=text,
            source=source,
            importance=importance,
            specificity=specificity,
            confirmation=confirmation,
            topic=topic,
            tags=tags or [],
        )

        # Tier 1: Hot cache
        self._hot.put(token)

        # Tier 2: Vector store
        self._vector.add(token)

        # Tier 3: Graph relationships
        if topic:
            self._graph.add_node(token.id, label=text[:100], topic=topic)
            self._graph.add_edge(token.id, topic, "belongs_to")

        if related_to:
            self._graph.add_node(token.id, label=text[:100])
            for related_id in related_to:
                self._graph.add_edge(token.id, related_id, "related_to")

        return token

    def store_token(self, token: Token, related_to: list[str] | None = None) -> None:
        """Store a pre-built token across tiers."""
        self._hot.put(token)
        self._vector.add(token)

        if token.topic:
            self._graph.add_node(token.id, label=token.text[:100], topic=token.topic)
            self._graph.add_edge(token.id, token.topic, "belongs_to")

        if related_to:
            self._graph.add_node(token.id, label=token.text[:100])
            for rid in related_to:
                self._graph.add_edge(token.id, rid, "related_to")

    # ── Recall ──────────────────────────────────────────────

    def recall(self, token_id: str) -> Optional[Token]:
        """Recall a specific token by ID. Checks hot cache first."""
        token = self._hot.get(token_id)
        if token:
            return token
        return None

    # ── Search ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        topic: str | None = None,
    ) -> SearchResult:
        """
        Search across all tiers and merge results.
        Hot cache: text search
        Vector store: semantic search
        Graph: relationship-based expansion
        """
        result = SearchResult()
        seen_ids: set[str] = set()

        # Tier 1: Hot cache text search
        hot_results = self._hot.search_text(query, top_k=top_k)
        for token in hot_results:
            if token.id not in seen_ids:
                result.tokens.append(token)
                seen_ids.add(token.id)
        result.sources["hot"] = len(hot_results)

        # Tier 2: Vector semantic search
        vector_results = self._vector.search(query, top_k=top_k, topic_filter=topic)
        for token_id, distance, meta in vector_results:
            if token_id not in seen_ids:
                # Reconstruct a lightweight token from metadata
                token = Token(
                    id=token_id,
                    text=meta.get("text", ""),
                    source=meta.get("source", "vector"),
                    importance=meta.get("importance", 0.5),
                    topic=meta.get("topic", ""),
                )
                result.tokens.append(token)
                seen_ids.add(token_id)
        result.sources["vector"] = len(vector_results)

        # Re-rank all results by token score
        result.tokens = self._scorer.rank(result.tokens, top_k=top_k)

        return result

    # ── Relate ──────────────────────────────────────────────

    def relate(self, source_id: str, target_id: str, relation: str) -> None:
        """Create a relationship in the knowledge graph."""
        self._graph.add_edge(source_id, target_id, relation)

    def get_related(self, token_id: str) -> list[tuple[str, str, dict]]:
        """Get all relationships for a token."""
        return self._graph.get_neighbors(token_id)

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """Find reasoning path between two concepts."""
        return self._graph.find_path(source_id, target_id)

    # ── Forget ──────────────────────────────────────────────

    def forget(self, token_id: str) -> MemoryResult:
        """Remove a token from all tiers."""
        self._hot.remove(token_id)
        self._vector.remove(token_id)
        self._graph.remove_node(token_id)
        return MemoryResult(True, "all", "forget", message=f"Forgotten {token_id}")

    # ── Lifecycle ───────────────────────────────────────────

    def start(self) -> None:
        """Start background services (decay, eviction)."""
        self._decay.start(self._hot.all_tokens)
        self._evictor.start_periodic(self._run_eviction)

    def stop(self) -> None:
        """Stop background services."""
        self._decay.stop()
        self._evictor.stop_periodic()

    def save(self) -> None:
        """Persist all tiers."""
        self._hot.save()
        self._graph.save()

    def _run_eviction(self) -> list[Token]:
        """Eviction pass: remove lowest-scored from hot cache."""
        tokens = self._hot.all_tokens()
        max_keep = MEMORY_V2.get("hot_cache_max_entries", 500)
        evicted = self._evictor.evict_from_list(tokens, max_keep=max_keep)
        for token in evicted:
            self._hot.remove(token.id)
        return evicted

    # ── Stats ───────────────────────────────────────────────

    def stats(self) -> dict:
        """Memory system statistics."""
        return {
            "hot_cache_count": self._hot.count,
            "vector_store_count": self._vector.count,
            "graph_nodes": self._graph.node_count,
            "graph_edges": self._graph.edge_count,
        }
