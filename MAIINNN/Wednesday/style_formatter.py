"""
Creative Brain: Style Formatter Department

Adds personality and tone to creative output.
Quarky has a distinct voice: curious, slightly playful, concise, helpful.
"""

import re
from typing import Any

from AppStudio.Infrastructure.base import Department, BrainInput


# ─── Personality traits and their expression ─────────────────

# Conversational connectors that make responses flow naturally
_CONNECTORS = [
    "By the way, ",
    "Oh, and ",
    "Also — ",
    "One more thing: ",
    "Speaking of which, ",
]

# Personality-injecting sentence endings
_CLOSERS = [
    "Pretty cool, right?",
    "Something to think about.",
    "What do you think?",
    "Want me to explore this further?",
    "Let me know if you want more on this.",
    "",  # sometimes say nothing
    "",
]

# Tone adjustments by intent
_TONE_MAP = {
    "creative":  "enthusiastic",   # full personality
    "question":  "helpful",        # informative but warm
    "task":      "practical",      # efficient
    "command":   "direct",         # minimal decoration
}


class StyleFormatter(Department):
    """
    Applies Quarky's personality to the creative draft.
    Tone adapts to intent type. Never over-decorates commands.
    """

    def __init__(self):
        super().__init__("style_formatter", "core.creative")

    def process(self, data: Any) -> Any:
        if not isinstance(data, BrainInput):
            return data

        draft: str = data.context.get("creative_draft", "")
        if not draft:
            return data

        tone = _TONE_MAP.get(data.intent, "helpful")
        styled = self._apply_tone(draft, tone)
        data.context["creative_draft"] = styled
        return data

    def _apply_tone(self, text: str, tone: str) -> str:
        """Apply tone-specific formatting."""
        if tone == "direct":
            # Commands: clean up, no fluff
            return self._clean_for_command(text)

        if tone == "practical":
            # Tasks: keep it organized
            return self._format_practical(text)

        if tone == "enthusiastic":
            # Creative: full personality
            return self._format_enthusiastic(text)

        # Default helpful: light touch
        return self._format_helpful(text)

    def _clean_for_command(self, text: str) -> str:
        """Strip creative decoration for command responses."""
        # Remove wishy-washy qualifiers
        text = re.sub(r'\b(perhaps|maybe|possibly|kind of|sort of)\b\s*', '', text)
        return text.strip()

    def _format_practical(self, text: str) -> str:
        """Light formatting for task-oriented responses."""
        return text.strip()

    def _format_enthusiastic(self, text: str) -> str:
        """Full creative personality — curious and engaging."""
        text = text.strip()
        # Ensure it doesn't already end with a question
        if not text.endswith("?") and not text.endswith("!"):
            # Sometimes add a closer
            import random
            closer = random.choice(_CLOSERS)
            if closer:
                text = text.rstrip(".") + ". " + closer
        return text

    def _format_helpful(self, text: str) -> str:
        """Warm but not over-the-top."""
        return text.strip()
