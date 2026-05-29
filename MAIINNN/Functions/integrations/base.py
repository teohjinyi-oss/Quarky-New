"""
Integrations: Base ABC

All integration providers implement this interface so the orchestrator
can discover capabilities and dispatch uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IntegrationBase(ABC):
    """Abstract base for all integration providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short human-readable provider name (e.g. 'google', 'microsoft')."""

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """List of supported actions (e.g. ['email', 'calendar'])."""

    @abstractmethod
    def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Execute an integration action.

        Parameters
        ----------
        action : str
            One of the values from ``capabilities`` (e.g. 'check_email').
        **kwargs
            Action-specific parameters.

        Returns
        -------
        Any
            Action result — typically a list of items or a status dict.
        """

    @property
    def available(self) -> bool:
        """Whether this provider is currently connected and usable."""
        return True
