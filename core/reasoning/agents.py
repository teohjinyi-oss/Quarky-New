"""
Multi-Agent Reasoning: Agent Adapters

Four specialised agents each generate an independent reasoning path as an
``AgentOutput``. Agents are intentionally lightweight and dependency-free so the
reasoning stack runs without heavy models; when a ``memory_manager`` (or other
capability) is injected via ``context`` they enrich their output with it.

  - LogicAgent       formal reasoning, correctness checking
  - CreativityAgent  hypothesis generation, exploration
  - EvidenceAgent    supports claims with known data
  - MemoryAgent      retrieves past context and patterns
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Any

from core.nlp.tokenizer import keyword_tokens
from core.reasoning.types import AgentOutput


class ReasoningAgent(ABC):
    """Base class for a reasoning agent producing one structured path."""

    name: str = "agent"

    @abstractmethod
    def _reason(self, query: str, context: dict[str, Any]) -> AgentOutput:
        """Produce an AgentOutput for the query. Override in subclass."""
        ...

    def reason(self, query: str, context: dict[str, Any] | None = None) -> AgentOutput:
        """Time-wrapped entry point used by the dispatcher."""
        ctx = context or {}
        start = time.perf_counter()
        try:
            out = self._reason(query, ctx)
        except Exception as exc:  # never let one agent break the panel
            out = AgentOutput(
                agent=self.name,
                response="",
                confidence=0.0,
                reasoning_trace=[f"{self.name} failed: {exc}"],
            )
        out.duration_ms = (time.perf_counter() - start) * 1000.0
        return out


# ─── Logic Agent ─────────────────────────────────────────────

_NEGATION = re.compile(r"\b(not|no|never|cannot|can't|isn't|aren't|won't)\b", re.I)
_COMPARATIVE = re.compile(r"\b(more|less|greater|fewer|better|worse|than)\b", re.I)


class LogicAgent(ReasoningAgent):
    """Formal reasoning and correctness checking via deterministic heuristics."""

    name = "logic"

    def _reason(self, query: str, context: dict[str, Any]) -> AgentOutput:
        keywords = keyword_tokens(query)
        trace = [f"Parsed {len(keywords)} key concepts"]
        claims: list[str] = []
        assumptions: list[str] = []

        polarity = "negative" if _NEGATION.search(query) else "positive"
        trace.append(f"Polarity: {polarity}")
        assumptions.append("Query is well-formed and self-consistent")

        if _COMPARATIVE.search(query):
            trace.append("Comparative structure detected")
            claims.append(f"The relation in '{query.strip()}' is comparative ({polarity}).")
            confidence = 0.7
        elif keywords:
            subject = keywords[0]
            claims.append(f"'{subject}' is the logical subject of the query ({polarity}).")
            confidence = 0.65 if len(keywords) >= 2 else 0.5
        else:
            confidence = 0.2

        # A logic agent may optionally consult a structured engine if provided.
        engine = context.get("logic_engine")
        if engine is not None and hasattr(engine, "evaluate"):
            try:
                verdict = engine.evaluate(query)
                if verdict:
                    claims.append(str(verdict))
                    confidence = min(1.0, confidence + 0.1)
                    trace.append("External logic engine consulted")
            except Exception:
                trace.append("External logic engine unavailable")

        response = claims[0] if claims else "No formal claim could be derived."
        return AgentOutput(
            agent=self.name,
            response=response,
            confidence=round(confidence, 4),
            claims=claims,
            assumptions=assumptions,
            reasoning_trace=trace,
            metadata={"polarity": polarity, "keywords": keywords},
        )


# ─── Creativity Agent ────────────────────────────────────────

class CreativityAgent(ReasoningAgent):
    """Hypothesis generation and exploration; deliberately divergent."""

    name = "creativity"

    def _reason(self, query: str, context: dict[str, Any]) -> AgentOutput:
        keywords = keyword_tokens(query)
        trace = ["Generating exploratory hypotheses"]
        claims: list[str] = []
        assumptions = ["Novel associations may be useful even if unverified"]

        if keywords:
            primary = keywords[0]
            claims.append(f"Hypothesis: '{primary}' could relate to an unexplored angle.")
            if len(keywords) >= 2:
                claims.append(
                    f"What if '{keywords[0]}' and '{keywords[1]}' are connected?"
                )
            trace.append(f"Seeded {len(claims)} hypotheses from key concepts")
            confidence = 0.45
        else:
            claims.append("Open-ended exploration: the question invites broad framing.")
            confidence = 0.3

        # Optional concept expansion if a blender is supplied.
        blender = context.get("concept_blender")
        if blender is not None and hasattr(blender, "blend") and keywords:
            try:
                blend = blender.blend(keywords)
                idea = getattr(blend, "idea", "") or getattr(blend, "summary", "")
                if idea:
                    claims.append(f"Blended idea: {idea}")
                    trace.append("Concept blender produced a novel combination")
            except Exception:
                trace.append("Concept blender unavailable")

        return AgentOutput(
            agent=self.name,
            response=claims[0],
            confidence=round(confidence, 4),
            claims=claims,
            assumptions=assumptions,
            reasoning_trace=trace,
            metadata={"exploratory": True, "keywords": keywords},
        )


# ─── Evidence Agent ──────────────────────────────────────────

class EvidenceAgent(ReasoningAgent):
    """Supports claims with known data, primarily from the memory manager."""

    name = "evidence"

    def _reason(self, query: str, context: dict[str, Any]) -> AgentOutput:
        trace = ["Searching for supporting evidence"]
        evidence: list[str] = []
        claims: list[str] = []
        assumptions = ["Stored knowledge is trustworthy unless contradicted"]
        confidence = 0.2

        memory = context.get("memory_manager")
        if memory is not None and hasattr(memory, "search"):
            try:
                results = memory.search(query, top_k=3)
                tokens = getattr(results, "tokens", None) or []
                for tok in tokens:
                    text = getattr(tok, "text", "") or ""
                    if text:
                        evidence.append(text)
                if evidence:
                    claims.append(f"Evidence supports: {evidence[0]}")
                    confidence = min(0.9, 0.4 + 0.15 * len(evidence))
                    trace.append(f"Found {len(evidence)} supporting record(s)")
                else:
                    trace.append("No supporting evidence in memory")
            except Exception:
                trace.append("Memory search failed")
        else:
            trace.append("No evidence source available")

        # Explicit facts can be supplied directly through context.
        for fact in context.get("facts", []) or []:
            evidence.append(str(fact))
        if context.get("facts"):
            confidence = min(0.95, confidence + 0.1)

        response = claims[0] if claims else "No corroborating evidence found."
        return AgentOutput(
            agent=self.name,
            response=response,
            confidence=round(confidence, 4),
            claims=claims,
            assumptions=assumptions,
            evidence=evidence,
            reasoning_trace=trace,
            metadata={"evidence_count": len(evidence)},
        )


# ─── Memory Agent ────────────────────────────────────────────

class MemoryAgent(ReasoningAgent):
    """Retrieves past context and recurring patterns from prior turns."""

    name = "memory"

    def _reason(self, query: str, context: dict[str, Any]) -> AgentOutput:
        trace = ["Recalling prior context"]
        claims: list[str] = []
        assumptions = ["Past context remains relevant to the current turn"]
        confidence = 0.2

        history = context.get("history") or []
        keywords = set(keyword_tokens(query))
        related = []
        for turn in history:
            turn_text = turn if isinstance(turn, str) else str(turn)
            if keywords & set(keyword_tokens(turn_text)):
                related.append(turn_text)
        if related:
            claims.append(f"Earlier you mentioned: {related[-1]}")
            confidence = min(0.8, 0.4 + 0.1 * len(related))
            trace.append(f"Matched {len(related)} prior turn(s)")
        else:
            trace.append("No related prior context")

        memory = context.get("memory_manager")
        if not related and memory is not None and hasattr(memory, "search"):
            try:
                results = memory.search(query, top_k=1)
                best = getattr(results, "best", None)
                text = getattr(best, "text", "") if best is not None else ""
                if text:
                    claims.append(f"Recalled from memory: {text}")
                    confidence = max(confidence, 0.5)
                    trace.append("Recalled a stored memory")
            except Exception:
                trace.append("Memory recall failed")

        response = claims[0] if claims else "No relevant past context found."
        return AgentOutput(
            agent=self.name,
            response=response,
            confidence=round(confidence, 4),
            claims=claims,
            assumptions=assumptions,
            reasoning_trace=trace,
            metadata={"matched_turns": len(related)},
        )


def default_agents() -> list[ReasoningAgent]:
    """Return one instance of each built-in agent."""
    return [LogicAgent(), CreativityAgent(), EvidenceAgent(), MemoryAgent()]
