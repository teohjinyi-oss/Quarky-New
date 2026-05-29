"""
Spinal Cord: Intent Router Department (v2)

Token-value-aware routing: uses SpecificityTier from the classifier
to decide which brain hemisphere(s) to activate.

Routing strategy (v2):
  SS (specific→specific): FAST analytical — direct answer
  GS (general→specific):  FAST analytical — explain then answer
  SG (specific→general):  DEEP both brains — broaden perspective
  GG (general→general):   CREATIVE primary — exploratory response

Falls back to v1 confidence-based rules when specificity is not available.
"""

from dataclasses import dataclass
from typing import Any

from runtime.config.config import FAST_MODE_THRESHOLD, DEEP_MODE_THRESHOLD, MAX_INPUT_LENGTH_FAST
from runtime.infrastructure.base import Department, BrainInput
from core.nlp.classifier import ClassifiedInput, classify

try:
    from core.intelligence.classifier import SpecificityClassifier
    _spec_classifier = SpecificityClassifier()
except ImportError:
    _spec_classifier = None  # type: ignore[assignment]


@dataclass
class RouteDecision:
    """Output of intent routing — tells dispatcher what to activate."""
    activate_analytical: bool = False
    activate_creative: bool = False
    mode: str = ""                  # "fast" | "creative" | "deep" | "dual"
    reason: str = ""
    brain_input: BrainInput | None = None
    specificity_tier: str = ""      # v2: "SS" | "GS" | "SG" | "GG" | ""


class IntentRouter(Department):
    """
    Routes input to the correct brain hemisphere(s).

    v2 Strategy matrix (specificity-first):
    ┌────────────────┬──────────────┬─────────────────────┐
    │ Specificity     │ Mode         │ Brains activated    │
    ├────────────────┼──────────────┼─────────────────────┤
    │ SS              │ FAST         │ Analytical only     │
    │ GS              │ FAST         │ Analytical only     │
    │ SG              │ DEEP         │ Both (parallel)     │
    │ GG              │ CREATIVE     │ Creative primary    │
    ├────────────────┼──────────────┼─────────────────────┤
    │ Fallback (v1 confidence-based):                      │
    │ command + high  │ FAST         │ Analytical only     │
    │ creative intent │ CREATIVE     │ Creative only       │
    │ low confidence  │ DEEP         │ Both (parallel)     │
    └────────────────┴──────────────┴─────────────────────┘
    """

    def __init__(self):
        super().__init__("intent_router", "core.spinal_cord")

    def process(self, data: Any) -> RouteDecision:
        brain_input = self._to_brain_input(data)
        if brain_input is None:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason="Could not parse input — defaulting to analytical",
            )

        # v2: Try specificity-based routing first
        if _spec_classifier is not None:
            decision = self._route_by_specificity(brain_input)
            if decision is not None:
                return decision

        # Fallback: v1 confidence-based routing
        return self._route_by_confidence(brain_input)

    def _route_by_specificity(self, brain_input: BrainInput) -> RouteDecision | None:
        """Route based on query specificity score (v2 primary strategy)."""
        if _spec_classifier is None:
            return None
        try:
            q_score = _spec_classifier.classify_query(brain_input.text)
        except Exception:
            return None

        # Map score to tier: >=0.55 = specific query
        # Without an answer yet, we route based on query specificity:
        #   High specificity (>=0.65): SS-like → fast analytical (direct answer)
        #   Medium specificity (>=0.55): GS-like → fast analytical (explain)
        #   Low-medium (>=0.40): SG-like → both brains
        #   Low (<0.40): GG-like → creative primary

        if q_score >= 0.65:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason=f"Specificity SS — direct analytical answer (q={q_score:.2f})",
                brain_input=brain_input,
                specificity_tier="SS",
            )
        elif q_score >= 0.55:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason=f"Specificity GS — analytical explain-then-answer (q={q_score:.2f})",
                brain_input=brain_input,
                specificity_tier="GS",
            )
        elif q_score >= 0.40:
            return RouteDecision(
                activate_analytical=True,
                activate_creative=True,
                mode="deep",
                reason=f"Specificity SG — both brains for broader context (q={q_score:.2f})",
                brain_input=brain_input,
                specificity_tier="SG",
            )
        else:
            return RouteDecision(
                activate_creative=True,
                activate_analytical=True,  # analytical backup
                mode="creative",
                reason=f"Specificity GG — creative primary (q={q_score:.2f})",
                brain_input=brain_input,
                specificity_tier="GG",
            )

    def _route_by_confidence(self, brain_input: BrainInput) -> RouteDecision:
        """Fallback v1 routing: confidence + intent based."""
        intent = brain_input.intent
        conf = brain_input.confidence
        text_len = len(brain_input.text)

        # Rule 1: Creative intent → creative brain
        if intent == "creative":
            return RouteDecision(
                activate_creative=True,
                mode="creative",
                reason=f"Creative intent detected (conf={conf:.2f})",
                brain_input=brain_input,
            )

        # Rule 2: Command with high confidence → fast analytical
        if intent == "command" and conf >= FAST_MODE_THRESHOLD:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason=f"Command + high confidence ({conf:.2f} >= {FAST_MODE_THRESHOLD})",
                brain_input=brain_input,
            )

        # Rule 3: Short command → fast analytical
        if intent == "command" and text_len <= MAX_INPUT_LENGTH_FAST:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason=f"Short command ({text_len} chars), fast path",
                brain_input=brain_input,
            )

        # Rule 4: Question with good confidence → analytical
        if intent == "question" and conf >= DEEP_MODE_THRESHOLD:
            return RouteDecision(
                activate_analytical=True,
                mode="fast",
                reason=f"Question + sufficient confidence ({conf:.2f} >= {DEEP_MODE_THRESHOLD})",
                brain_input=brain_input,
            )

        # Rule 5: Low confidence or task → BOTH brains
        return RouteDecision(
            activate_analytical=True,
            activate_creative=True,
            mode="deep",
            reason=f"Deep mode: intent={intent}, conf={conf:.2f} — activating both hemispheres",
            brain_input=brain_input,
        )

    def _to_brain_input(self, data: Any) -> BrainInput | None:
        """Normalize any input into BrainInput."""
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
