"""
Decision Engine: Memory Updater Department

Decides what from this interaction should be stored and in which memory layer.
Rules:
  - Every interaction → temporary (auto-expire, short-term recall)
  - Questions with good answers → flexible (summarized for later)
  - Explicit "remember" commands → permanent (locked)
  - Repeated topics → boost priority on existing entries
"""

import re

from core.decision.collector import DecisionContext
from core.decision.evaluator import EvalScores
from core.decision.merger import MergedResult
from core.memory import manager as mem


# Phrases that signal permanent storage
_PERMANENT_TRIGGERS = [
    r"\bremember\s+(this\s+)?forever\b",
    r"\bnever\s+forget\b",
    r"\bsave\s+permanently\b",
    r"\bkeep\s+this\s+always\b",
    r"\bstore\s+permanently\b",
]

# Minimum confidence to store in flexible layer
_FLEX_THRESHOLD = 0.4


def update_memory(
    ctx: DecisionContext,
    scores: EvalScores,
    merged: MergedResult,
) -> list[str]:
    """
    Decide what to store and where. Returns a list of action descriptions.
    """
    actions: list[str] = []
    user_text = ctx.user_text
    response_text = merged.response

    # 1. Always store in temporary (conversation history)
    interaction = f"Q: {user_text}\nA: {response_text}"
    mem.store_temporary(interaction, source="decision.memory_updater")
    actions.append("stored interaction in temporary")

    # 2. Check for explicit permanent triggers
    if _is_permanent_request(user_text):
        # Store the user's actual content, not the Q&A
        content = _extract_remember_content(user_text)
        mem.store_permanent(content, tags=["user-requested"], source="user")
        actions.append(f"stored in permanent: {content[:50]}")
        return actions  # Don't also store in flexible/priority

    # 3. Good answers → flexible (summarized for later recall)
    if merged.confidence >= _FLEX_THRESHOLD and len(response_text) > 30:
        mem.store_flexible(interaction, source="decision.memory_updater")
        actions.append("stored in flexible (summarized)")

    # 4. High-confidence, topic-specific → priority (reinforcement)
    if merged.confidence >= 0.6 and ctx.intent.upper() in ("QUESTION", "TASK"):
        mem.store_priority(
            interaction,
            source="decision.memory_updater",
            importance=min(1.0, merged.confidence),
        )
        actions.append(f"stored in priority (importance={merged.confidence:.2f})")

    return actions


def _is_permanent_request(text: str) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in _PERMANENT_TRIGGERS)


def _extract_remember_content(text: str) -> str:
    """Strip the 'remember forever' framing to get the actual content."""
    lower = text.lower()
    # Remove trigger phrases
    for pattern in [
        r"^(please\s+)?remember\s+(this\s+)?forever[:\s]*",
        r"^(please\s+)?never\s+forget[:\s]*",
        r"^(please\s+)?save\s+permanently[:\s]*",
        r"^(please\s+)?keep\s+this\s+always[:\s]*",
        r"^(please\s+)?store\s+permanently[:\s]*",
    ]:
        cleaned = re.sub(pattern, "", lower, count=1).strip()
        if cleaned and cleaned != lower:
            # Return using original casing
            offset = len(text) - len(cleaned)
            return text[offset:].strip()

    return text
