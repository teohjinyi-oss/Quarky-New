"""
Decision Engine: Collector Department

Gathers inputs from the Core Brain (SpinalResult), Memory recall,
and action feasibility checks. Packages everything into a DecisionContext
for downstream departments.
"""

from dataclasses import dataclass, field
from typing import Any

from AppStudio.Infrastructure.base import SpinalResult, BrainResult
from MAIINNN.Memory.manager import recall, SearchResult


@dataclass
class DecisionContext:
    """All gathered data the Decision Engine works with."""
    spinal: SpinalResult
    memory: SearchResult
    user_text: str
    intent: str
    analytical: BrainResult | None = None
    creative: BrainResult | None = None
    memory_hits: int = 0
    best_memory: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


def collect(spinal: SpinalResult) -> DecisionContext:
    """
    Gather all relevant context for decision-making.
    1. Extract brain results from SpinalResult
    2. Recall related memories using keywords from the input
    3. Package into DecisionContext
    """
    user_text = spinal.input_text
    intent = spinal.input_intent

    # Extract keywords for memory recall from brain metadata
    keywords = _extract_keywords(spinal)

    # Recall from all memory layers
    mem_result = recall(keywords, max_per_layer=3) if keywords else SearchResult()

    return DecisionContext(
        spinal=spinal,
        memory=mem_result,
        user_text=user_text,
        intent=intent,
        analytical=spinal.analytical,
        creative=spinal.creative,
        memory_hits=mem_result.total,
        best_memory=mem_result.best,
    )


def _extract_keywords(spinal: SpinalResult) -> list[str]:
    """Pull keywords from brain results or fall back to input text words."""
    keywords: list[str] = []

    # Try analytical metadata first
    if spinal.analytical and spinal.analytical.metadata:
        kw = spinal.analytical.metadata.get("keywords", [])
        if kw:
            keywords.extend(kw)

    # Fall back to tokenizing input text
    if not keywords and spinal.input_text:
        from MAIINNN.NLP.tokenizer import keyword_tokens
        keywords = keyword_tokens(spinal.input_text)[:10]

    return keywords
