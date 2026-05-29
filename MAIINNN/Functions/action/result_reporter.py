"""
Action System: Result Reporter

Dataclasses for action results, action plans (multi-action previews),
and action step descriptions. Every executor returns an ActionResult.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UndoInfo:
    """Information needed to undo an action."""
    undo_type: str              # "file_restore", "volume_revert", "brightness_revert"
    previous_value: Any = None  # previous volume/brightness level, etc.
    trash_path: str = ""        # path in quarky_trash for file restores
    description: str = ""       # human-readable undo description


@dataclass
class ActionResult:
    """The result of executing a single action."""
    success: bool
    message: str
    data: Any = None
    duration_ms: float = 0.0
    undo_info: UndoInfo | None = None


@dataclass
class ActionStep:
    """One step in a multi-action plan."""
    action_type: str
    target: str
    risk_level: str
    description: str            # human-readable: "Open Chrome"
    auto_execute: bool = False  # True if LOW risk → auto-run


@dataclass
class ActionPlan:
    """A plan for multi-action commands, shown as preview before execution."""
    steps: list[ActionStep] = field(default_factory=list)
    total_steps: int = 0
    risky_steps: int = 0       # steps that need confirmation

    def add_step(self, action_type: str, target: str,
                 risk_level: str, description: str) -> None:
        auto = risk_level in ("LOW", "MEDIUM")
        step = ActionStep(
            action_type=action_type,
            target=target,
            risk_level=risk_level,
            description=description,
            auto_execute=auto,
        )
        self.steps.append(step)
        self.total_steps = len(self.steps)
        if not auto:
            self.risky_steps += 1

    def format_preview(self) -> str:
        """Format the plan as a numbered preview for the user."""
        if not self.steps:
            return "No actions planned."

        lines = ["Action Plan:"]
        for i, step in enumerate(self.steps, 1):
            risk_tag = f"[{step.risk_level}]"
            auto_tag = " (auto)" if step.auto_execute else " (confirm)"
            lines.append(f"  {i}. {step.description} {risk_tag}{auto_tag}")

        if self.risky_steps:
            lines.append(f"\n{self.risky_steps} action(s) require confirmation.")
        else:
            lines.append("\nAll actions are safe to auto-execute.")

        return "\n".join(lines)
