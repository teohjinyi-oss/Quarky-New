"""
Automation: Planner

Converts a user's natural-language request into a series of
automation steps (a Chain) by matching against known action templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from MAIINNN.Functions.automation.chain import Chain


@dataclass
class ActionTemplate:
    """A known automatable action."""
    name: str
    keywords: list[str]
    builder: Callable[..., Any]  # returns a step function
    description: str = ""


class AutomationPlanner:
    """Maps user requests to Chain objects."""

    def __init__(self):
        self._templates: list[ActionTemplate] = []

    def register(self, template: ActionTemplate):
        self._templates.append(template)

    def plan(self, user_request: str) -> Chain | None:
        """Build a chain from a user request, or None if nothing matches."""
        request_lower = user_request.lower()
        matched: list[ActionTemplate] = []
        for tpl in self._templates:
            if any(kw in request_lower for kw in tpl.keywords):
                matched.append(tpl)

        if not matched:
            return None

        chain = Chain(name=f"auto_{len(matched)}_steps")
        for tpl in matched:
            step_fn = tpl.builder(user_request)
            chain.add(tpl.name, step_fn)
        return chain

    def preview(self, user_request: str) -> str | None:
        """
        Return a human-readable numbered plan for the user to review
        before execution. Returns None if no steps match.
        """
        request_lower = user_request.lower()
        matched: list[ActionTemplate] = []
        for tpl in self._templates:
            if any(kw in request_lower for kw in tpl.keywords):
                matched.append(tpl)

        if not matched:
            return None

        lines = [f"Plan for: \"{user_request}\"", ""]
        for i, tpl in enumerate(matched, 1):
            desc = tpl.description or tpl.name
            lines.append(f"  {i}. {desc}")
        lines.append("")
        lines.append("Confirm to execute, or cancel.")
        return "\n".join(lines)

    def list_capabilities(self) -> list[str]:
        return [f"{t.name}: {t.description}" for t in self._templates]
