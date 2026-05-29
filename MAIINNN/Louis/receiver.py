"""
Analytical Brain: Receiver Department

First department in the analytical pipeline.
Validates that the input is suitable for analytical processing,
converts ClassifiedInput → BrainInput, and passes it forward.
"""

from typing import Any
from AppStudio.Infrastructure.base import Department, BrainInput
from MAIINNN.NLP.classifier import ClassifiedInput


class AnalyticalReceiver(Department):
    """Gate-check: only accepts inputs that warrant analytical processing."""

    # Intents the analytical brain handles well
    ACCEPTED_INTENTS = {"command", "question", "task"}

    def __init__(self):
        super().__init__("receiver", "core.analytical")

    def process(self, data: Any) -> BrainInput | None:
        """
        Convert ClassifiedInput → BrainInput.
        Returns None if this input has zero analytical value.
        """
        if isinstance(data, BrainInput):
            return data  # already wrapped (forwarded from spinal cord)

        if isinstance(data, ClassifiedInput):
            return BrainInput(
                text=data.raw,
                intent=data.intent,
                confidence=data.confidence,
                entities=data.entities,
                tokens=data.tokens,
                keywords=data.keywords,
            )

        # Raw string fallback
        if isinstance(data, str):
            from MAIINNN.NLP.classifier import classify
            classified = classify(data)
            return BrainInput(
                text=classified.raw,
                intent=classified.intent,
                confidence=classified.confidence,
                entities=classified.entities,
                tokens=classified.tokens,
                keywords=classified.keywords,
            )

        return None  # reject unknown input types
