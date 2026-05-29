"""
Spinal Cord: Forwarder Department (v2)

Final stage of the spinal cord — orchestrates the full brain pipeline.

v2 enhancements:
  - Injects token context (specificity tier, memory hints) into BrainInput
  - Passes specificity tier to response formatting
  - Memory-aware: enriches input with relevant memory before brain processing
"""

from typing import Any

from runtime.infrastructure.base import Department, SpinalResult, BrainInput
from core.routing.intent_router import IntentRouter, RouteDecision
from core.routing.parallel_dispatcher import ParallelDispatcher
from core.routing.result_collector import ResultCollector


# ─── Singleton instances ─────────────────────────────────────
_router = IntentRouter()
_dispatcher = ParallelDispatcher()
_collector = ResultCollector()


class Forwarder(Department):
    """
    Orchestrates the full brain pipeline:
      Input → Router → [EnrichContext] → Dispatcher → Collector → SpinalResult

    v2: Enriches BrainInput with token context before dispatching.
    """

    def __init__(self):
        super().__init__("forwarder", "core.spinal_cord")
        self._memory_manager = None

    def set_memory(self, memory_manager: Any) -> None:
        """Inject the v2 memory manager for context enrichment."""
        self._memory_manager = memory_manager

    def process(self, data: Any) -> SpinalResult | None:
        """
        Run the entire Core Brain on input.
        Accepts: str, ClassifiedInput, or BrainInput.
        Returns: SpinalResult with analytical and/or creative outputs.
        """
        # Step 1: Route
        route: RouteDecision = _router.process(data)

        # Step 2: Enrich context with memory + specificity
        if route.brain_input is not None:
            self._enrich_context(route)

        # Step 3: Dispatch to brain(s)
        brain_results = _dispatcher.process(route)

        # Step 4: Collect results
        spinal_result = _collector.process((route, brain_results))

        return spinal_result

    def _enrich_context(self, route: RouteDecision) -> None:
        """Add token-value context to the brain input."""
        brain_input = route.brain_input
        if brain_input is None:
            return

        # Pass specificity tier through for response formatting
        brain_input.context["specificity_tier"] = getattr(
            route, "specificity_tier", ""
        )
        brain_input.context["route_mode"] = route.mode

        # Enrich with relevant memory if available
        if self._memory_manager is not None:
            # Inject memory manager so downstream departments (logic engine) can search
            brain_input.context["memory_manager"] = self._memory_manager
            # Inject graph store for relationship-based reasoning
            if hasattr(self._memory_manager, "_graph"):
                brain_input.context["graph_store"] = self._memory_manager._graph
            try:
                search_result = self._memory_manager.search(
                    brain_input.text, top_k=3
                )
                if hasattr(search_result, "tokens") and search_result.tokens:
                    brain_input.context["memory_hints"] = [
                        {"id": t.id, "text": t.text, "importance": t.importance}
                        for t in search_result.tokens[:3]
                    ]
            except Exception:
                pass  # memory enrichment is optional


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API — the one function other systems call
# ═══════════════════════════════════════════════════════════════

_forwarder = Forwarder()


def think(text: str) -> SpinalResult | None:
    """
    The Core Brain's public interface.

    Feed it text → it classifies, routes, processes through the
    appropriate brain hemisphere(s), and returns a SpinalResult.

    Usage:
        from core.routing.forwarder import think
        result = think("what is 5 plus 3?")
        print(result.analytical.response)  # "5 + 3 = 8"
    """
    return _forwarder.process(text)


def set_memory(memory_manager: Any) -> None:
    """Inject the v2 memory manager into the brain pipeline."""
    _forwarder.set_memory(memory_manager)
