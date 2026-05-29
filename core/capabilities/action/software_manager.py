"""
Action System: Software Manager

Install, update, and search software using Windows Package Manager (winget).
All operations are HIGH risk — always require user confirmation before execution.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from core.capabilities.result_reporter import ActionResult


@dataclass
class SoftwareAction:
    """Describes a software management operation."""
    operation: str          # "install" | "update" | "search" | "list"
    package_name: str
    confirmed: bool = False


def is_winget_available() -> bool:
    """Check if winget is installed and accessible."""
    try:
        result = subprocess.run(
            ["winget", "--version"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode == 0
    except Exception:
        return False


def search(query: str, max_results: int = 5) -> ActionResult:
    """Search for packages via winget."""
    try:
        result = subprocess.run(
            ["winget", "search", query, "--count", str(max_results)],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            return ActionResult(
                success=True,
                message=f"Search results for '{query}':\n{result.stdout.strip()}",
            )
        return ActionResult(
            success=False,
            message=f"No packages found for '{query}'.",
        )
    except subprocess.TimeoutExpired:
        return ActionResult(success=False, message="Search timed out.")
    except Exception as e:
        return ActionResult(success=False, message=f"Search failed: {e}")


def install(package_name: str) -> ActionResult:
    """
    Install a package via winget.
    HIGH RISK — caller must have already confirmed with user.
    """
    try:
        result = subprocess.run(
            ["winget", "install", package_name,
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            return ActionResult(
                success=True,
                message=f"Successfully installed '{package_name}'.",
            )
        return ActionResult(
            success=False,
            message=f"Install failed:\n{result.stderr or result.stdout}",
        )
    except subprocess.TimeoutExpired:
        return ActionResult(success=False, message="Install timed out (2 min limit).")
    except Exception as e:
        return ActionResult(success=False, message=f"Install error: {e}")


def update(package_name: str) -> ActionResult:
    """
    Update a package via winget.
    HIGH RISK — caller must have already confirmed with user.
    """
    try:
        result = subprocess.run(
            ["winget", "upgrade", package_name,
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            return ActionResult(
                success=True,
                message=f"Successfully updated '{package_name}'.",
            )
        return ActionResult(
            success=False,
            message=f"Update failed:\n{result.stderr or result.stdout}",
        )
    except subprocess.TimeoutExpired:
        return ActionResult(success=False, message="Update timed out (2 min limit).")
    except Exception as e:
        return ActionResult(success=False, message=f"Update error: {e}")


def execute(action: SoftwareAction) -> ActionResult:
    """Route a software management action."""
    if not is_winget_available():
        return ActionResult(
            success=False,
            message="winget is not available on this system.",
        )

    if action.operation == "search":
        return search(action.package_name)

    # Install/update require explicit confirmation
    if not action.confirmed:
        return ActionResult(
            success=False,
            message=(
                f"Software {action.operation} requires confirmation. "
                f"Please confirm: {action.operation} '{action.package_name}'?"
            ),
            data={"needs_confirmation": True, "action": action.operation,
                  "package": action.package_name},
        )

    if action.operation == "install":
        return install(action.package_name)

    if action.operation == "update":
        return update(action.package_name)

    return ActionResult(
        success=False,
        message=f"Unknown software operation: {action.operation}",
    )
