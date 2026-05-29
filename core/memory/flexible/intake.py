"""
Flexible Memory: Intake Department

Receives raw text, extracts keywords, and prepares a FlexEntry
for summarization and storage.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.nlp.tokenizer import keyword_tokens


@dataclass
class FlexEntry:
    """A single flexible memory entry (summary-based)."""
    id: str
    original: str
    summary: str                  # filled by summarizer
    keywords: list[str]
    created_at: float
    last_accessed: float
    access_count: int = 0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original": self.original,
            "summary": self.summary,
            "keywords": self.keywords,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FlexEntry":
        return cls(
            id=d["id"],
            original=d.get("original", ""),
            summary=d.get("summary", ""),
            keywords=d.get("keywords", []),
            created_at=d["created_at"],
            last_accessed=d.get("last_accessed", d["created_at"]),
            access_count=d.get("access_count", 0),
            source=d.get("source", ""),
            metadata=d.get("metadata", {}),
        )


def create_entry(
    content: str,
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> FlexEntry:
    """
    Create a new flexible memory entry.
    Summary is left empty — the Summarizer department fills it.
    """
    now = time.time()
    keywords = keyword_tokens(content)[:15]

    return FlexEntry(
        id=uuid.uuid4().hex[:12],
        original=content,
        summary="",
        keywords=keywords,
        created_at=now,
        last_accessed=now,
        access_count=0,
        source=source,
        metadata=metadata or {},
    )
