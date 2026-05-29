"""
Automation: Chain

A chain is a sequence of named steps that execute in order.
Each step is a callable that receives the output of the previous step.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class StepResult:
    """Result of a single chain step."""
    name: str
    success: bool
    output: Any = None
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class ChainResult:
    """Result of running an entire chain."""
    chain_name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def final_output(self) -> Any:
        return self.steps[-1].output if self.steps else None


class Chain:
    """An ordered sequence of steps that pipe data forward."""

    def __init__(self, name: str):
        self.name = name
        self._steps: list[tuple[str, Callable[..., Any]]] = []

    def add(self, step_name: str, fn: Callable[..., Any]) -> Chain:
        """Add a step. fn receives (previous_output) and returns next output."""
        self._steps.append((step_name, fn))
        return self

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def run(self, initial_input: Any = None) -> ChainResult:
        """Execute the chain sequentially."""
        result = ChainResult(chain_name=self.name)
        current = initial_input
        for step_name, fn in self._steps:
            t0 = time.perf_counter()
            try:
                current = fn(current)
                dur = (time.perf_counter() - t0) * 1000
                result.steps.append(StepResult(
                    name=step_name, success=True,
                    output=current, duration_ms=round(dur, 2),
                ))
            except Exception as exc:
                dur = (time.perf_counter() - t0) * 1000
                result.steps.append(StepResult(
                    name=step_name, success=False,
                    error=str(exc), duration_ms=round(dur, 2),
                ))
                break  # stop chain on failure
        return result
