"""
Template Generation Backend (default)

A deterministic, dependency-free backend. It does not "make up" content — it
rephrases the rule engine's existing answer into a more natural, tier-aware
sentence. This keeps Quarky fully offline and transparent while still smoothing
the rigid template output the upgrade plan flagged as the critical gap.

Because it is deterministic, the same input always yields the same phrasing,
which keeps the benchmark harness reproducible.
"""

from __future__ import annotations

from core.generation.backend import (
    GenerationBackend,
    GenerationRequest,
    GenerationResult,
)


class TemplateBackend(GenerationBackend):
    """Deterministic, offline phrasing backend keyed on the specificity tier."""

    name = "template"

    # Lead-ins that make each tier read less robotic without adding claims.
    _LEAD_INS = {
        "SS": "{answer}",
        "GS": "Here's what I found: {answer}",
        "SG": "Broadly speaking, {answer}",
        "GG": "{answer}",
    }

    def generate(self, request: GenerationRequest) -> GenerationResult:
        answer = (request.answer or "").strip()
        if not answer:
            return GenerationResult(
                text="I don't have enough to answer that yet.",
                backend=self.name,
                enriched=False,
                confidence=request.confidence,
            )

        tier = request.tier if request.tier in self._LEAD_INS else "GG"
        template = self._LEAD_INS[tier]
        text = template.format(answer=answer)
        text = self._tidy(text)

        return GenerationResult(
            text=text,
            backend=self.name,
            enriched=(text != answer),
            confidence=request.confidence,
            metadata={"tier": tier},
        )

    @staticmethod
    def _tidy(text: str) -> str:
        """Normalise spacing and ensure terminal punctuation."""
        text = " ".join(text.split())
        if text and text[-1] not in ".!?":
            text += "."
        return text
