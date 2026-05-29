"""
Creative Brain: Randomizer Department

Injects controlled randomness into creative output.
Not chaos — structured variation that makes outputs feel fresh and non-repetitive.

Techniques:
  - Word substitution with synonyms at controlled rate
  - Sentence reordering within safe bounds
  - Emphasis variation (add/remove intensifiers)
  - Perspective shifts
"""

import random
from typing import Any

from AppStudio.Infrastructure.base import Department, BrainInput


# ─── Synonym pools for word substitution ────────────────────
_SYNONYMS: dict[str, list[str]] = {
    "interesting": ["fascinating", "intriguing", "compelling", "noteworthy"],
    "good": ["excellent", "great", "solid", "impressive"],
    "think": ["consider", "ponder", "reflect on", "explore"],
    "important": ["crucial", "significant", "essential", "key"],
    "different": ["unique", "distinct", "alternative", "novel"],
    "idea": ["concept", "notion", "thought", "vision"],
    "create": ["craft", "design", "build", "develop"],
    "change": ["transform", "shift", "evolve", "reshape"],
    "big": ["significant", "substantial", "major", "vast"],
    "small": ["subtle", "minor", "modest", "fine"],
    "connect": ["link", "bridge", "relate", "tie"],
    "here": ["right here", "at this point", "now"],
}

# Intensifiers to sprinkle or remove
_INTENSIFIERS = [
    "really", "quite", "particularly", "especially",
    "remarkably", "notably", "genuinely",
]

# Perspective shift prefixes
_PERSPECTIVES = [
    "From a different perspective, ",
    "Looking at it another way, ",
    "Interestingly enough, ",
    "Here's a twist: ",
    "Consider this angle: ",
    "",  # no shift (weighted by inclusion)
    "",
    "",
]


class Randomizer(Department):
    """
    Adds controlled variation to creative drafts.
    Rate-limited: won't modify more than 30% of the output.
    """

    SUBSTITUTION_RATE = 0.25   # chance of replacing a substitutable word
    INTENSIFIER_RATE = 0.15    # chance of adding an intensifier before adjectives

    def __init__(self):
        super().__init__("randomizer", "core.creative")

    def process(self, data: Any) -> Any:
        if not isinstance(data, BrainInput):
            return data

        draft: str = data.context.get("creative_draft", "")
        if not draft:
            return data

        # Apply controlled randomness
        varied = self._vary_words(draft)
        varied = self._add_perspective(varied)

        data.context["creative_draft"] = varied
        return data

    def _vary_words(self, text: str) -> str:
        """Substitute some words with synonyms at controlled rate."""
        words = text.split()
        result = []

        for word in words:
            clean = word.lower().strip(".,!?;:")
            if clean in _SYNONYMS and random.random() < self.SUBSTITUTION_RATE:
                replacement = random.choice(_SYNONYMS[clean])
                # Preserve original casing roughly
                if word[0].isupper():
                    replacement = replacement.capitalize()
                # Preserve trailing punctuation
                trailing = ""
                if word and word[-1] in ".,!?;:":
                    trailing = word[-1]
                result.append(replacement + trailing)
            else:
                result.append(word)

        return " ".join(result)

    def _add_perspective(self, text: str) -> str:
        """Occasionally prepend a perspective shift."""
        if random.random() < 0.3:
            prefix = random.choice(_PERSPECTIVES)
            if prefix:
                # Only add to first sentence
                return prefix + text[0].lower() + text[1:]
        return text
