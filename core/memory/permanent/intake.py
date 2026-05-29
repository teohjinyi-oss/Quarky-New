"""
Permanent Memory: Intake Department

ONLY accepts explicit user commands ("remember forever").
Creates entries destined for SQLite storage.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.nlp.tokenizer import keyword_tokens


@dataclass
class PermanentEntry:
    """A single permanent memory entry (locked, no auto-delete)."""
    id: str
    content: str
    keywords: list[str]
    tags: list[str]
    created_at: float
    last_accessed: float
    access_count: int = 0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "keywords": self.keywords,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PermanentEntry":
        return cls(
            id=d["id"],
            content=d["content"],
            keywords=d.get("keywords", []),
            tags=d.get("tags", []),
            created_at=d["created_at"],
            last_accessed=d.get("last_accessed", d["created_at"]),
            access_count=d.get("access_count", 0),
            source=d.get("source", ""),
            metadata=d.get("metadata", {}),
        )


def create_entry(
    content: str,
    tags: list[str] | None = None,
    keywords: list[str] | None = None,
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> PermanentEntry:
    """
    Create a permanent entry. Used ONLY for explicit "remember forever"
    or auto-promoted priority entries.
    """
    now = time.time()

    if keywords is None:
        keywords = keyword_tokens(content)[:15]

    return PermanentEntry(
        id=uuid.uuid4().hex[:12],
        content=content,
        keywords=keywords,
        tags=tags or [],
        created_at=now,
        last_accessed=now,
        access_count=0,
        source=source,
        metadata=metadata or {},
    )
