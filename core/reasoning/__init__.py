"""
Multi-Agent Reasoning System (add-on)

A contextual, multi-agent reasoning stack layered on top of Quarky's existing
dual-brain pipeline. Specialised agents generate parallel reasoning paths which
are then evaluated by three *independent* signals rather than a single score:

  - Correctness  (truth validation)        — logic / evidence agent confidence
  - Coherence    (consistency checking)    — CoherenceLayer
  - Contextual   (task-dependent value)    — ContextualEvaluator

Layers:
  agents      LogicAgent, CreativityAgent, EvidenceAgent, MemoryAgent
  dispatcher  MultiAgentDispatcher — runs agents in parallel
  coherence   CoherenceLayer — flags contradictions, preserves all paths
  belief      BeliefStateTracker — gradual confidence revision over turns
  contextual  ContextualEvaluator — value-based, task-aware path selection
  engine      MultiAgentReasoningEngine — orchestrates the full stack
"""

from core.reasoning.types import (
    AgentOutput,
    BeliefState,
    CoherenceReport,
    ContextualEvaluation,
    ContextualScore,
    ContradictionFlag,
    ReasoningOutcome,
    TaskType,
)
from core.reasoning.agents import (
    ReasoningAgent,
    LogicAgent,
    CreativityAgent,
    EvidenceAgent,
    MemoryAgent,
    default_agents,
)
from core.reasoning.dispatcher import MultiAgentDispatcher
from core.reasoning.coherence import CoherenceLayer
from core.reasoning.belief_state import BeliefStateTracker
from core.reasoning.contextual_evaluation import (
    ContextualEvaluator,
    detect_task_type,
)
from core.reasoning.synthesizer import synthesize
from core.reasoning.engine import MultiAgentReasoningEngine

__all__ = [
    # types
    "AgentOutput",
    "BeliefState",
    "CoherenceReport",
    "ContextualEvaluation",
    "ContextualScore",
    "ContradictionFlag",
    "ReasoningOutcome",
    "TaskType",
    # agents
    "ReasoningAgent",
    "LogicAgent",
    "CreativityAgent",
    "EvidenceAgent",
    "MemoryAgent",
    "default_agents",
    # layers
    "MultiAgentDispatcher",
    "CoherenceLayer",
    "BeliefStateTracker",
    "ContextualEvaluator",
    "detect_task_type",
    "synthesize",
    "MultiAgentReasoningEngine",
]
