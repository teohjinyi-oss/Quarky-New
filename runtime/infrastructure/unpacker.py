"""
Infrastructure: Unpacker

Reassembles chunked packets back into the original payload.
Handles out-of-order arrival and missing chunks.
"""

import json
import threading
from typing import Any, Optional


class UnpackBuffer:
    """
    Collects chunks for a single packet_id and reassembles when complete.
    Thread-safe.
    """

    def __init__(self, packet_id: str, total: int):
        self.packet_id = packet_id
        self.total = total
        self._chunks: dict[int, str] = {}
        self._lock = threading.Lock()

    def add_chunk(self, seq: int, data: str) -> bool:
        """
        Add a chunk. Returns True if all chunks now received.
        """
        with self._lock:
            self._chunks[seq] = data
            return len(self._chunks) == self.total

    def reassemble(self) -> str:
        """Reassemble all chunks in order. Call only after all received."""
        with self._lock:
            parts = [self._chunks[i] for i in range(self.total)]
            return "".join(parts)

    @property
    def is_complete(self) -> bool:
        with self._lock:
            return len(self._chunks) == self.total

    @property
    def received_count(self) -> int:
        return len(self._chunks)


class Unpacker:
    """
    Global unpacker — manages reassembly buffers for all in-flight packets.
    Thread-safe singleton.
    """

    _instance: Optional["Unpacker"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Unpacker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._buffers: dict[str, UnpackBuffer] = {}
        self._buf_lock = threading.Lock()

    def receive_chunk(self, chunk: dict) -> Optional[Any]:
        """
        Receive a chunk dict. Returns the reassembled payload if
        all chunks for this packet are now received, else None.

        Chunk format: {packet_id, seq, total, data, is_final}
        """
        pid = chunk["packet_id"]
        seq = chunk["seq"]
        total = chunk["total"]
        data = chunk["data"]

        # Single-chunk packet — return immediately
        if total == 1:
            return self._deserialize(data)

        with self._buf_lock:
            if pid not in self._buffers:
                self._buffers[pid] = UnpackBuffer(pid, total)
            buf = self._buffers[pid]

        complete = buf.add_chunk(seq, data)

        if complete:
            raw = buf.reassemble()
            with self._buf_lock:
                self._buffers.pop(pid, None)
            return self._deserialize(raw)

        return None

    def _deserialize(self, data: str) -> Any:
        """Try to deserialize JSON, fall back to raw string."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    def pending_packets(self) -> dict[str, int]:
        """Returns {packet_id: received_count} for incomplete packets."""
        with self._buf_lock:
            return {
                pid: buf.received_count
                for pid, buf in self._buffers.items()
            }

    def clear(self):
        """Clear all pending buffers."""
        with self._buf_lock:
            self._buffers.clear()
