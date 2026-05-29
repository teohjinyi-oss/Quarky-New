"""
Infrastructure: JSON-over-TCP Protocol (v2)

Defines the message format and types for Java GUI ↔ Python backend
communication. All messages are JSON with a fixed header structure.

Message types:
- CHAT        — User text → response text
- ACTION      — Execute an action (open app, set volume, etc.)
- STATUS      — System status request/response
- STREAM      — Streaming response (for long answers)
- MEMORY_QUERY — Search/browse memory
- NOTIFICATION — Push notification to GUI
- HEARTBEAT   — Keep-alive ping/pong
- VOICE_STATE — Voice pipeline state changes
- SETTINGS    — Settings read/write

Wire format:
  [4 bytes: message length (big-endian uint32)]
  [JSON payload]
"""

from __future__ import annotations

import json
import struct
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """Protocol message types."""
    CHAT = "CHAT"
    ACTION = "ACTION"
    STATUS = "STATUS"
    STREAM = "STREAM"
    MEMORY_QUERY = "MEMORY_QUERY"
    NOTIFICATION = "NOTIFICATION"
    HEARTBEAT = "HEARTBEAT"
    VOICE_STATE = "VOICE_STATE"
    SETTINGS = "SETTINGS"
    ERROR = "ERROR"


@dataclass
class ProtocolMessage:
    """
    Standard message format for the TCP protocol.
    Both GUI→Backend and Backend→GUI use this format.
    """
    type: MessageType
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reply_to: str = ""              # ID of message this replies to
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "id": self.id,
            "reply_to": self.reply_to,
            "ts": self.timestamp,
            "payload": self.payload,
        }, ensure_ascii=False)

    def to_bytes(self) -> bytes:
        """Serialize to wire format: [4-byte length][JSON]."""
        json_bytes = self.to_json().encode("utf-8")
        length = struct.pack(">I", len(json_bytes))
        return length + json_bytes

    @classmethod
    def from_json(cls, data: str) -> ProtocolMessage:
        """Deserialize from JSON string."""
        obj = json.loads(data)
        return cls(
            type=MessageType(obj["type"]),
            payload=obj.get("payload", {}),
            id=obj.get("id", uuid.uuid4().hex[:12]),
            reply_to=obj.get("reply_to", ""),
            timestamp=obj.get("ts", time.time()),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> ProtocolMessage:
        """Deserialize from wire format."""
        if len(data) < 4:
            raise ValueError("Message too short")
        length = struct.unpack(">I", data[:4])[0]
        json_str = data[4:4 + length].decode("utf-8")
        return cls.from_json(json_str)


# ── Factory functions for common message types ──────────────

def chat_request(text: str, context: dict | None = None) -> ProtocolMessage:
    """Create a chat request message (GUI → Backend)."""
    return ProtocolMessage(
        type=MessageType.CHAT,
        payload={"text": text, "context": context or {}},
    )


def chat_response(text: str, reply_to: str, confidence: float = 0.0,
                  metadata: dict | None = None) -> ProtocolMessage:
    """Create a chat response message (Backend → GUI)."""
    return ProtocolMessage(
        type=MessageType.CHAT,
        payload={
            "text": text,
            "confidence": confidence,
            "metadata": metadata or {},
        },
        reply_to=reply_to,
    )


def stream_chunk(text: str, reply_to: str, done: bool = False) -> ProtocolMessage:
    """Create a streaming response chunk."""
    return ProtocolMessage(
        type=MessageType.STREAM,
        payload={"text": text, "done": done},
        reply_to=reply_to,
    )


def action_request(action: str, params: dict | None = None) -> ProtocolMessage:
    """Create an action request."""
    return ProtocolMessage(
        type=MessageType.ACTION,
        payload={"action": action, "params": params or {}},
    )


def action_response(success: bool, result: str, reply_to: str) -> ProtocolMessage:
    """Create an action response."""
    return ProtocolMessage(
        type=MessageType.ACTION,
        payload={"success": success, "result": result},
        reply_to=reply_to,
    )


def status_request() -> ProtocolMessage:
    """Request system status."""
    return ProtocolMessage(type=MessageType.STATUS)


def status_response(stats: dict, reply_to: str) -> ProtocolMessage:
    """Send system status."""
    return ProtocolMessage(
        type=MessageType.STATUS,
        payload=stats,
        reply_to=reply_to,
    )


def notification(title: str, body: str, priority: str = "info") -> ProtocolMessage:
    """Push a notification to GUI."""
    return ProtocolMessage(
        type=MessageType.NOTIFICATION,
        payload={"title": title, "body": body, "priority": priority},
    )


def heartbeat() -> ProtocolMessage:
    """Keep-alive heartbeat."""
    return ProtocolMessage(
        type=MessageType.HEARTBEAT,
        payload={"ping": True},
    )


def heartbeat_response(reply_to: str) -> ProtocolMessage:
    """Heartbeat response."""
    return ProtocolMessage(
        type=MessageType.HEARTBEAT,
        payload={"pong": True},
        reply_to=reply_to,
    )


def voice_state(state: str, transcription: str = "") -> ProtocolMessage:
    """Voice pipeline state change notification."""
    return ProtocolMessage(
        type=MessageType.VOICE_STATE,
        payload={"state": state, "transcription": transcription},
    )


def error_response(message: str, reply_to: str = "") -> ProtocolMessage:
    """Error response."""
    return ProtocolMessage(
        type=MessageType.ERROR,
        payload={"error": message},
        reply_to=reply_to,
    )


def memory_query(query: str, top_k: int = 10) -> ProtocolMessage:
    """Memory search query."""
    return ProtocolMessage(
        type=MessageType.MEMORY_QUERY,
        payload={"query": query, "top_k": top_k},
    )


def settings_message(action: str = "get", settings: dict | None = None) -> ProtocolMessage:
    """Settings read/write."""
    return ProtocolMessage(
        type=MessageType.SETTINGS,
        payload={"action": action, "settings": settings or {}},
    )


# ── Wire helpers ────────────────────────────────────────────

def read_message_from_buffer(buffer: bytes) -> tuple[Optional[ProtocolMessage], bytes]:
    """
    Try to read a complete message from a byte buffer.
    Returns (message, remaining_buffer) or (None, buffer) if incomplete.
    """
    if len(buffer) < 4:
        return None, buffer

    length = struct.unpack(">I", buffer[:4])[0]
    if length > 1_048_576:  # 1 MB max
        raise ValueError(f"Message too large: {length} bytes")

    total = 4 + length
    if len(buffer) < total:
        return None, buffer

    msg = ProtocolMessage.from_bytes(buffer[:total])
    return msg, buffer[total:]
