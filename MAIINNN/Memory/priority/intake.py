"""
Priority Memory: Intake Department

Receives store requests and assigns initial importance score.
Entries reinforce through access, decay over time.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Config import MEMORY
from MAIINNN.NLP.tokenizer import keyword_tokens


@dataclass
class PriorityEntry:
    """A single priority memory entry with importance tracking."""
    id: str
    content: str
    keywords: list[str]
    importance: float
    created_at: float
    last_accessed: float
    last_decayed: float
    access_count: int = 0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "keywords": self.keywords,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "last_decayed": self.last_decayed,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PriorityEntry":
        return cls(
            id=d["id"],
            content=d["content"],
            keywords=d.get("keywords", []),
            importance=d.get("importance", MEMORY["priority_initial_importance"]),
            created_at=d["created_at"],
            last_accessed=d.get("last_accessed", d["created_at"]),
            last_decayed=d.get("last_decayed", d["created_at"]),
            access_count=d.get("access_count", 0),
            source=d.get("source", ""),
            metadata=d.get("metadata", {}),
        )


def create_entry(
    content: str,
    keywords: list[str] | None = None,
    source: str = "",
    importance: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> PriorityEntry:
    """Create a new priority entry with initial importance."""
    now = time.time()

    if keywords is None:
        keywords = keyword_tokens(content)[:15]

    resolved_importance: float = importance if importance is not None else MEMORY["priority_initial_importance"]

    return PriorityEntry(
        id=uuid.uuid4().hex[:12],
        content=content,
        keywords=keywords,
        importance=resolved_importance,
        created_at=now,
        last_accessed=now,
        last_decayed=now,
        access_count=0,
        source=source,
        metadata=metadata or {},
    )
