"""
Automation: Macro

User-defined macros — named shortcuts that expand to chains.
Persisted to disk so they survive restarts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from AppStudio.Config import CONFIG


@dataclass
class Macro:
    """A saved user macro."""
    name: str
    steps: list[str]        # ordered action names
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "steps": self.steps, "description": self.description}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Macro:
        return cls(name=d["name"], steps=d.get("steps", []), description=d.get("description", ""))


class MacroStore:
    """Manages user macros."""

    def __init__(self):
        auto_cfg = CONFIG.get("AUTOMATION", {})
        self._path = os.path.join(
            auto_cfg.get("dir", "data/automation"),
            "macros.json"
        )
        self._macros: dict[str, Macro] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for d in items:
                    m = Macro.from_dict(d)
                    self._macros[m.name] = m
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._macros.values()], f)

    # ── CRUD ─────────────────────────────────────────────────

    def save(self, macro: Macro):
        self._macros[macro.name] = macro
        self._save()

    def get(self, name: str) -> Macro | None:
        return self._macros.get(name)

    def delete(self, name: str):
        self._macros.pop(name, None)
        self._save()

    def list_macros(self) -> list[str]:
        return list(self._macros.keys())

    def all(self) -> list[Macro]:
        return list(self._macros.values())
