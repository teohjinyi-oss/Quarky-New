"""
Generation Backend Interface

Defines the contract every generation backend must satisfy. Keeping this an
explicit, small interface is what makes the backend *pluggable*: a future local
model only needs to implement :meth:`GenerationBackend.generate` and register
itself — nothing else in Quarky has to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationRequest:
    """Everything a backend needs to (optionally) enrich a response.

    ``answer`` is the deterministic answer the rule engine already produced;
    a backend's job is to phrase it more fluently, never to invent new facts.
    """

    query: str
    answer: str = ""
    tier: str = "GG"                                  # SS | GS | SG | GG
    confidence: float = 0.5
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """A backend's output, plus provenance for transparency."""

    text: str
    backend: str = ""
    enriched: bool = False           # True if the backend changed the answer
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class GenerationBackend(ABC):
    """Abstract base for a pluggable generation backend."""

    #: Short stable identifier used by the registry.
    name: str = "backend"

    #: Whether this backend can run in the current environment. A model-backed
    #: backend should override this to report missing weights / dependencies so
    #: the gate can fall back gracefully instead of raising.
    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Produce a (possibly enriched) response for the request."""
        ...
