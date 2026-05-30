"""
Tests for the Multi-Agent Reasoning System (core.reasoning).

Covers each layer independently plus an end-to-end engine run:
  - Agents produce structured AgentOutput
  - Dispatcher runs agents in parallel and preserves order
  - Coherence Layer flags contradictions without discarding paths
  - Belief State Layer revises confidence gradually over turns
  - Contextual Evaluation classifies task type and applies policy profiles
  - Engine separates correctness / coherence / contextual value signals
"""

import pytest

from core.reasoning import (
    AgentOutput,
    BeliefStateTracker,
    CoherenceLayer,
    ContextualEvaluator,
    CreativityAgent,
    EvidenceAgent,
    LogicAgent,
    MemoryAgent,
    MultiAgentDispatcher,
    MultiAgentReasoningEngine,
    ReasoningOutcome,
    TaskType,
    default_agents,
    detect_task_type,
)


# ─── Agents ──────────────────────────────────────────────────

class TestAgents:
    def test_logic_agent_returns_output(self):
        out = LogicAgent().reason("Is the sky blue?")
        assert isinstance(out, AgentOutput)
        assert out.agent == "logic"
        assert out.claims
        assert 0.0 <= out.confidence <= 1.0

    def test_creativity_agent_is_exploratory(self):
        out = CreativityAgent().reason("combine music and math")
        assert out.agent == "creativity"
        assert out.metadata.get("exploratory") is True

    def test_evidence_agent_uses_injected_facts(self):
        out = EvidenceAgent().reason("water boils", context={"facts": ["water boils at 100C"]})
        assert "water boils at 100C" in out.evidence

    def test_memory_agent_matches_history(self):
        out = MemoryAgent().reason(
            "tell me about water", context={"history": ["we discussed water earlier"]}
        )
        assert out.metadata["matched_turns"] >= 1

    def test_agent_never_raises_on_bad_context(self):
        # A faulty memory_manager must not break the agent.
        class Boom:
            def search(self, *a, **k):
                raise RuntimeError("nope")

        out = EvidenceAgent().reason("anything", context={"memory_manager": Boom()})
        assert isinstance(out, AgentOutput)
        assert out.confidence >= 0.0


# ─── Dispatcher ──────────────────────────────────────────────

class TestDispatcher:
    def test_runs_all_agents(self):
        disp = MultiAgentDispatcher()
        outputs = disp.dispatch("Is the sky blue?")
        names = {o.agent for o in outputs}
        assert names == {"logic", "creativity", "evidence", "memory"}

    def test_preserves_registration_order(self):
        agents = default_agents()
        disp = MultiAgentDispatcher(agents)
        outputs = disp.dispatch("hello world")
        assert [o.agent for o in outputs] == [a.name for a in agents]


# ─── Coherence Layer ─────────────────────────────────────────

class TestCoherence:
    def test_no_contradiction_when_consistent(self):
        outs = [
            AgentOutput(agent="logic", response="The sky is blue", claims=["The sky is blue"]),
            AgentOutput(agent="evidence", response="The sky is blue", claims=["The sky is blue"]),
        ]
        report = CoherenceLayer().analyze(outs)
        assert report.consistent
        assert report.coherence_score == 1.0

    def test_detects_direct_contradiction(self):
        outs = [
            AgentOutput(agent="logic", response="The sky is blue", claims=["The sky is blue"]),
            AgentOutput(agent="creativity", response="The sky is not blue", claims=["The sky is not blue"]),
        ]
        report = CoherenceLayer().analyze(outs)
        assert not report.consistent
        assert report.contradictions[0].kind == "claim"

    def test_contradiction_preserves_all_paths(self):
        outs = [
            AgentOutput(agent="logic", response="X is true", claims=["X is true"]),
            AgentOutput(agent="creativity", response="X is not true", claims=["X is not true"]),
        ]
        report = CoherenceLayer().analyze(outs)
        # Disagreement flagged but both paths retained.
        assert set(report.preserved_paths) == {"logic", "creativity"}


# ─── Belief State Layer ──────────────────────────────────────

class TestBeliefState:
    def test_tracks_new_belief(self):
        tracker = BeliefStateTracker()
        outs = [AgentOutput(agent="logic", claims=["water boils at 100C"], confidence=0.9)]
        tracker.update(outs)
        state = tracker.get("water boils at 100C")
        assert state is not None
        assert state.support_count == 1

    def test_revision_is_gradual_not_binary(self):
        tracker = BeliefStateTracker(learning_rate=0.3)
        outs = [AgentOutput(agent="logic", claims=["X holds"], confidence=1.0)]
        tracker.update(outs)
        state = tracker.get("X holds")
        # Started at 0.5, moves only part-way toward 1.0 in one step.
        assert 0.5 < state.confidence < 1.0

    def test_confidence_converges_over_turns(self):
        tracker = BeliefStateTracker(learning_rate=0.5)
        outs = [AgentOutput(agent="logic", claims=["X holds"], confidence=1.0)]
        for _ in range(6):
            tracker.update(outs)
        state = tracker.get("X holds")
        assert state.confidence > 0.9
        assert len(state.history) == 6

    def test_contradiction_dampens_confidence(self):
        from core.reasoning import CoherenceReport, ContradictionFlag

        tracker = BeliefStateTracker(learning_rate=0.5)
        outs = [AgentOutput(agent="logic", claims=["disputed claim"], confidence=1.0)]
        coherence = CoherenceReport(
            contradictions=[
                ContradictionFlag(agent_a="logic", agent_b="creativity", kind="claim", detail="x")
            ]
        )
        tracker.update(outs, coherence)
        state = tracker.get("disputed claim")
        # Dampened target (0.5*1.0) keeps confidence around the starting point.
        assert state.confidence <= 0.6
        assert state.contradiction_count == 1


# ─── Contextual Evaluation Layer ─────────────────────────────

class TestContextualEvaluation:
    def test_detect_verification(self):
        assert detect_task_type("Is the earth round?") == TaskType.VERIFICATION

    def test_detect_exploration(self):
        assert detect_task_type("What if we merged two ideas?") == TaskType.EXPLORATION

    def test_detect_explanation(self):
        assert detect_task_type("Why does ice float?") == TaskType.EXPLANATION

    def test_detect_mixed(self):
        assert detect_task_type("Is this true and what if it changed?") == TaskType.MIXED

    def test_verification_prioritizes_logic_and_evidence(self):
        outs = [
            AgentOutput(agent="logic", response="r", claims=["c"], confidence=0.8),
            AgentOutput(agent="evidence", response="r", claims=["c"], evidence=["e"], confidence=0.8),
            AgentOutput(agent="creativity", response="r", claims=["c"], confidence=0.4),
            AgentOutput(agent="memory", response="r", claims=["c"], confidence=0.3),
        ]
        ev = ContextualEvaluator().evaluate("Is X true?", outs, TaskType.VERIFICATION)
        assert ev.task_type == TaskType.VERIFICATION
        top_two = ev.prioritized_agents[:2]
        assert "logic" in top_two and "evidence" in top_two

    def test_exploration_prioritizes_creativity(self):
        outs = default_agents_outputs()
        ev = ContextualEvaluator().evaluate("What if?", outs, TaskType.EXPLORATION)
        assert ev.prioritized_agents[0] == "creativity"

    def test_mixed_preserves_multiple_paths(self):
        outs = default_agents_outputs()
        ev = ContextualEvaluator().evaluate("mixed query", outs, TaskType.MIXED)
        assert len(ev.prioritized_agents) >= 2


def default_agents_outputs():
    return [
        AgentOutput(agent="logic", response="r", claims=["c"], confidence=0.6),
        AgentOutput(agent="creativity", response="r", claims=["c"], confidence=0.6,
                    metadata={"exploratory": True}),
        AgentOutput(agent="evidence", response="r", claims=["c"], confidence=0.6),
        AgentOutput(agent="memory", response="r", claims=["c"], confidence=0.6),
    ]


# ─── Engine (integration) ────────────────────────────────────

class TestEngine:
    def test_engine_returns_outcome(self):
        out = MultiAgentReasoningEngine().reason("Is the sky blue?")
        assert isinstance(out, ReasoningOutcome)
        assert out.response

    def test_engine_reports_three_independent_signals(self):
        out = MultiAgentReasoningEngine().reason("Why does ice float?")
        assert set(out.signals) == {"correctness", "coherence", "contextual_value"}
        for v in out.signals.values():
            assert 0.0 <= v <= 1.0

    def test_engine_routes_verification_to_logic_evidence(self):
        out = MultiAgentReasoningEngine().reason("Is water made of hydrogen?")
        assert out.task_type == TaskType.VERIFICATION
        assert out.contextual.profile == "logic+evidence"

    def test_engine_routes_exploration_to_creativity(self):
        out = MultiAgentReasoningEngine().reason("What if cars could fly?")
        assert out.task_type == TaskType.EXPLORATION
        assert "creativity" in out.contextual.prioritized_agents

    def test_engine_preserves_beliefs_across_turns(self):
        engine = MultiAgentReasoningEngine()
        engine.reason("Is the sky blue?")
        engine.reason("Is the sky blue?")
        # Belief store accumulates across turns.
        assert engine.beliefs.all_beliefs()

    def test_mixed_task_synthesis_lists_perspectives(self):
        out = MultiAgentReasoningEngine().reason("Is it true and what if it were not?")
        assert out.task_type == TaskType.MIXED
        assert "perspective" in out.response.lower()
