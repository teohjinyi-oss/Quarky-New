"""
Creative Brain: Receiver Department

Gate-check for the creative hemisphere.
Accepts all input types but enriches creative-specific context.
"""

from typing import Any
from AppStudio.Infrastructure.base import Department, BrainInput
from MAIINNN.NLP.classifier import ClassifiedInput


class CreativeReceiver(Department):
    """Accepts input for creative processing. More permissive than analytical."""

    def __init__(self):
        super().__init__("receiver", "core.creative")

    def process(self, data: Any) -> BrainInput | None:
        if isinstance(data, BrainInput):
            return data

        if isinstance(data, ClassifiedInput):
            return BrainInput(
                text=data.raw,
                intent=data.intent,
                confidence=data.confidence,
                entities=data.entities,
                tokens=data.tokens,
                keywords=data.keywords,
            )

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

        return None
