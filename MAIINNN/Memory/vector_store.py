"""
Memory v2: Vector Store (Tier 2)

ChromaDB-backed semantic search for long-term knowledge.
Stores token embeddings for similarity search.
Falls back to a simple in-memory dictionary if ChromaDB is unavailable.

Features:
- Semantic similarity search (cosine distance)
- Metadata filtering
- Automatic embedding generation
- Batch operations for efficiency
"""

from __future__ import annotations

import threading
from typing import Optional

from MAIINNN.Intelligence.token import Token


# ── Lazy ChromaDB loading ───────────────────────────────────
_client = None
_collection = None
_chroma_available = True
_init_lock = threading.Lock()


def _init_chroma(persist_dir: str, collection_name: str):
    """Initialize ChromaDB client and collection."""
    global _client, _collection, _chroma_available

    if _collection is not None:
        return

    with _init_lock:
        if _collection is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            _client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            ))
            _collection = _client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except (ImportError, Exception):
            _chroma_available = False


class VectorStore:
    """
    Tier 2: ChromaDB-backed semantic vector store.
    Falls back to in-memory brute-force if ChromaDB unavailable.
    """

    def __init__(
        self,
        persist_dir: str = "",
        collection_name: str = "quarky_memory",
        max_entries: int = 50000,
    ):
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._max_entries = max_entries
        self._lock = threading.Lock()

        # Fallback in-memory store
        self._fallback: dict[str, dict] = {}

        if persist_dir:
            _init_chroma(persist_dir, collection_name)

    def add(self, token: Token, embedding: list[float] | None = None) -> None:
        """Add a token to the vector store."""
        emb = embedding or token.embedding
        if not emb:
            # Generate embedding
            from MAIINNN.NLP.embeddings import encode
            emb = encode(token.text)
            if not emb:
                return

        metadata = {
            "text": token.text[:500],
            "source": token.source,
            "topic": token.topic,
            "importance": token.importance,
            "specificity": token.specificity.value,
            "confirmation": token.confirmation.value,
        }

        if _chroma_available and _collection is not None:
            _collection.upsert(
                ids=[token.id],
                embeddings=[emb],
                metadatas=[metadata],
                documents=[token.text],
            )
        else:
            with self._lock:
                self._fallback[token.id] = {
                    "embedding": emb,
                    "metadata": metadata,
                    "text": token.text,
                }

    def add_batch(self, tokens: list[Token], embeddings: list[list[float]] | None = None) -> None:
        """Batch add tokens."""
        if not tokens:
            return

        if embeddings is None:
            from MAIINNN.NLP.embeddings import encode_batch
            texts = [t.text for t in tokens]
            embeddings = encode_batch(texts)

        for token, emb in zip(tokens, embeddings):
            if emb:
                token.embedding = emb
                self.add(token, emb)

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        topic_filter: str | None = None,
    ) -> list[tuple[str, float, dict]]:
        """
        Semantic search. Returns list of (token_id, distance, metadata).
        Lower distance = more similar.
        """
        from MAIINNN.NLP.embeddings import encode
        query_emb = encode(query_text)
        if not query_emb:
            return []

        return self.search_by_embedding(query_emb, top_k, topic_filter)

    def search_by_embedding(
        self,
        embedding: list[float],
        top_k: int = 10,
        topic_filter: str | None = None,
    ) -> list[tuple[str, float, dict]]:
        """Search by pre-computed embedding vector."""
        if _chroma_available and _collection is not None:
            where: dict[str, str] | None = {"topic": topic_filter} if topic_filter else None
            results = _collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._max_entries),
                where=where,  # type: ignore[arg-type]
            )
            if not results or not results["ids"] or not results["ids"][0]:
                return []

            output = []
            for i, token_id in enumerate(results["ids"][0]):
                distances = results.get("distances")
                metadatas = results.get("metadatas")
                distance = distances[0][i] if distances else 0.0
                meta = metadatas[0][i] if metadatas else {}
                output.append((token_id, distance, meta or {}))
            return output
        else:
            return self._fallback_search(embedding, top_k)

    def remove(self, token_id: str) -> None:
        """Remove a token from the vector store."""
        if _chroma_available and _collection is not None:
            try:
                _collection.delete(ids=[token_id])
            except Exception:
                pass
        else:
            with self._lock:
                self._fallback.pop(token_id, None)

    def contains(self, token_id: str) -> bool:
        if _chroma_available and _collection is not None:
            try:
                result = _collection.get(ids=[token_id])
                return bool(result and result["ids"])
            except Exception:
                return False
        return token_id in self._fallback

    @property
    def count(self) -> int:
        if _chroma_available and _collection is not None:
            return _collection.count()
        return len(self._fallback)

    # ── Fallback ────────────────────────────────────────────

    def _fallback_search(
        self,
        query_emb: list[float],
        top_k: int,
    ) -> list[tuple[str, float, dict]]:
        """Brute-force cosine search in fallback store."""
        from MAIINNN.NLP.embeddings import cosine_similarity_dense

        with self._lock:
            items = list(self._fallback.items())

        scored = []
        for token_id, data in items:
            emb = data.get("embedding", [])
            if emb:
                sim = cosine_similarity_dense(query_emb, emb)
                scored.append((token_id, 1.0 - sim, data.get("metadata", {})))

        scored.sort(key=lambda x: x[1])
        return scored[:top_k]
