"""
Analytical Brain: Response Generator (v2)

Template engine that produces different response styles based on
the SpecificityTier of the query/answer pair:

  SS (specific→specific): Direct, precise answer.
  GS (general→specific): Explain then answer.
  SG (specific→general): Contextualize the specific into broader view.
  GG (general→general): Conversational, exploratory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from AppStudio.Infrastructure.base import Department

try:
    from MAIINNN.Intelligence.token import SpecificityTier
except ImportError:
    SpecificityTier = None  # type: ignore[assignment,misc]


@dataclass
class GeneratedResponse:
    """Output from the response generator."""
    text: str
    tier: str = "GG"
    template_used: str = ""
    confidence: float = 0.5


class ResponseGenerator(Department):
    """
    Generates final analytical responses styled by specificity tier.
    """

    def __init__(self):
        super().__init__("response_generator", "core.analytical")

    def process(self, data) -> GeneratedResponse:
        """
        Generate a response.

        Args:
            data: dict with 'answer', 'tier' (str), 'query', 'reasoning_steps'
        """
        if not isinstance(data, dict):
            return GeneratedResponse(text="I'm not sure how to answer that.")

        answer = data.get("answer", "")
        tier = data.get("tier", "GG")
        query = data.get("query", "")

        if not answer:
            return GeneratedResponse(
                text="I don't have enough information to answer that yet.",
                tier=tier,
            )

        return self._format_by_tier(answer, tier, query)

    def _format_by_tier(
        self, answer: str, tier: str, query: str
    ) -> GeneratedResponse:
        """Apply tier-appropriate formatting."""
        if tier == "SS":
            return self._format_ss(answer)
        elif tier == "GS":
            return self._format_gs(answer, query)
        elif tier == "SG":
            return self._format_sg(answer, query)
        else:
            return self._format_gg(answer)

    # ------- per-tier formatters ------- #

    def _format_ss(self, answer: str) -> GeneratedResponse:
        """Specific question → Specific answer: Direct and concise."""
        return GeneratedResponse(
            text=answer.strip(),
            tier="SS",
            template_used="direct",
            confidence=0.85,
        )

    def _format_gs(self, answer: str, query: str) -> GeneratedResponse:
        """General question → Specific answer: Explain then answer."""
        text = f"Here's what I know — {answer.strip()}"
        return GeneratedResponse(
            text=text,
            tier="GS",
            template_used="explain_then_answer",
            confidence=0.7,
        )

    def _format_sg(self, answer: str, query: str) -> GeneratedResponse:
        """Specific question → General answer: Broaden the view."""
        text = f"In broader terms, {answer.strip()}"
        return GeneratedResponse(
            text=text,
            tier="SG",
            template_used="broaden",
            confidence=0.6,
        )

    def _format_gg(self, answer: str) -> GeneratedResponse:
        """General question → General answer: Conversational."""
        text = f"That's an interesting area. {answer.strip()}"
        return GeneratedResponse(
            text=text,
            tier="GG",
            template_used="conversational",
            confidence=0.5,
        )
