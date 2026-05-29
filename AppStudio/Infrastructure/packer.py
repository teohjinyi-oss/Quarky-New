"""
Infrastructure: Packer

Splits large payloads into fixed-size chunks with sequence IDs.
Prevents any single message from blocking the transport.
Worker-pool capable for parallel packing of big data.
"""

import uuid
import math
from typing import Any

from AppStudio.Config import TRANSPORT


def generate_packet_id() -> str:
    """Generate unique packet group ID."""
    return uuid.uuid4().hex[:12]


def pack(payload: Any, max_chunk_size: int | None = None) -> list[dict]:
    """
    Pack a payload into sequenced chunks.

    Args:
        payload: The data to pack (will be serialized to str if not already)
        max_chunk_size: Override for chunk size (default from config)

    Returns:
        List of chunk dicts, each with:
            - packet_id: group identifier
            - seq: sequence number (0-indexed)
            - total: total number of chunks
            - data: the chunk content
            - is_final: True if last chunk
    """
    chunk_size = max_chunk_size or TRANSPORT["max_chunk_size"]

    # Serialize to string for chunking
    if not isinstance(payload, str):
        import json
        try:
            serialized = json.dumps(payload, default=str)
        except (TypeError, ValueError):
            serialized = str(payload)
    else:
        serialized = payload

    # If small enough, return single chunk (fast path)
    if len(serialized) <= chunk_size:
        pid = generate_packet_id()
        return [{
            "packet_id": pid,
            "seq": 0,
            "total": 1,
            "data": serialized,
            "is_final": True,
        }]

    # Split into chunks
    pid = generate_packet_id()
    total = math.ceil(len(serialized) / chunk_size)
    chunks = []

    for i in range(total):
        start = i * chunk_size
        end = start + chunk_size
        chunks.append({
            "packet_id": pid,
            "seq": i,
            "total": total,
            "data": serialized[start:end],
            "is_final": (i == total - 1),
        })

    return chunks


def needs_packing(payload: Any, threshold: int | None = None) -> bool:
    """Check if a payload is large enough to need packing."""
    threshold = threshold or TRANSPORT["direct_call_max_payload"]
    if isinstance(payload, str):
        return len(payload) > threshold
    if isinstance(payload, (dict, list)):
        import json
        try:
            return len(json.dumps(payload, default=str)) > threshold
        except (TypeError, ValueError):
            return True
    return len(str(payload)) > threshold
