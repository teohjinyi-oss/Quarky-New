"""
Decision Engine: Merger Department (v2)

Combines brain outputs based on evaluation scores.

v2 enhancements:
  - Specificity-tier-aware merging (SS gets direct, GG gets exploratory)
  - Token relevance weighting in blend selection
  - Richer memory context weaving

Strategy:
  - Strong analytical (dominant)  → use analytical, discard creative
  - Strong creative (dominant)    → use creative
  - Both close                    → merge: lead with analytical, append creative color
  - Neither strong                → fallback response
  - Memory enhances any result    → weave in remembered context
"""

from dataclasses import dataclass, field
from typing import Any

from core.decision.collector import DecisionContext
from core.decision.evaluator import EvalScores


@dataclass
class MergedResult:
    """The merged, final response text + metadata."""
    response: str
    confidence: float
    source: str                    # "analytical", "creative", "merged", "fallback"
    reasoning: list[str] = field(default_factory=list)
    memory_context: str = ""       # relevant memory snippet woven in
    specificity_tier: str = ""     # v2: tier that drove the merge
    metadata: dict[str, Any] = field(default_factory=dict)


def merge(ctx: DecisionContext, scores: EvalScores) -> MergedResult:
    """
    Combine brain results into a single coherent response.
    """
    result = MergedResult(
        response="",
        confidence=0.0,
        source="fallback",
        specificity_tier=scores.specificity_tier,
    )

    # Phase 1: Pick the base response
    if scores.dominant == "analytical" and ctx.analytical:
        result.response = ctx.analytical.response
        result.confidence = scores.analytical_score + scores.memory_bonus
        result.source = "analytical"
        result.reasoning = list(ctx.analytical.reasoning)

    elif scores.dominant == "creative" and ctx.creative:
        result.response = ctx.creative.response
        result.confidence = scores.creative_score + scores.memory_bonus
        result.source = "creative"
        result.reasoning = list(ctx.creative.reasoning)

    elif scores.dominant == "both" and ctx.analytical and ctx.creative:
        # Merged: analytical leads, creative adds flavor
        result.response = _blend(
            ctx.analytical.response,
            ctx.creative.response,
            scores.specificity_tier,
        )
        result.confidence = (
            max(scores.analytical_score, scores.creative_score)
            + scores.memory_bonus
        )
        result.source = "merged"
        result.reasoning = list(ctx.analytical.reasoning)
        result.reasoning.append(
            f"Creative enrichment added (conf={scores.creative_score:.2f})"
        )

    elif ctx.analytical:
        # Only analytical available
        result.response = ctx.analytical.response
        result.confidence = scores.analytical_score + scores.memory_bonus
        result.source = "analytical"
        result.reasoning = list(ctx.analytical.reasoning)

    elif ctx.creative:
        # Only creative available
        result.response = ctx.creative.response
        result.confidence = scores.creative_score + scores.memory_bonus
        result.source = "creative"
        result.reasoning = list(ctx.creative.reasoning)

    else:
        result.response = "I'm not sure how to help with that. Could you rephrase?"
        result.confidence = 0.1
        result.source = "fallback"
        result.reasoning = ["No brain produced a usable result"]

    # Phase 2: Weave in memory context if valuable
    if ctx.best_memory:
        mem_text = _extract_memory_text(ctx.best_memory)
        if mem_text and _is_relevant(mem_text, ctx.user_text):
            result.memory_context = mem_text
            result.reasoning.append(f"Memory context recalled: {mem_text[:50]}...")

    # Cap confidence
    result.confidence = min(1.0, result.confidence)

    return result


def _blend(analytical: str, creative: str, tier: str = "") -> str:
    """
    Merge two brain outputs into one coherent answer.

    v2: Tier-aware blending:
      SS/GS → Analytical dominates, minimal creative
      SG    → Equal weight
      GG    → Creative dominates with analytical grounding
    """
    base = analytical.rstrip()

    # Extract novel sentences from creative
    creative_sentences = [s.strip() for s in creative.split(".")
                         if s.strip() and len(s.strip()) > 10]
    if not creative_sentences:
        return base

    # Tier-based blending
    if tier in ("SS", "GS"):
        # Minimal creative — only add if really novel
        lower_base = base.lower()
        for sentence in creative_sentences[:1]:
            if sentence.lower() not in lower_base:
                if not base.endswith((".", "!", "?")):
                    base += "."
                return f"{base} {sentence}."
        return base

    elif tier == "GG":
        # Creative leads, analytical grounds
        creative_text = creative.rstrip()
        lower_creative = creative_text.lower()
        for sentence in [s.strip() for s in analytical.split(".")
                         if s.strip() and len(s.strip()) > 10]:
            if sentence.lower() not in lower_creative:
                if not creative_text.endswith((".", "!", "?")):
                    creative_text += "."
                return f"{creative_text} {sentence}."
        return creative_text

    else:
        # Default / SG: analytical leads, creative adds
        lower_base = base.lower()
        for sentence in creative_sentences:
            if sentence.lower() not in lower_base:
                if not base.endswith((".", "!", "?")):
                    base += "."
                return f"{base} {sentence}."
        return base


def _extract_memory_text(memory_entry: Any) -> str:
    """Pull text from any memory entry type."""
    if hasattr(memory_entry, "content") and memory_entry.content:
        return memory_entry.content
    if hasattr(memory_entry, "text") and memory_entry.text:
        return memory_entry.text
    if hasattr(memory_entry, "summary") and memory_entry.summary:
        return memory_entry.summary
    if hasattr(memory_entry, "original") and memory_entry.original:
        return memory_entry.original
    return ""


def _is_relevant(memory_text: str, user_text: str) -> bool:
    """Quick relevance check — at least one meaningful word overlaps."""
    from core.nlp.tokenizer import keyword_tokens
    mem_kw = set(keyword_tokens(memory_text))
    user_kw = set(keyword_tokens(user_text))
    return len(mem_kw & user_kw) >= 1
