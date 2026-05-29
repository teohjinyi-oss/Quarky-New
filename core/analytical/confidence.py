"""
Analytical Brain: Confidence Scorer Department

Rates the quality of the analytical pipeline's output.
Combines signals from: pattern match confidence, reasoning chain confidence,
calculator success, and input classifier confidence.

If overall confidence is below threshold → marks output as uncertain.
"""

from dataclasses import dataclass
from typing import Any

from runtime.config.config import FAST_MODE_THRESHOLD, DEEP_MODE_THRESHOLD
from runtime.infrastructure.base import Department
from core.analytical.parser import ParsedInput
from core.analytical.logic_engine import ReasoningChain


@dataclass
class ConfidenceScore:
    """Detailed breakdown of confidence signals."""
    pattern_signal: float = 0.0       # from pattern match
    reasoning_signal: float = 0.0     # from logic engine
    calculator_signal: float = 0.0    # from calculator
    classifier_signal: float = 0.0    # from NLP classifier
    overall: float = 0.0             # weighted combination
    is_confident: bool = False       # above threshold?
    explanation: str = ""


class ConfidenceScorer(Department):
    """
    Combines all confidence signals into a final score.
    Weights: reasoning (40%), pattern (30%), classifier (20%), calculator (10%).
    """

    WEIGHT_REASONING = 0.40
    WEIGHT_PATTERN = 0.30
    WEIGHT_CLASSIFIER = 0.20
    WEIGHT_CALCULATOR = 0.10

    CONFIDENCE_THRESHOLD = 0.35  # below this → uncertain

    def __init__(self):
        super().__init__("confidence", "core.analytical")

    def process(self, data: Any) -> Any:
        if not isinstance(data, ParsedInput):
            return data

        ctx = data.brain_input.context
        score = ConfidenceScore()

        # Signal 1: NLP classifier confidence
        score.classifier_signal = data.brain_input.confidence

        # Signal 2: Pattern match
        match_result = ctx.get("pattern_match")
        if match_result and match_result.has_match and match_result.best_match:
            score.pattern_signal = match_result.best_match.confidence

        # Signal 3: Reasoning chain
        reasoning: ReasoningChain | None = ctx.get("reasoning")
        if reasoning:
            score.reasoning_signal = reasoning.confidence

        # Signal 4: Calculator
        calc = ctx.get("calc_result")
        if calc and calc.success:
            score.calculator_signal = 0.95

        # Weighted overall
        score.overall = (
            score.reasoning_signal * self.WEIGHT_REASONING +
            score.pattern_signal * self.WEIGHT_PATTERN +
            score.classifier_signal * self.WEIGHT_CLASSIFIER +
            score.calculator_signal * self.WEIGHT_CALCULATOR
        )
        score.overall = round(min(score.overall, 1.0), 3)
        score.is_confident = score.overall >= self.CONFIDENCE_THRESHOLD

        # Explain
        parts = []
        if score.pattern_signal > 0:
            parts.append(f"pattern={score.pattern_signal:.2f}")
        if score.reasoning_signal > 0:
            parts.append(f"reasoning={score.reasoning_signal:.2f}")
        if score.calculator_signal > 0:
            parts.append(f"calc={score.calculator_signal:.2f}")
        parts.append(f"classifier={score.classifier_signal:.2f}")
        score.explanation = f"overall={score.overall:.3f} ({', '.join(parts)})"

        ctx["confidence_score"] = score
        return data
