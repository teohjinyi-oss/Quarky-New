"""
Decision Engine: Output Gate Department (v2)

THE ONLY thing that speaks to the user.
Final formatting, delivery, and the public API for the Decision Engine.

v2 enhancements:
  - GUI-ready output (rich text, markdown formatting)
  - Specificity tier passthrough for UI styling
  - Token context in metadata for learning feedback
  - Stream-ready: can chunk responses for progressive display

Orchestrates: Collector → Evaluator → Merger → ActionResolver → MemoryUpdater → Action Execution → Output.
"""

from dataclasses import dataclass, field
from typing import Any

from AppStudio.Infrastructure.base import SpinalResult
from MAIINNN.Connectors.forwarder import think
from MAIINNN.Decision.collector import collect, DecisionContext
from MAIINNN.Decision.evaluator import evaluate, EvalScores
from MAIINNN.Decision.merger import merge, MergedResult
from MAIINNN.Decision.action_resolver import resolve, ActionRequest
from MAIINNN.Decision.memory_updater import update_memory
from MAIINNN.Functions.result_reporter import ActionResult
from MAIINNN.Functions.action.receiver import execute as execute_action
from MAIINNN.Functions.action.undo_manager import record as record_undo


@dataclass
class FinalOutput:
    """The complete output package delivered to the user."""
    response: str
    confidence: float
    source: str                         # "analytical", "creative", "merged", "fallback"
    action_request: ActionRequest | None = None
    action_result: ActionResult | None = None
    memory_actions: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    memory_context: str = ""
    specificity_tier: str = ""          # v2: for GUI styling
    metadata: dict[str, Any] = field(default_factory=dict)


def decide(spinal: SpinalResult) -> FinalOutput:
    """
    Run the full Decision Engine pipeline on a SpinalResult.
    Returns the final user-facing output.
    """
    # Step 1: Collect context
    ctx: DecisionContext = collect(spinal)

    # v2: Pass specificity tier from brain context through to evaluator
    if spinal.analytical and spinal.analytical.metadata:
        ctx.extra["specificity_tier"] = spinal.analytical.metadata.get(
            "specificity_tier", ""
        )

    # Step 2: Evaluate signal strengths
    scores: EvalScores = evaluate(ctx)

    # Step 3: Merge brain outputs
    merged: MergedResult = merge(ctx, scores)

    # Step 4: Resolve actions (if needed)
    action_req: ActionRequest | None = resolve(ctx, scores)

    # Step 5: Update memory
    mem_actions: list[str] = update_memory(ctx, scores, merged)

    # Step 6: Execute action if safe (LOW/MEDIUM auto-execute)
    action_result: ActionResult | None = None
    if action_req and not action_req.needs_confirmation:
        action_result = execute_action(action_req, confirmed=False)
        # Record undo if the action was successful and has undo info
        if action_result.success and action_result.undo_info:
            record_undo(action_req.action_type, action_result.undo_info)

    # Step 7: Final formatting
    response = _format_response(merged, action_req, action_result)

    return FinalOutput(
        response=response,
        confidence=merged.confidence,
        source=merged.source,
        action_request=action_req,
        action_result=action_result,
        memory_actions=mem_actions,
        reasoning=merged.reasoning,
        memory_context=merged.memory_context,
        specificity_tier=merged.specificity_tier,
        metadata={
            "route_mode": ctx.extra.get("route_mode", ""),
            "memory_hits": ctx.memory_hits,
        },
    )


def _format_response(merged: MergedResult, action: ActionRequest | None,
                     action_result: ActionResult | None = None) -> str:
    """
    Apply final formatting to the response.
    Handles action confirmation prompts, action results, and memory context.
    """
    text = merged.response.strip()

    # If action was executed, show the result
    if action_result is not None:
        if action_result.success:
            text = action_result.message
        else:
            # Check if it needs confirmation (not a real failure)
            data = action_result.data
            if isinstance(data, dict) and data.get("needs_confirmation"):
                pass  # Will be handled by confirmation flow below
            # Don't append handler-not-found errors — just keep brain response
            elif "No handler registered" not in (action_result.message or ""):
                text = f"{text}\n\n{action_result.message}"

    # If action requires confirmation, show detailed preview
    if action and action.needs_confirmation:
        risk = action.risk_level
        if risk == "CRITICAL":
            text = (f"⚠ CRITICAL ACTION: {action.action_type} → {action.target}\n"
                    f"Risk Level: CRITICAL\n"
                    f"This requires your explicit confirmation.\n"
                    f"Type 'y' to confirm or 'n' to cancel.")
        elif risk == "HIGH":
            text = (f"⚡ Action: {action.action_type} → {action.target}\n"
                    f"Risk Level: HIGH\n"
                    f"Confirm? (y/n)")

    return text


def confirm_action(action_request: ActionRequest) -> ActionResult:
    """
    Execute a previously-confirmed action.
    Called after user types 'y' to a confirmation prompt.
    """
    result = execute_action(action_request, confirmed=True)
    if result.success and result.undo_info:
        record_undo(action_request.action_type, result.undo_info)
    return result


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API — the one function the interface layer calls
# ═══════════════════════════════════════════════════════════════

def process(text: str) -> FinalOutput:
    """
    The Decision Engine's public interface.
    Feed it raw user text → it runs the full pipeline:
      Brain (think) → Collect → Evaluate → Merge → Action → Memory → Output

    Usage:
        from MAIINNN.Decision.output_gate import process
        result = process("what is 5 plus 3?")
        print(result.response)
    """
    spinal = think(text)
    if spinal is None:
        return FinalOutput(
            response="I couldn't process that. Could you try again?",
            confidence=0.0,
            source="error",
        )
    return decide(spinal)
