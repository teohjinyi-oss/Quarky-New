"""
Analytical Brain: Reasoner (v2)

Multi-hop reasoning using the knowledge graph.
When pattern matching fails, the reasoner tries to find an answer
by traversing relationships in the graph store.

Example: "What language runs in browsers?" →
  Graph: JavaScript --[runs_in]--> browsers
  Answer: JavaScript
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from AppStudio.Infrastructure.base import Department


@dataclass
class ReasoningStep:
    """One step in a reasoning chain."""
    node: str
    relation: str
    confidence: float = 0.5


@dataclass
class ReasoningResult:
    """Output of the reasoning engine."""
    answer: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    confidence: float = 0.0
    method: str = ""  # "graph_traversal" | "semantic_match" | "none"


class Reasoner(Department):
    """
    Multi-hop reasoning using graph traversal and semantic search.
    """

    def __init__(self):
        super().__init__("reasoner", "core.analytical")
        self._memory_manager = None

    def set_memory(self, memory_manager) -> None:
        """Inject the memory manager for graph/vector access."""
        self._memory_manager = memory_manager

    def process(self, data) -> ReasoningResult:
        """
        Try to reason about a query using knowledge graph.

        Args:
            data: dict with 'query', 'keywords', 'entities'
        """
        if not isinstance(data, dict):
            return ReasoningResult(method="none")

        query = data.get("query", "")
        keywords = data.get("keywords", [])

        if not query:
            return ReasoningResult(method="none")

        # Strategy 1: Graph traversal
        result = self._graph_reason(query, keywords)
        if result.confidence > 0.3:
            return result

        # Strategy 2: Semantic memory search
        result = self._semantic_reason(query)
        if result.confidence > 0.3:
            return result

        return ReasoningResult(method="none")

    def _graph_reason(self, query: str, keywords: list[str]) -> ReasoningResult:
        """Try to find answer by traversing knowledge graph."""
        if not self._memory_manager:
            return ReasoningResult(method="none")

        steps = []

        # Search for keyword nodes in graph
        for kw in keywords[:3]:
            neighbors = self._memory_manager.get_related(kw)
            for neighbor_id, relation, attrs in neighbors:
                steps.append(ReasoningStep(
                    node=neighbor_id,
                    relation=relation,
                    confidence=0.6,
                ))

        if not steps:
            return ReasoningResult(method="graph_traversal", confidence=0.0)

        # Build answer from best path
        best = max(steps, key=lambda s: s.confidence)
        return ReasoningResult(
            answer=f"Based on what I know: {best.node} ({best.relation})",
            steps=steps,
            confidence=best.confidence,
            method="graph_traversal",
        )

    def _semantic_reason(self, query: str) -> ReasoningResult:
        """Try to find answer via semantic memory search."""
        if not self._memory_manager:
            return ReasoningResult(method="none")

        results = self._memory_manager.search(query, top_k=3)
        if not results.tokens:
            return ReasoningResult(method="semantic_match", confidence=0.0)

        best = results.best
        if best is None:
            return ReasoningResult(method="semantic_match", confidence=0.0)

        return ReasoningResult(
            answer=best.text,
            steps=[ReasoningStep(
                node=best.id,
                relation="semantic_match",
                confidence=best.importance,
            )],
            confidence=min(0.7, best.importance),
            method="semantic_match",
        )
