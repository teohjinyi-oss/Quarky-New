"""
Spinal Cord: Parallel Dispatcher Department

Fires brain hemispheres based on RouteDecision.
For DEEP mode: runs both brains in parallel using threads.
For FAST/CREATIVE mode: runs only the selected brain.

Each brain runs through its full pipeline:
  Analytical: Receiver → Parser → Calculator → PatternMatcher → LogicEngine → Confidence → Responder
  Creative:   Receiver → ConceptExpander → TemplateEngine → Randomizer → StyleFormatter → Responder
"""

import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from AppStudio.Infrastructure.base import Department, Pipeline, BrainInput, BrainResult

# Analytical pipeline departments
from MAIINNN.Louis.receiver import AnalyticalReceiver
from MAIINNN.Louis.parser import AnalyticalParser
from MAIINNN.Louis.calculator import Calculator
from MAIINNN.Louis.pattern_matcher import PatternMatcher
from MAIINNN.Louis.logic_engine import LogicEngine
from MAIINNN.Louis.confidence import ConfidenceScorer
from MAIINNN.Louis.responder import AnalyticalResponder

# Creative pipeline departments
from MAIINNN.Wednesday.receiver import CreativeReceiver
from MAIINNN.Wednesday.concept_expander import ConceptExpander
from MAIINNN.Wednesday.template_engine import TemplateEngine
from MAIINNN.Wednesday.randomizer import Randomizer
from MAIINNN.Wednesday.style_formatter import StyleFormatter
from MAIINNN.Wednesday.responder import CreativeResponder

from MAIINNN.Connectors.intent_router import RouteDecision


def _build_analytical_pipeline() -> Pipeline:
    """Construct the full analytical processing pipeline."""
    return Pipeline([
        AnalyticalReceiver(),
        AnalyticalParser(),
        Calculator(),
        PatternMatcher(),
        LogicEngine(),
        ConfidenceScorer(),
        AnalyticalResponder(),
    ])


def _build_creative_pipeline() -> Pipeline:
    """Construct the full creative processing pipeline."""
    return Pipeline([
        CreativeReceiver(),
        ConceptExpander(),
        TemplateEngine(),
        Randomizer(),
        StyleFormatter(),
        CreativeResponder(),
    ])


# Pre-built pipelines (stateless departments, safe to reuse)
_analytical_pipeline = _build_analytical_pipeline()
_creative_pipeline = _build_creative_pipeline()


class ParallelDispatcher(Department):
    """
    Dispatches input to brain hemisphere(s) based on RouteDecision.
    Parallel mode uses ThreadPoolExecutor for true simultaneous processing.
    """

    def __init__(self):
        super().__init__("parallel_dispatcher", "core.spinal_cord")

    def process(self, data: Any) -> dict[str, BrainResult | None]:
        """
        Returns: {"analytical": BrainResult|None, "creative": BrainResult|None}
        """
        if not isinstance(data, RouteDecision):
            return {"analytical": None, "creative": None}

        brain_input = data.brain_input
        if brain_input is None:
            return {"analytical": None, "creative": None}

        results: dict[str, BrainResult | None] = {
            "analytical": None,
            "creative": None,
        }

        both = data.activate_analytical and data.activate_creative

        if both:
            # DEEP MODE: fire both in parallel
            results = self._run_parallel(brain_input)
        elif data.activate_analytical:
            results["analytical"] = self._run_analytical(brain_input)
        elif data.activate_creative:
            results["creative"] = self._run_creative(brain_input)

        return results

    def _run_parallel(self, brain_input: BrainInput) -> dict[str, BrainResult | None]:
        """Run both brains simultaneously. Each gets its own copy of input."""
        results: dict[str, BrainResult | None] = {
            "analytical": None,
            "creative": None,
        }

        # Deep copy so brains don't share mutable context
        analytical_input = copy.deepcopy(brain_input)
        creative_input = copy.deepcopy(brain_input)

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="brain") as pool:
            futures = {
                pool.submit(self._run_analytical, analytical_input): "analytical",
                pool.submit(self._run_creative, creative_input): "creative",
            }
            for future in as_completed(futures):
                brain_name = futures[future]
                try:
                    results[brain_name] = future.result(timeout=5.0)
                except Exception:
                    results[brain_name] = None

        return results

    def _run_analytical(self, brain_input: BrainInput) -> BrainResult | None:
        """Run the full analytical pipeline."""
        result = _analytical_pipeline.run(brain_input)
        if isinstance(result, BrainResult):
            return result
        return None

    def _run_creative(self, brain_input: BrainInput) -> BrainResult | None:
        """Run the full creative pipeline."""
        result = _creative_pipeline.run(brain_input)
        if isinstance(result, BrainResult):
            return result
        return None
