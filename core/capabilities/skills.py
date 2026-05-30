"""
Unified Skill Interface & Planner (Phase 3)

Quarky already has real OS-level reach (web, monitor, habits, automation,
integrations) — an edge sandboxed cloud agents lack. But those tools were wired
ad-hoc. This module gives them **one consistent interface** plus a small planner
so Quarky can *chain* skills into multi-step plans: the foundation of genuine
agentic behaviour.

Design:
  - :class:`Skill` — a uniform contract (name, description, ``can_handle`` and
    ``run``). Any existing capability can be wrapped as a Skill.
  - :class:`SkillRegistry` — registration + intent-based lookup.
  - :class:`SkillPlanner` — turns a request into an ordered :class:`SkillPlan`
    of steps (optionally feeding each step's output into the next) and executes
    it, collecting per-step results.

Everything here is dependency-free and offline; wrapping a heavier capability
only requires implementing the two abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillResult:
    """Outcome of running a single skill."""

    skill: str
    success: bool
    output: Any = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class Skill(ABC):
    """Uniform contract every Quarky capability is adapted to."""

    name: str = "skill"
    description: str = ""

    @abstractmethod
    def can_handle(self, request: str, context: dict[str, Any]) -> float:
        """Return a 0.0–1.0 confidence that this skill applies to the request."""
        ...

    @abstractmethod
    def run(self, request: str, context: dict[str, Any]) -> SkillResult:
        """Execute the skill for the request."""
        ...


class FunctionSkill(Skill):
    """Adapter that turns a plain function into a Skill.

    Lets existing capability functions join the registry without subclassing::

        FunctionSkill("echo", lambda req, ctx: req, keywords=["echo", "say"])
    """

    def __init__(
        self,
        name: str,
        func: Callable[[str, dict[str, Any]], Any],
        keywords: list[str] | None = None,
        description: str = "",
    ):
        self.name = name
        self.description = description
        self._func = func
        self._keywords = [k.lower() for k in (keywords or [])]

    def can_handle(self, request: str, context: dict[str, Any]) -> float:
        if not self._keywords:
            return 0.1
        low = request.lower()
        hits = sum(1 for k in self._keywords if k in low)
        return min(1.0, hits / len(self._keywords)) if hits else 0.0

    def run(self, request: str, context: dict[str, Any]) -> SkillResult:
        try:
            output = self._func(request, context)
            return SkillResult(self.name, True, output=output)
        except Exception as exc:
            return SkillResult(self.name, False, message=str(exc))


class SkillRegistry:
    """Holds registered skills and finds the best one for a request."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not getattr(skill, "name", ""):
            raise ValueError("Skill must define a non-empty 'name'.")
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> None:
        self._skills.pop(name, None)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def match(
        self, request: str, context: dict[str, Any] | None = None,
        threshold: float = 0.1,
    ) -> list[tuple[Skill, float]]:
        """Rank skills by their ``can_handle`` confidence for the request."""
        ctx = context or {}
        scored = [
            (s, round(s.can_handle(request, ctx), 4)) for s in self._skills.values()
        ]
        scored = [(s, c) for s, c in scored if c >= threshold]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    def best(
        self, request: str, context: dict[str, Any] | None = None
    ) -> Skill | None:
        ranked = self.match(request, context)
        return ranked[0][0] if ranked else None


@dataclass
class PlanStep:
    """One step in a skill plan."""

    skill: str
    request: str
    feed_forward: bool = False        # pass this step's output to the next step


@dataclass
class SkillPlan:
    """An ordered set of steps the planner will execute."""

    steps: list[PlanStep] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.steps)


@dataclass
class PlanExecution:
    """The result of running a plan."""

    results: list[SkillResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.results) and all(r.success for r in self.results)

    @property
    def final_output(self) -> Any:
        return self.results[-1].output if self.results else None


class SkillPlanner:
    """Builds and executes ordered skill plans (single- and multi-step)."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def plan(self, request: str, context: dict[str, Any] | None = None) -> SkillPlan:
        """Build a plan for a request.

        Supports explicit chaining: splitting the request on " then " yields a
        sequential, output-feeding plan. A single request becomes a one-step
        plan routed to the best-matching skill.
        """
        ctx = context or {}
        segments = [seg.strip() for seg in request.split(" then ") if seg.strip()]
        steps: list[PlanStep] = []
        for i, segment in enumerate(segments):
            skill = self.registry.best(segment, ctx)
            if skill is None:
                continue
            steps.append(PlanStep(
                skill=skill.name,
                request=segment,
                feed_forward=(i < len(segments) - 1),
            ))
        return SkillPlan(steps=steps)

    def execute(
        self, plan: SkillPlan, context: dict[str, Any] | None = None
    ) -> PlanExecution:
        """Run each step in order, optionally feeding outputs forward."""
        ctx = dict(context or {})
        execution = PlanExecution()
        for step in plan.steps:
            skill = self.registry.get(step.skill)
            if skill is None:
                execution.results.append(
                    SkillResult(step.skill, False, message="skill not found")
                )
                break
            result = skill.run(step.request, ctx)
            execution.results.append(result)
            if not result.success:
                break
            if step.feed_forward:
                ctx["previous_output"] = result.output
        return execution

    def run(
        self, request: str, context: dict[str, Any] | None = None
    ) -> PlanExecution:
        """Convenience: plan then execute in one call."""
        return self.execute(self.plan(request, context), context)
