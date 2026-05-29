"""
Temporary Memory: Intake Department

Stamps incoming data with created_at, expiry, and a unique ID.
Prepares entries for the Store department.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from runtime.config.config import MEMORY


@dataclass
class TempEntry:
    """A single temporary memory entry."""
    id: str
    content: str
    keywords: list[str]
    created_at: float
    expires_at: float
    source: str = ""              # which system stored this
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "keywords": self.keywords,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TempEntry":
        return cls(
            id=d["id"],
            content=d["content"],
            keywords=d.get("keywords", []),
            created_at=d["created_at"],
            expires_at=d["expires_at"],
            source=d.get("source", ""),
            metadata=d.get("metadata", {}),
        )


def create_entry(
    content: str,
    keywords: list[str] | None = None,
    source: str = "",
    ttl_hours: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> TempEntry:
    """
    Create a new temporary memory entry with automatic expiry.

    Args:
        content: The text to remember
        keywords: Search keywords (auto-extracted if None)
        source: Which system stored this
        ttl_hours: Time-to-live in hours (defaults to config)
        metadata: Extra data to attach
    """
    now = time.time()
    ttl = ttl_hours if ttl_hours is not None else MEMORY["temporary_default_ttl_hours"]

    if keywords is None:
        from core.nlp.tokenizer import keyword_tokens
        keywords = keyword_tokens(content)

    return TempEntry(
        id=uuid.uuid4().hex[:12],
        content=content,
        keywords=keywords,
        created_at=now,
        expires_at=now + (ttl * 3600),
        source=source,
        metadata=metadata or {},
    )
