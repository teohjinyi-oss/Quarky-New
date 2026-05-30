"""
Multi-Agent Reasoning: Coherence Layer

Detects contradictions between agent reasoning paths. Crucially, disagreement is
*flagged but never discarded* — every path with usable content is preserved so
the contextual layer can decide what is valuable for the task.

Detection heuristics (zero external dependencies):
  - Direct negation: one agent asserts X, another asserts "not X".
  - Conflicting assumptions: shared subject with opposing polarity.
"""

from __future__ import annotations

import re

from core.nlp.tokenizer import keyword_tokens
from core.reasoning.types import AgentOutput, ContradictionFlag, CoherenceReport

_NEGATION = re.compile(r"\b(not|no|never|cannot|can't|isn't|aren't|won't|false)\b", re.I)


def _polarity(text: str) -> str:
    return "negative" if _NEGATION.search(text) else "positive"


def _content_words(text: str) -> set[str]:
    """Meaningful words with negation tokens removed for overlap comparison."""
    words = keyword_tokens(text)
    return {w for w in words if not _NEGATION.fullmatch(w)}


class CoherenceLayer:
    """Compares agent paths and reports contradictions without pruning them."""

    def __init__(self, overlap_threshold: float = 0.5):
        # Minimum content-word overlap (Jaccard) to treat two claims as "about
        # the same thing" before comparing their polarity.
        self.overlap_threshold = overlap_threshold

    def analyze(self, outputs: list[AgentOutput]) -> CoherenceReport:
        report = CoherenceReport()

        # Preserve every path that produced usable content.
        report.preserved_paths = [
            o.agent for o in outputs if o.claims or o.response
        ]

        usable = [o for o in outputs if o.claims or o.response]
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                flag = self._compare(usable[i], usable[j])
                if flag is not None:
                    report.contradictions.append(flag)

        if report.contradictions:
            report.notes.append(
                f"{len(report.contradictions)} contradiction(s) flagged; "
                "all perspectives retained for contextual evaluation."
            )
        else:
            report.notes.append("No contradictions detected across agents.")

        return report

    def _compare(self, a: AgentOutput, b: AgentOutput) -> ContradictionFlag | None:
        """Compare two agents' primary statements for direct conflict."""
        a_claims = a.claims or ([a.response] if a.response else [])
        b_claims = b.claims or ([b.response] if b.response else [])

        for ca in a_claims:
            for cb in b_claims:
                wa, wb = _content_words(ca), _content_words(cb)
                if not wa or not wb:
                    continue
                overlap = len(wa & wb) / len(wa | wb)
                if overlap < self.overlap_threshold:
                    continue
                if _polarity(ca) != _polarity(cb):
                    return ContradictionFlag(
                        agent_a=a.agent,
                        agent_b=b.agent,
                        kind="claim",
                        detail=f"'{ca.strip()}' vs '{cb.strip()}'",
                        severity=round(0.5 + 0.5 * overlap, 4),
                    )
        return None
