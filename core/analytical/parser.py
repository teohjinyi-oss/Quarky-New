"""
Analytical Brain: Parser Department

Breaks input into structured processable units.
Identifies what TYPE of analytical work is needed:
- Math expression to evaluate
- Factual question to look up
- Command to map to an action
- Multi-step task to decompose
"""

import re
from dataclasses import dataclass, field
from typing import Any

from runtime.infrastructure.base import Department, BrainInput
from core.nlp.tokenizer import tokenize_sentences, keyword_tokens


@dataclass
class ParsedInput:
    """Structured representation of what the analytical brain needs to do."""
    brain_input: BrainInput
    task_type: str                    # "math" | "factual" | "command" | "definition" | "comparison" | "general"
    sub_tasks: list[str] = field(default_factory=list)  # decomposed steps
    math_expressions: list[str] = field(default_factory=list)
    question_focus: str = ""          # the core thing being asked about
    sentences: list[str] = field(default_factory=list)


# ─── Detection patterns ─────────────────────────────────────
_MATH_RE = re.compile(
    r'\b\d+\s*[\+\-\*\/\%\^]\s*\d+|'        # 5 + 3, 10 * 2
    r'\b(calculate|compute|solve|evaluate)\b|'
    r'\bsqrt|log|sin|cos|tan\b|'
    r'\b\d+\s*(plus|minus|times|divided by|to the power)\s*\d+',
    re.IGNORECASE,
)

_DEFINITION_RE = re.compile(
    r'\b(what is|what are|define|meaning of|definition of|explain what)\b',
    re.IGNORECASE,
)

_COMPARISON_RE = re.compile(
    r'\b(difference between|compare|versus|vs\.?|better|worse|which one)\b',
    re.IGNORECASE,
)

_MULTI_STEP_RE = re.compile(
    r'\b(and then|after that|first .+ then|step by step|also)\b',
    re.IGNORECASE,
)


class AnalyticalParser(Department):
    """Parses input into structured tasks for downstream departments."""

    def __init__(self):
        super().__init__("parser", "core.analytical")

    def process(self, data: Any) -> ParsedInput | None:
        if not isinstance(data, BrainInput):
            return None

        text = data.text
        lower = text.lower()

        # Detect task type
        task_type = self._detect_task_type(lower, data.intent)

        # Extract math expressions
        math_exprs = _MATH_RE.findall(text)
        math_expressions = [m if isinstance(m, str) else m[0]
                           for m in math_exprs if m]

        # Decompose multi-step
        sub_tasks = self._decompose(text)

        # Find question focus (main keywords)
        focus = self._extract_focus(data.keywords, lower)

        # Split sentences
        sentences = tokenize_sentences(text)

        return ParsedInput(
            brain_input=data,
            task_type=task_type,
            sub_tasks=sub_tasks,
            math_expressions=math_expressions,
            question_focus=focus,
            sentences=sentences,
        )

    def _detect_task_type(self, lower: str, intent: str) -> str:
        """Determine what kind of analytical work this requires."""
        if _MATH_RE.search(lower):
            return "math"
        if _DEFINITION_RE.search(lower):
            return "definition"
        if _COMPARISON_RE.search(lower):
            return "comparison"
        if intent == "command":
            return "command"
        if intent == "question":
            return "factual"
        return "general"

    def _decompose(self, text: str) -> list[str]:
        """Split compound requests into sub-tasks."""
        if not _MULTI_STEP_RE.search(text):
            return [text]

        # Split on conjunction words
        parts = re.split(
            r'\b(?:and then|after that|then|also)\b',
            text,
            flags=re.IGNORECASE,
        )
        return [p.strip() for p in parts if p.strip()]

    def _extract_focus(self, keywords: list[str], lower: str) -> str:
        """Extract the main topic being asked about."""
        if not keywords:
            return ""

        # For "what is X" patterns, extract X
        match = re.search(r'what (?:is|are) (?:a |an |the )?(.+?)(?:\?|$)', lower)
        if match:
            return match.group(1).strip()

        # Otherwise, first 3 keywords joined
        return " ".join(keywords[:3])
