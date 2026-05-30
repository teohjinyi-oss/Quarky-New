"""
Tests for Phase 2 reasoning critique + verification (core/reasoning/critique.py).
"""

from core.reasoning import MultiAgentReasoningEngine, CritiqueLayer
from core.reasoning.critique import CritiqueReport
from core.reasoning.types import (
    AgentOutput,
    CoherenceReport,
    ContradictionFlag,
    TaskType,
)


def _outputs():
    return [
        AgentOutput(agent="logic", response="X is true", confidence=0.8,
                    claims=["X is true"], evidence=["fact A"]),
        AgentOutput(agent="evidence", response="supports X", confidence=0.7,
                    claims=["X holds"], evidence=["data B"]),
        AgentOutput(agent="creativity", response="maybe Y", confidence=0.4,
                    claims=["Y possible"], assumptions=["speculative"]),
    ]


class TestCritiqueLayer:
    def test_critiques_every_path(self):
        layer = CritiqueLayer()
        report = layer.review(_outputs(), CoherenceReport(), TaskType.EXPLANATION)
        assert isinstance(report, CritiqueReport)
        assert len(report.critiques) == 3
        assert {c.agent for c in report.critiques} == {"logic", "evidence", "creativity"}

    def test_evidence_is_a_strength(self):
        layer = CritiqueLayer()
        report = layer.review(_outputs(), CoherenceReport(), TaskType.EXPLANATION)
        logic = report.for_agent("logic")
        assert any("evidence" in s for s in logic.strengths)

    def test_no_evidence_is_a_weakness(self):
        layer = CritiqueLayer()
        report = layer.review(_outputs(), CoherenceReport(), TaskType.EXPLANATION)
        creative = report.for_agent("creativity")
        assert any("evidence" in w for w in creative.weaknesses)

    def test_verification_supported(self):
        layer = CritiqueLayer()
        report = layer.review(_outputs(), CoherenceReport(), TaskType.VERIFICATION)
        assert report.verification_verdict == "supported"
        assert report.verification_confidence > 0.5

    def test_verification_disputed_on_contradiction(self):
        layer = CritiqueLayer()
        coherence = CoherenceReport(contradictions=[
            ContradictionFlag("logic", "evidence", "claim", "conflict", 0.8)
        ])
        report = layer.review(_outputs(), coherence, TaskType.VERIFICATION)
        assert report.verification_verdict == "disputed"

    def test_non_verification_is_not_applicable(self):
        layer = CritiqueLayer()
        report = layer.review(_outputs(), CoherenceReport(), TaskType.EXPLORATION)
        assert report.verification_verdict == "not_applicable"

    def test_contradicted_path_loses_confidence(self):
        layer = CritiqueLayer()
        coherence = CoherenceReport(contradictions=[
            ContradictionFlag("logic", "creativity", "claim", "conflict", 0.5)
        ])
        report = layer.review(_outputs(), coherence, TaskType.EXPLANATION)
        logic = report.for_agent("logic")
        assert any("contradicted" in w for w in logic.weaknesses)
        assert logic.revised_confidence < 0.8


class TestEngineIntegration:
    def test_engine_attaches_critique(self):
        outcome = MultiAgentReasoningEngine().reason("Is the sky blue?")
        assert outcome.critique is not None
        assert outcome.critique.verification_verdict in (
            "supported", "disputed", "inconclusive"
        )

    def test_engine_critique_can_be_disabled(self):
        engine = MultiAgentReasoningEngine()
        engine.self_critique_enabled = False
        outcome = engine.reason("Explain rainbows.")
        assert outcome.critique is None
