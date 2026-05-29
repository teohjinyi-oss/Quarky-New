"""
Creative Brain: Template Engine Department

Applies creative response templates based on intent type.
Transforms raw concept webs into structured creative output.

Strategy: Different intents get different creative treatment:
  - "creative" intent → full creative mode (brainstorm, story, etc.)
  - "question" intent → add an interesting angle / "did you know"
  - "task" intent → suggest creative approaches
  - "command" intent → minimal creative overlay
"""

import random
from typing import Any

from AppStudio.Infrastructure.base import Department, BrainInput
from MAIINNN.Wednesday.concept_expander import ConceptWeb


# ═══════════════════════════════════════════════════════════════
#  RESPONSE TEMPLATES
# ═══════════════════════════════════════════════════════════════

_BRAINSTORM_INTROS = [
    "Here are some ideas to explore:",
    "Let me think about this from different angles:",
    "Some creative directions to consider:",
    "Here's what comes to mind:",
    "Let me brainstorm on this:",
]

_CREATIVE_FRAMING = [
    "Looking at this creatively...",
    "Here's an interesting perspective...",
    "Thinking outside the box...",
    "From a different angle...",
    "Consider this...",
]

_STORY_STARTERS = [
    "Once upon a time, in a world where {concept}...",
    "Imagine a place where {concept} is the key to everything...",
    "Picture this: {concept}, but not as you know it...",
    "In the year 2100, {concept} changed everything...",
    "There was once a {concept} that nobody understood...",
]

_WHAT_IF_TEMPLATES = [
    "What if {keyword} could {action}? That would change how we think about {domain}.",
    "Imagine a world where {keyword} and {keyword2} are connected. What would that look like?",
    "Here's a thought: what if {keyword} is really about {association}?",
]


class TemplateEngine(Department):
    """
    Applies creative templates to concept webs.
    Produces structured creative text based on intent.
    """

    def __init__(self):
        super().__init__("template_engine", "core.creative")

    def process(self, data: Any) -> Any:
        if not isinstance(data, BrainInput):
            return data

        web: ConceptWeb | None = data.context.get("concept_web")
        if not web:
            data.context["creative_draft"] = self._minimal_response(data)
            return data

        intent = data.intent

        if intent == "creative":
            draft = self._full_creative(data, web)
        elif intent == "question":
            draft = self._creative_angle(data, web)
        elif intent == "task":
            draft = self._creative_approach(data, web)
        else:
            draft = self._minimal_creative(data, web)

        data.context["creative_draft"] = draft
        return data

    def _full_creative(self, inp: BrainInput, web: ConceptWeb) -> str:
        """Full creative mode: brainstorm, metaphors, what-ifs."""
        parts = []

        # Intro
        parts.append(random.choice(_BRAINSTORM_INTROS))

        # Associations
        if web.associations:
            sample = random.sample(web.associations, min(4, len(web.associations)))
            parts.append(f"\nRelated concepts: {', '.join(sample)}")

        # Metaphors
        if web.metaphors:
            parts.append(f"\n{web.metaphors[0]}")

        # What-if / inversion
        if web.inversions:
            parts.append(f"\n{random.choice(web.inversions)}")

        # Probing question
        if web.questions:
            parts.append(f"\n{random.choice(web.questions)}")

        return "\n".join(parts)

    def _creative_angle(self, inp: BrainInput, web: ConceptWeb) -> str:
        """Add an interesting creative angle to a question."""
        parts = [random.choice(_CREATIVE_FRAMING)]

        if web.metaphors:
            parts.append(web.metaphors[0])
        if web.associations:
            sample = web.associations[:3]
            parts.append(f"This connects to: {', '.join(sample)}.")
        if web.questions:
            parts.append(random.choice(web.questions))

        return " ".join(parts)

    def _creative_approach(self, inp: BrainInput, web: ConceptWeb) -> str:
        """Suggest creative approaches to a task."""
        keywords = web.seed_keywords
        parts = ["Here's a creative take on approaching this:"]

        if web.associations:
            parts.append(
                f"Think about it in terms of {random.choice(web.associations)}."
            )
        if web.inversions:
            parts.append(random.choice(web.inversions))

        return " ".join(parts)

    def _minimal_creative(self, inp: BrainInput, web: ConceptWeb) -> str:
        """Minimal creative overlay for non-creative intents."""
        if web.associations:
            return f"Interestingly, this relates to: {', '.join(web.associations[:3])}."
        return ""

    def _minimal_response(self, inp: BrainInput) -> str:
        """Fallback when no concept web exists."""
        if inp.keywords:
            kw = inp.keywords[0]
            return f"That's an interesting topic — {kw}. Let me think about it."
        return "Hmm, let me think about that creatively."
