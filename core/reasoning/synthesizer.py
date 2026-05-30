"""
Multi-Agent Reasoning: Synthesizer

Builds the final structured response. For single-objective tasks it leads with
the highest-value path; for mixed tasks it preserves multiple valid perspectives
and presents a structured synthesis instead of collapsing them.
"""

from __future__ import annotations

from core.reasoning.types import (
    AgentOutput,
    CoherenceReport,
    ContextualEvaluation,
    TaskType,
)


def synthesize(
    outputs: list[AgentOutput],
    coherence: CoherenceReport,
    contextual: ContextualEvaluation,
) -> str:
    """Compose a human-readable answer from the prioritized reasoning paths."""
    by_agent = {o.agent: o for o in outputs}
    selected = [by_agent[a] for a in contextual.prioritized_agents if a in by_agent]
    if not selected:
        selected = outputs[:1]

    lines: list[str] = []

    if contextual.task_type == TaskType.MIXED and len(selected) > 1:
        lines.append("Multiple perspectives are relevant here:")
        for out in selected:
            if out.response:
                lines.append(f"- [{out.agent}] {out.response}")
    else:
        lead = selected[0]
        if lead.response:
            lines.append(lead.response)
        for out in selected[1:]:
            if out.response and out.response not in lines[0:1]:
                lines.append(f"Additionally ({out.agent}): {out.response}")

    if coherence.contradictions:
        lines.append(
            f"Note: {len(coherence.contradictions)} differing view(s) were kept "
            "rather than discarded."
        )

    return "\n".join(lines).strip()
