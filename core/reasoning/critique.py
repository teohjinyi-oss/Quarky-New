"""
Multi-Agent Reasoning: Critique & Verification Layer (Phase 2)

A transparency feature no cloud LLM exposes: the reasoning stack critiques *its
own* paths and, for verification tasks, runs an explicit verification pass.

What it does (all deterministic, zero external dependencies):
  - **Self-critique** — for every agent path, derive concrete strengths
    (evidence present, claims made, coherent with peers) and weaknesses (no
    evidence, unsupported assumptions, contradicted by peers) and produce a
    *revised* confidence rather than trusting the agent's self-report.
  - **Verification loop** — for ``TaskType.VERIFICATION`` queries, cross-check
    the correctness-oriented agents (logic + evidence) against the coherence
    report and emit a verdict: ``supported`` / ``disputed`` / ``inconclusive``.

The layer never discards paths; it annotates them, in keeping with the rest of
the reasoning design.
"""

from __future__ import annotations

from core.reasoning.types import (
    AgentCritique,
    AgentOutput,
    CoherenceReport,
    CritiqueReport,
    TaskType,
)

# Agents whose agreement constitutes "verification" of a factual claim.
_CORRECTNESS_AGENTS = ("logic", "evidence")


class CritiqueLayer:
    """Self-critique and verification over a panel of reasoning paths."""

    def __init__(self, verification_margin: float = 0.15):
        # How decisively the correctness agents must agree (in confidence) for a
        # verification verdict of "supported" rather than "inconclusive".
        self.verification_margin = verification_margin

    # ── public API ────────────────────────────────────────────
    def review(
        self,
        outputs: list[AgentOutput],
        coherence: CoherenceReport,
        task_type: TaskType,
    ) -> CritiqueReport:
        """Critique every path and, for verification tasks, run the check."""
        contradicted = self._contradicted_agents(coherence)
        critiques = [self._critique_one(o, contradicted) for o in outputs]

        report = CritiqueReport(critiques=critiques)
        if task_type == TaskType.VERIFICATION:
            self._verify(outputs, contradicted, report)
        return report

    # ── self-critique ─────────────────────────────────────────
    def _critique_one(
        self, out: AgentOutput, contradicted: set[str]
    ) -> AgentCritique:
        strengths: list[str] = []
        weaknesses: list[str] = []
        confidence = out.confidence

        if out.evidence:
            strengths.append(f"{len(out.evidence)} supporting evidence item(s)")
            confidence = min(1.0, confidence + 0.05)
        else:
            weaknesses.append("no supporting evidence")
            confidence = max(0.0, confidence - 0.05)

        if out.claims:
            strengths.append(f"{len(out.claims)} explicit claim(s)")
        else:
            weaknesses.append("no explicit claim derived")
            confidence = max(0.0, confidence - 0.05)

        # An assumption with no evidence to back it is a weakness.
        if out.assumptions and not out.evidence:
            weaknesses.append("relies on unverified assumptions")

        if out.agent in contradicted:
            weaknesses.append("contradicted by another path")
            confidence = max(0.0, confidence - 0.1)
        elif out.response:
            strengths.append("coherent with the panel")

        return AgentCritique(
            agent=out.agent,
            strengths=strengths,
            weaknesses=weaknesses,
            revised_confidence=round(confidence, 4),
            verified=(out.agent in _CORRECTNESS_AGENTS and not weaknesses),
        )

    # ── verification loop ─────────────────────────────────────
    def _verify(
        self,
        outputs: list[AgentOutput],
        contradicted: set[str],
        report: CritiqueReport,
    ) -> None:
        correctness = [o for o in outputs if o.agent in _CORRECTNESS_AGENTS]
        if not correctness:
            report.verification_verdict = "inconclusive"
            report.notes.append("No correctness-oriented agents available.")
            return

        avg_conf = sum(o.confidence for o in correctness) / len(correctness)
        any_contradicted = any(o.agent in contradicted for o in correctness)

        if any_contradicted:
            verdict = "disputed"
        elif avg_conf >= 0.5 + self.verification_margin:
            verdict = "supported"
        elif avg_conf <= 0.5 - self.verification_margin:
            verdict = "disputed"
        else:
            verdict = "inconclusive"

        report.verification_verdict = verdict
        report.verification_confidence = round(avg_conf, 4)
        report.notes.append(
            f"Verification over {len(correctness)} correctness agent(s): {verdict}."
        )

    # ── helpers ───────────────────────────────────────────────
    @staticmethod
    def _contradicted_agents(coherence: CoherenceReport) -> set[str]:
        flagged: set[str] = set()
        for c in coherence.contradictions:
            flagged.add(c.agent_a)
            flagged.add(c.agent_b)
        return flagged
