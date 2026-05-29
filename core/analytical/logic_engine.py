"""
Analytical Brain: Logic Engine Department

Semantic reasoning when pattern matcher has no direct answer.
Uses memory search + embeddings to find relevant knowledge,
applies deduction chains, and constructs analytical responses.

Strategy:
  - Entity types detected → infer what the user wants
  - Search memory for semantically similar past knowledge
  - Use graph relationships to chain reasoning
  - Command intent → map to action description
  - Question with no stored answer → honest "I don't know yet"
"""

import re
from dataclasses import dataclass, field
from typing import Any

from runtime.infrastructure.base import Department
from core.analytical.parser import ParsedInput
from core.analytical.pattern_matcher import MatchResult
from core.nlp.embeddings import text_similarity


@dataclass
class ReasoningChain:
    """A chain of logical deduction steps."""
    steps: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    source: str = ""            # "pattern" | "logic" | "calculator" | "fallback"


# ─── Reasoning rules ────────────────────────────────────────

def _reason_command(parsed: ParsedInput) -> ReasoningChain:
    """Reason about command-type inputs → what action is needed."""
    text = parsed.brain_input.text
    entities = parsed.brain_input.entities
    steps = []

    steps.append(f"Detected intent: COMMAND")

    # Check for app names
    apps = entities.get("app_names", [])
    if apps:
        app = apps[0]
        steps.append(f"Target application: {app}")

        # Determine action verb
        if re.search(r'\b(open|launch|start|run)\b', text, re.I):
            steps.append(f"Action: OPEN {app}")
            return ReasoningChain(
                steps=steps,
                conclusion=f"Opening {app} for you.",
                confidence=0.85,
                source="logic",
            )
        elif re.search(r'\b(close|stop|kill|quit|exit)\b', text, re.I):
            steps.append(f"Action: CLOSE {app}")
            return ReasoningChain(
                steps=steps,
                conclusion=f"Closing {app}.",
                confidence=0.85,
                source="logic",
            )

    # Check for system commands
    if re.search(r'\b(volume|sound)\b', text, re.I):
        if re.search(r'\b(up|raise|increase|louder)\b', text, re.I):
            steps.append("Action: VOLUME UP")
            return ReasoningChain(steps=steps, conclusion="Turning volume up.", confidence=0.8, source="logic")
        elif re.search(r'\b(down|lower|decrease|quieter|softer)\b', text, re.I):
            steps.append("Action: VOLUME DOWN")
            return ReasoningChain(steps=steps, conclusion="Turning volume down.", confidence=0.8, source="logic")
        elif re.search(r'\b(mute|silence)\b', text, re.I):
            steps.append("Action: MUTE")
            return ReasoningChain(steps=steps, conclusion="Muting sound.", confidence=0.85, source="logic")

    if re.search(r'\b(brightness)\b', text, re.I):
        if re.search(r'\b(up|raise|increase|brighter)\b', text, re.I):
            return ReasoningChain(steps=["Action: BRIGHTNESS UP"], conclusion="Increasing brightness.", confidence=0.8, source="logic")
        elif re.search(r'\b(down|lower|decrease|dimmer)\b', text, re.I):
            return ReasoningChain(steps=["Action: BRIGHTNESS DOWN"], conclusion="Decreasing brightness.", confidence=0.8, source="logic")

    if re.search(r'\bscreenshot\b', text, re.I):
        return ReasoningChain(steps=["Action: SCREENSHOT"], conclusion="Taking a screenshot.", confidence=0.9, source="logic")

    if re.search(r'\b(shutdown|shut down)\b', text, re.I):
        return ReasoningChain(steps=["Action: SHUTDOWN (CRITICAL)"], conclusion="This would shut down your computer. Confirm?", confidence=0.9, source="logic")

    if re.search(r'\brestart\b', text, re.I):
        return ReasoningChain(steps=["Action: RESTART (CRITICAL)"], conclusion="This would restart your computer. Confirm?", confidence=0.9, source="logic")

    # Generic command fallback
    steps.append("Could not map to specific action")
    return ReasoningChain(
        steps=steps,
        conclusion=f"I understand you want me to do something, but I need more specifics.",
        confidence=0.3,
        source="fallback",
    )


def _reason_factual(parsed: ParsedInput) -> ReasoningChain:
    """Reason about factual questions using semantic memory search."""
    focus = parsed.question_focus
    keywords = parsed.brain_input.keywords
    text = parsed.brain_input.text

    steps = [f"Question focus: '{focus}'"]
    steps.append(f"Keywords: {keywords}")

    # Try semantic memory search
    memory_mgr = parsed.brain_input.context.get("memory_manager")
    if memory_mgr:
        try:
            results = memory_mgr.search(text, top_k=5)
            if results and hasattr(results, "tokens") and results.tokens:
                # Score each result by semantic similarity to the query
                scored = []
                for token in results.tokens:
                    if hasattr(token, "text") and token.text:
                        sim = text_similarity(text, token.text)
                        scored.append((token, sim))

                scored.sort(key=lambda x: x[1], reverse=True)
                best_token, best_sim = scored[0] if scored else (None, 0.0)

                if best_token and best_sim > 0.35:
                    answer_text = best_token.text
                    # If it's a stored Q&A pair, extract just the answer
                    if "\nA: " in answer_text:
                        answer_text = answer_text.split("\nA: ", 1)[1]
                    steps.append(f"Found relevant memory (similarity: {best_sim:.2f})")
                    steps.append(f"Source: {getattr(best_token, 'source', 'memory')}")
                    return ReasoningChain(
                        steps=steps,
                        conclusion=answer_text,
                        confidence=min(0.85, best_sim + 0.2),
                        source="memory",
                    )
                else:
                    steps.append(f"Memory search returned results but low similarity (best: {best_sim:.2f})")
        except Exception:
            steps.append("Memory search failed")

    # Try graph-based reasoning
    graph = parsed.brain_input.context.get("graph_store")
    if graph and focus:
        try:
            neighbors = graph.get_neighbors(focus.lower(), depth=2)
            if neighbors:
                facts = []
                for neighbor, relation, attrs in neighbors[:3]:
                    facts.append(f"{focus} {relation} {neighbor}")
                steps.append(f"Graph found {len(neighbors)} related concepts")
                conclusion = ". ".join(facts) + "."
                return ReasoningChain(
                    steps=steps,
                    conclusion=conclusion,
                    confidence=0.55,
                    source="logic",
                )
        except Exception:
            pass

    if focus:
        steps.append("No relevant knowledge found in memory or graph")
        return ReasoningChain(
            steps=steps,
            conclusion=f"I don't have knowledge about '{focus}' yet. "
                       f"I can learn if you teach me, or I can search the web.",
            confidence=0.15,
            source="fallback",
        )

    return ReasoningChain(
        steps=steps,
        conclusion="I'm not sure what you're asking. Could you rephrase?",
        confidence=0.1,
        source="fallback",
    )


def _reason_definition(parsed: ParsedInput) -> ReasoningChain:
    """Handle definition-type questions using memory search."""
    focus = parsed.question_focus
    text = parsed.brain_input.text

    steps = [f"Definition request for: '{focus}'"]

    # Search memory for definition
    memory_mgr = parsed.brain_input.context.get("memory_manager")
    if memory_mgr and focus:
        try:
            results = memory_mgr.search(f"what is {focus}", top_k=5)
            if results and hasattr(results, "tokens") and results.tokens:
                scored = []
                for token in results.tokens:
                    if hasattr(token, "text") and token.text:
                        sim = text_similarity(text, token.text)
                        scored.append((token, sim))

                scored.sort(key=lambda x: x[1], reverse=True)
                best_token, best_sim = scored[0] if scored else (None, 0.0)

                if best_token and best_sim > 0.3:
                    answer_text = best_token.text
                    if "\nA: " in answer_text:
                        answer_text = answer_text.split("\nA: ", 1)[1]
                    steps.append(f"Found definition in memory (similarity: {best_sim:.2f})")
                    return ReasoningChain(
                        steps=steps,
                        conclusion=answer_text,
                        confidence=min(0.8, best_sim + 0.2),
                        source="memory",
                    )
        except Exception:
            pass

    return ReasoningChain(
        steps=[f"Definition request for: '{focus}'", "Not found in knowledge base"],
        conclusion=f"I don't have a definition for '{focus}' in my knowledge base yet. "
                   f"You can teach me by saying 'remember that {focus} means...'",
        confidence=0.2,
        source="fallback",
    )


def _reason_general(parsed: ParsedInput) -> ReasoningChain:
    """Generic analytical reasoning using semantic search."""
    keywords = parsed.brain_input.keywords
    entities = parsed.brain_input.entities
    text = parsed.brain_input.text

    steps = [f"General analytical task"]
    if keywords:
        steps.append(f"Key concepts: {', '.join(keywords[:5])}")
    if entities:
        for etype, evals in entities.items():
            steps.append(f"Found {etype}: {evals}")

    if not keywords:
        return ReasoningChain(
            steps=steps,
            conclusion="I couldn't extract clear meaning from that. Could you be more specific?",
            confidence=0.1,
            source="fallback",
        )

    # Search memory for any relevant context
    memory_mgr = parsed.brain_input.context.get("memory_manager")
    if memory_mgr:
        try:
            results = memory_mgr.search(text, top_k=3)
            if results and hasattr(results, "tokens") and results.tokens:
                scored = []
                for token in results.tokens:
                    if hasattr(token, "text") and token.text:
                        sim = text_similarity(text, token.text)
                        scored.append((token, sim))

                scored.sort(key=lambda x: x[1], reverse=True)
                best_token, best_sim = scored[0] if scored else (None, 0.0)

                if best_token and best_sim > 0.3:
                    answer_text = best_token.text
                    if "\nA: " in answer_text:
                        answer_text = answer_text.split("\nA: ", 1)[1]
                    steps.append(f"Found related context in memory (similarity: {best_sim:.2f})")
                    return ReasoningChain(
                        steps=steps,
                        conclusion=answer_text,
                        confidence=min(0.7, best_sim + 0.15),
                        source="memory",
                    )
        except Exception:
            pass

    return ReasoningChain(
        steps=steps,
        conclusion=f"I understand this relates to: {', '.join(keywords[:3])}. "
                   f"Could you tell me what you'd like me to do with it?",
        confidence=0.3,
        source="fallback",
    )


# Route map: task_type → reasoning function
_REASONERS = {
    "command":    _reason_command,
    "factual":    _reason_factual,
    "definition": _reason_definition,
    "comparison": _reason_factual,   # same logic for now
    "general":    _reason_general,
    "math":       _reason_general,   # calculator already handled math
}


class LogicEngine(Department):
    """
    Applies rule-based reasoning when pattern matcher has no answer.
    Falls back gracefully with honest uncertainty.
    """

    def __init__(self):
        super().__init__("logic_engine", "core.analytical")

    def process(self, data: Any) -> Any:
        if not isinstance(data, ParsedInput):
            return data

        ctx = data.brain_input.context

        # If pattern matcher already found a strong match, skip reasoning
        match_result: MatchResult | None = ctx.get("pattern_match")
        if match_result and match_result.has_match and match_result.best_match:
            if match_result.best_match.confidence >= 0.7:
                ctx["reasoning"] = ReasoningChain(
                    steps=["Pattern match found — using direct answer"],
                    conclusion=match_result.best_match.answer,
                    confidence=match_result.best_match.confidence,
                    source="pattern",
                )
                return data

        # If calculator produced a result, use it
        calc_result = ctx.get("calc_result")
        if calc_result and calc_result.success:
            ctx["reasoning"] = ReasoningChain(
                steps=[f"Calculated: {calc_result.formatted}"],
                conclusion=calc_result.formatted,
                confidence=0.95,
                source="calculator",
            )
            return data

        # Apply reasoning based on task type
        reasoner = _REASONERS.get(data.task_type, _reason_general)
        chain = reasoner(data)
        ctx["reasoning"] = chain

        return data
