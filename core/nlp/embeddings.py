"""
NLP: Sentence Embeddings (v2)

Uses sentence-transformers (all-MiniLM-L6-v2) for dense vector embeddings.
Falls back to bag-of-words cosine similarity if sentence-transformers is
not available (e.g., during tests without GPU).

Provides:
- encode(): text → dense float vector
- similarity(): cosine similarity between two texts
- encode_batch(): batch encoding for efficiency
- bow fallback for lightweight environments
"""

from __future__ import annotations

import math
import threading
from functools import lru_cache
from typing import Optional

from core.nlp.tokenizer import keyword_tokens


# ── Lazy model loading ──────────────────────────────────────
_model = None
_model_lock = threading.Lock()
_USE_TRANSFORMER = True  # disabled on import failure


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model, _USE_TRANSFORMER
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            return _model
        except ImportError:
            _USE_TRANSFORMER = False
            return None


def encode(text: str) -> list[float]:
    """
    Encode text into a dense embedding vector.
    Returns 384-dim float list (MiniLM) or sparse BoW fallback.
    """
    if not text or not text.strip():
        return []
    return _encode_cached(text)


@lru_cache(maxsize=1024)
def _encode_cached(text: str) -> list[float]:
    """Cached embedding computation — avoids re-encoding identical strings."""
    model = _get_model()
    if model is not None:
        vec = model.encode(text, show_progress_bar=False)
        return vec.tolist()

    # Fallback: normalized BoW vector
    return _bow_dense(text)


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts efficiently in one call."""
    if not texts:
        return []

    model = _get_model()
    if model is not None:
        vecs = model.encode(texts, show_progress_bar=False, batch_size=32)
        return [v.tolist() for v in vecs]

    return [_bow_dense(t) for t in texts]


def similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using embeddings."""
    vec_a = encode(text_a)
    vec_b = encode(text_b)
    if not vec_a or not vec_b:
        return 0.0
    return cosine_similarity_dense(vec_a, vec_b)


def cosine_similarity_dense(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two dense vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def is_transformer_available() -> bool:
    """Check if sentence-transformers loaded successfully."""
    _get_model()
    return _USE_TRANSFORMER


# ── Bag-of-Words Fallback ───────────────────────────────────

def bow_vector(text: str, vocabulary: list[str] | None = None) -> dict[str, int]:
    """Bag-of-words sparse vector: word → count."""
    tokens = keyword_tokens(text)
    vec: dict[str, int] = {}
    for t in tokens:
        if vocabulary is None or t in vocabulary:
            vec[t] = vec.get(t, 0) + 1
    return vec


def cosine_similarity_sparse(
    vec_a: dict[str, float],
    vec_b: dict[str, float],
) -> float:
    """Cosine similarity between two sparse vectors (dicts)."""
    keys = set(vec_a.keys()) | set(vec_b.keys())
    if not keys:
        return 0.0

    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def text_similarity(text_a: str, text_b: str) -> float:
    """
    Quick text similarity — uses transformer embeddings if available,
    falls back to BoW cosine.
    """
    if _USE_TRANSFORMER or _model is not None:
        return similarity(text_a, text_b)
    vec_a: dict[str, float] = {k: float(v) for k, v in bow_vector(text_a).items()}
    vec_b: dict[str, float] = {k: float(v) for k, v in bow_vector(text_b).items()}
    return cosine_similarity_sparse(vec_a, vec_b)


def _bow_dense(text: str, dim: int = 64) -> list[float]:
    """
    Convert text to a fixed-size dense vector using hashing trick.
    Used as fallback when sentence-transformers is not available.
    """
    tokens = keyword_tokens(text)
    vec = [0.0] * dim
    for token in tokens:
        idx = hash(token) % dim
        vec[idx] += 1.0

    # Normalize
    mag = math.sqrt(sum(v * v for v in vec))
    if mag > 0:
        vec = [v / mag for v in vec]
    return vec
