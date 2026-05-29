"""
Automation: Executor

Top-level runner: resolves a user request into a chain (via Planner or Macro),
executes it, and returns the result.
"""

from __future__ import annotations

from typing import Any

from MAIINNN.Functions.automation.chain import Chain, ChainResult
from MAIINNN.Functions.automation.planner import AutomationPlanner
from MAIINNN.Functions.automation.macro import MacroStore, Macro


class AutomationExecutor:
    """Orchestrates automation: macro lookup → planner → chain execution."""

    def __init__(
        self,
        planner: AutomationPlanner | None = None,
        macro_store: MacroStore | None = None,
    ):
        self._planner = planner or AutomationPlanner()
        self._macros = macro_store or MacroStore()
        # action_name → callable used when expanding macros
        self._action_registry: dict[str, Any] = {}
        # Set of app title substrings where typing is pre-approved
        self._typing_allowlist: set[str] = {
            "chrome", "firefox", "edge", "brave", "opera",
            "notepad", "code", "visual studio", "word",
            "excel", "terminal", "powershell", "cmd",
        }

    def register_action(self, name: str, fn: Any):
        """Register an action callable by name (used for macro expansion)."""
        self._action_registry[name] = fn

    # ── typing ───────────────────────────────────────────────

    def type_text(self, text: str, *, confirm: bool = True) -> str:
        """
        Type text into the currently focused application using pyautogui.
        Safety: Only proceeds if the focused window is in the allowlist,
        or if confirm=False (caller already got user approval).
        """
        try:
            import pygetwindow as gw
            import pyautogui
        except ImportError:
            return "Typing unavailable. Install: pip install pyautogui pygetwindow"

        active = gw.getActiveWindow()
        if active is None:
            return "No active window to type into."

        title_lower = active.title.lower()

        # Safety check: is this a known-safe window?
        if confirm:
            is_known = any(app in title_lower for app in self._typing_allowlist)
            if not is_known:
                return (
                    f"Typing into '{active.title}' is not pre-approved. "
                    f"Please confirm you want to type into this window."
                )

        pyautogui.write(text, interval=0.02)
        return f"Typed {len(text)} characters into '{active.title}'."

    # ── execute ──────────────────────────────────────────────

    def preview(self, user_request: str) -> str | None:
        """Return a human-readable plan preview, or None if nothing matched."""
        return self._planner.preview(user_request)

    def run(self, user_request: str, *, confirmed: bool = False) -> ChainResult | None:
        """
        Try macro first, then planner. Returns None if nothing matched.
        For multi-step plans, set confirmed=True to skip preview gate.
        """
        # Check if user_request is a macro name
        macro = self._macros.get(user_request.strip())
        if macro:
            return self._run_macro(macro)

        # Plan from NL
        chain = self._planner.plan(user_request)
        if chain:
            # Gate multi-step plans behind confirmation
            if chain.step_count > 1 and not confirmed:
                preview_text = self._planner.preview(user_request) or ""
                # Return a result with a preview step indicating confirmation needed
                from MAIINNN.Functions.automation.chain import ChainResult, StepResult
                result = ChainResult(chain_name="preview")
                result.steps.append(StepResult(
                    name="preview",
                    success=False,
                    output=preview_text or "Multi-step plan requires confirmation.",
                    error="confirmation_required",
                ))
                return result
            return chain.run()

        return None

    def _run_macro(self, macro: Macro) -> ChainResult:
        """Expand a macro into a chain and run it."""
        chain = Chain(name=f"macro_{macro.name}")
        for step_name in macro.steps:
            fn = self._action_registry.get(step_name)
            if fn:
                chain.add(step_name, fn)
            else:
                chain.add(step_name, lambda _prev, s=step_name: f"[unknown action: {s}]")
        return chain.run()

    # ── helpers ──────────────────────────────────────────────

    def capabilities(self) -> list[str]:
        caps = self._planner.list_capabilities()
        macros = [f"macro:{m}" for m in self._macros.list_macros()]
        return caps + macros
