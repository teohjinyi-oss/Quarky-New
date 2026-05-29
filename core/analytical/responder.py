"""
Analytical Brain: Responder Department

Final stage of the analytical pipeline.
Packages all collected signals (pattern match, calculator, logic engine,
confidence score) into a single BrainResult for the spinal cord.
"""

import time
from typing import Any

from runtime.infrastructure.base import Department, BrainResult
from core.analytical.parser import ParsedInput
from core.analytical.logic_engine import ReasoningChain
from core.analytical.confidence import ConfidenceScore


class AnalyticalResponder(Department):
    """Packages the analytical pipeline output into BrainResult."""

    def __init__(self):
        super().__init__("responder", "core.analytical")

    def process(self, data: Any) -> BrainResult | None:
        if not isinstance(data, ParsedInput):
            return None

        ctx = data.brain_input.context
        reasoning: ReasoningChain | None = ctx.get("reasoning")
        conf_score: ConfidenceScore | None = ctx.get("confidence_score")

        # Build response text
        if reasoning and reasoning.conclusion:
            response = reasoning.conclusion
        else:
            response = "I processed your input but couldn't form a clear answer."

        # Build reasoning trace
        steps = []
        steps.append(f"task_type: {data.task_type}")
        if reasoning:
            steps.extend(reasoning.steps)
            steps.append(f"source: {reasoning.source}")

        # Confidence
        confidence = 0.0
        if conf_score:
            confidence = conf_score.overall
            steps.append(f"confidence: {conf_score.explanation}")
        elif reasoning:
            confidence = reasoning.confidence

        # Metadata
        metadata = {
            "task_type": data.task_type,
            "question_focus": data.question_focus,
            "entities": data.brain_input.entities,
        }

        # Calculator result if present
        calc = ctx.get("calc_result")
        if calc and calc.success:
            metadata["calculation"] = {
                "expression": calc.expression,
                "result": calc.result,
            }

        # Pattern match info
        match_result = ctx.get("pattern_match")
        if match_result and match_result.has_match:
            metadata["pattern_category"] = match_result.best_match.category

        # Compute duration
        duration = (time.time() - data.brain_input.timestamp) * 1000

        return BrainResult(
            source="analytical",
            response=response,
            confidence=confidence,
            reasoning=steps,
            metadata=metadata,
            duration_ms=round(duration, 2),
        )
