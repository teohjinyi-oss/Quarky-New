"""
Spinal Cord: Result Collector Department

Gathers brain outputs and keeps them UNMIXED.
Does NOT merge — that's the Decision Engine's job.
Just collects, validates, and pairs with routing metadata.
"""

from typing import Any

from AppStudio.Infrastructure.base import Department, BrainResult, SpinalResult
from MAIINNN.Connectors.intent_router import RouteDecision


class ResultCollector(Department):
    """
    Collects hemisphere results into a SpinalResult.
    Validates each result but does NOT decide which is better.
    """

    def __init__(self):
        super().__init__("result_collector", "core.spinal_cord")

    def process(self, data: Any) -> SpinalResult | None:
        """
        Expects a tuple: (RouteDecision, dict[str, BrainResult|None])
        Returns SpinalResult with both brain outputs preserved separately.
        """
        if not isinstance(data, tuple) or len(data) != 2:
            return None

        route_decision, brain_results = data

        if not isinstance(route_decision, RouteDecision):
            return None
        if not isinstance(brain_results, dict):
            return None

        analytical = brain_results.get("analytical")
        creative = brain_results.get("creative")

        # Validate types
        if analytical is not None and not isinstance(analytical, BrainResult):
            analytical = None
        if creative is not None and not isinstance(creative, BrainResult):
            creative = None

        brain_input = route_decision.brain_input

        return SpinalResult(
            analytical=analytical,
            creative=creative,
            route_decision=route_decision.reason,
            input_intent=brain_input.intent if brain_input else "",
            input_text=brain_input.text if brain_input else "",
        )
