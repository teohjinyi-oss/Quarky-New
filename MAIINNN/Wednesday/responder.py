"""
Creative Brain: Responder Department

Final stage of the creative pipeline.
Packages the styled creative draft into a BrainResult.
"""

import time
from typing import Any

from AppStudio.Infrastructure.base import Department, BrainResult, BrainInput
from MAIINNN.Wednesday.concept_expander import ConceptWeb


class CreativeResponder(Department):
    """Packages creative pipeline output into BrainResult."""

    def __init__(self):
        super().__init__("responder", "core.creative")

    def process(self, data: Any) -> BrainResult | None:
        if not isinstance(data, BrainInput):
            return None

        ctx = data.context
        draft: str = ctx.get("creative_draft", "")
        web: ConceptWeb | None = ctx.get("concept_web")

        if not draft:
            draft = "I thought about it creatively, but didn't find a strong angle."

        # Build reasoning trace
        reasoning = ["Creative pipeline activated"]
        if web:
            reasoning.append(f"Seed keywords: {web.seed_keywords}")
            if web.associations:
                reasoning.append(f"Associations found: {len(web.associations)}")
            if web.metaphors:
                reasoning.append(f"Metaphors generated: {len(web.metaphors)}")
            if web.inversions:
                reasoning.append(f"Inversions: {len(web.inversions)}")

        # Creative confidence: based on richness of concept web
        confidence = 0.3  # base
        if web:
            if web.associations:
                confidence += 0.2
            if web.metaphors:
                confidence += 0.15
            if web.inversions:
                confidence += 0.1
            if web.questions:
                confidence += 0.05
        confidence = min(confidence, 0.95)

        # Metadata
        metadata: dict[str, Any] = {
            "intent": data.intent,
        }
        if web:
            metadata["associations"] = web.associations[:5]
            metadata["seed_keywords"] = web.seed_keywords

        duration = (time.time() - data.timestamp) * 1000

        return BrainResult(
            source="creative",
            response=draft,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            metadata=metadata,
            duration_ms=round(duration, 2),
        )
