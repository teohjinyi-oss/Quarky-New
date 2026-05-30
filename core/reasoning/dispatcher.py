"""
Multi-Agent Reasoning: Parallel Dispatcher

Runs the configured agents concurrently and collects their structured
``AgentOutput`` paths. Mirrors the threading approach used by the existing
``core.routing.parallel_dispatcher`` so behaviour is familiar.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.reasoning.agents import ReasoningAgent, default_agents
from core.reasoning.types import AgentOutput


class MultiAgentDispatcher:
    """Fires every agent in parallel and returns their reasoning paths."""

    def __init__(self, agents: list[ReasoningAgent] | None = None, timeout: float = 5.0):
        self.agents = agents if agents is not None else default_agents()
        self.timeout = timeout

    def dispatch(self, query: str, context: dict[str, Any] | None = None) -> list[AgentOutput]:
        """Run all agents on the query; preserve agent order in the result."""
        ctx = context or {}
        if not self.agents:
            return []

        results: dict[str, AgentOutput] = {}
        with ThreadPoolExecutor(
            max_workers=len(self.agents), thread_name_prefix="agent"
        ) as pool:
            futures = {
                pool.submit(agent.reason, query, ctx): agent.name
                for agent in self.agents
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result(timeout=self.timeout)
                except Exception as exc:
                    results[name] = AgentOutput(
                        agent=name,
                        reasoning_trace=[f"dispatch error: {exc}"],
                    )

        # Return in the deterministic order the agents were registered.
        return [results[a.name] for a in self.agents if a.name in results]
