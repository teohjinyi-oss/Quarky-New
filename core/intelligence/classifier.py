"""
Intelligence: Specificity Classifier

Classifies input/output pairs into specificity tiers.
The tier determines how Quarky routes its response:

  SS (Specific Q → Specific A) = exact answer from knowledge
  GS (General Q → Specific A)  = broad question, precise answer available  
  SG (Specific Q → General A)  = specific question, only vague answer available
  GG (General Q → General A)   = both sides vague, lowest priority

The classifier uses heuristic signals:
  - Question word type (who/what/when = specific; how/why = general)
  - Entity presence (names, numbers, dates = specific)
  - Token count and diversity
  - Determiner usage ("the" = specific, "a/some" = general)
"""

from __future__ import annotations

import re
from core.intelligence.token import SpecificityTier


# ── Signal patterns ──────────────────────────────────────────

# Words that signal a SPECIFIC question
_SPECIFIC_Q_SIGNALS = {
    "who", "whom", "whose", "which", "where", "when",
    "what time", "what date", "what year", "what name",
    "how many", "how much", "how old", "how long", "how far",
}

# Words that signal a GENERAL question
_GENERAL_Q_SIGNALS = {
    "how", "why", "what", "explain", "describe", "tell me about",
    "what is", "what are", "what does", "can you",
}

# Specific entity indicators (regex patterns)
_ENTITY_PATTERNS = [
    re.compile(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b'),  # dates
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:km|mi|kg|lb|cm|mm|m|ft|in|°[cfCF])\b'),  # measurements
    re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'),  # proper nouns (multi-word)
    re.compile(r'\b\d{3,}\b'),  # large numbers
    re.compile(r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b', re.I),
    re.compile(r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I),
]

# Determiners
_SPECIFIC_DETERMINERS = {"the", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our"}
_GENERAL_DETERMINERS = {"a", "an", "some", "any", "most", "all", "many", "few"}


class SpecificityClassifier:
    """
    Classifies text into specificity levels and pairs query+answer
    into a SpecificityTier for response routing.
    """

    def classify_query(self, text: str) -> float:
        """
        Score how SPECIFIC a query is.
        Returns float in [0.0, 1.0] where 1.0 = highly specific.
        """
        if not text:
            return 0.0

        lower = text.lower().strip()
        score = 0.5  # neutral starting point
        signals = 0

        # Check specific question patterns
        for pattern in _SPECIFIC_Q_SIGNALS:
            if lower.startswith(pattern) or f" {pattern}" in f" {lower}":
                score += 0.15
                signals += 1
                break  # only count once

        # Check general question patterns (only if no specific match)
        if signals == 0:
            for pattern in _GENERAL_Q_SIGNALS:
                if lower.startswith(pattern) or f" {pattern}" in f" {lower}":
                    score -= 0.1
                    break

        # Entity presence (dates, names, numbers, measurements)
        entity_count = sum(1 for p in _ENTITY_PATTERNS if p.search(text))
        score += min(0.2, entity_count * 0.08)

        # Determiner analysis
        words = lower.split()
        spec_det = sum(1 for w in words if w in _SPECIFIC_DETERMINERS)
        gen_det = sum(1 for w in words if w in _GENERAL_DETERMINERS)
        if spec_det > gen_det:
            score += 0.05
        elif gen_det > spec_det:
            score -= 0.05

        # Short, pointed questions tend to be more specific
        if len(words) <= 5 and any(lower.startswith(w) for w in ("who", "where", "when")):
            score += 0.1

        return max(0.0, min(1.0, score))

    def classify_answer(self, text: str) -> float:
        """
        Score how SPECIFIC an answer is.
        Returns float in [0.0, 1.0] where 1.0 = highly specific.
        """
        if not text:
            return 0.0

        lower = text.lower().strip()
        score = 0.5  # neutral
        words = lower.split()

        # Entity presence → specific answer
        entity_count = sum(1 for p in _ENTITY_PATTERNS if p.search(text))
        score += min(0.25, entity_count * 0.1)

        # Short, definitive answers → specific
        if len(words) <= 10:
            score += 0.1

        # Hedging words → general answer
        hedges = {"maybe", "perhaps", "possibly", "generally", "usually",
                  "sometimes", "often", "might", "could", "probably"}
        hedge_count = sum(1 for w in words if w in hedges)
        score -= min(0.2, hedge_count * 0.08)

        # Numbers and data → specific
        number_count = sum(1 for w in words if re.match(r'^\d+(?:\.\d+)?$', w))
        score += min(0.15, number_count * 0.05)

        return max(0.0, min(1.0, score))

    def classify_pair(self, query: str, answer: str, threshold: float = 0.55) -> SpecificityTier:
        """
        Classify a query-answer pair into a SpecificityTier.

        Args:
            query: The user's question/input
            answer: The system's answer/response
            threshold: Score above this = specific, below = general

        Returns:
            SpecificityTier: SS, GS, SG, or GG
        """
        q_score = self.classify_query(query)
        a_score = self.classify_answer(answer)

        q_specific = q_score >= threshold
        a_specific = a_score >= threshold

        if q_specific and a_specific:
            return SpecificityTier.SS
        elif not q_specific and a_specific:
            return SpecificityTier.GS
        elif q_specific and not a_specific:
            return SpecificityTier.SG
        else:
            return SpecificityTier.GG

    def routing_priority(self, tier: SpecificityTier) -> str:
        """Human-readable routing label for a tier."""
        labels = {
            SpecificityTier.SS: "TOP — exact match",
            SpecificityTier.GS: "HIGH — good knowledge",
            SpecificityTier.SG: "MID — needs learning",
            SpecificityTier.GG: "LOW — fallback",
        }
        return labels.get(tier, "UNKNOWN")
