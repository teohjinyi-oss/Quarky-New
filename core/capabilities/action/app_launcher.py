"""
Action System: App Launcher

Opens applications and URLs using subprocess and webbrowser.
Uses app_discovery for name resolution and fuzzy matching.
"""

import subprocess
import webbrowser
import time
import re
from typing import Any

from core.decision.action_resolver import ActionRequest
from core.capabilities.result_reporter import ActionResult
from core.capabilities.action.app_discovery import find_app, fuzzy_find, refresh, app_count


def launch(action_request: ActionRequest) -> ActionResult:
    """
    Main handler for app_launch actions.
    Tries to open the target as an app or URL.
    """
    target = action_request.target.strip()

    if not target:
        return ActionResult(success=False, message="No target specified to launch.")

    # Check if it's a URL
    if _is_url(target):
        return _open_url(target)

    # Try to find the app
    return _open_app(target)


def _is_url(text: str) -> bool:
    """Check if text looks like a URL."""
    return bool(re.match(r'https?://|www\.', text, re.IGNORECASE))


def _open_url(url: str) -> ActionResult:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        webbrowser.open(url)
        return ActionResult(
            success=True,
            message=f"Opened URL: {url}",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Failed to open URL: {e}")


def _open_app(target: str) -> ActionResult:
    """Open an application by name."""
    # Ensure registry is populated
    if app_count() == 0:
        refresh()

    # 1. Try exact/alias match
    app_info = find_app(target)
    if app_info:
        return _launch_path(app_info["name"], app_info["path"])

    # 2. Try fuzzy match
    fuzzy_results = fuzzy_find(target, cutoff=0.4, max_results=3)
    if fuzzy_results:
        best = fuzzy_results[0]
        if best["score"] >= 0.7:
            # High confidence — launch directly
            return _launch_path(best["name"], best["path"])
        else:
            # Low confidence — suggest
            suggestions = ", ".join(r["name"] for r in fuzzy_results)
            return ActionResult(
                success=False,
                message=f"Could not find '{target}'. Did you mean: {suggestions}?",
                data={"suggestions": fuzzy_results},
            )

    # 3. Last resort: try launching directly via shell
    return _launch_direct(target)


def _launch_path(name: str, path: str) -> ActionResult:
    """Launch an app from its known path."""
    try:
        if path.startswith("shell:AppsFolder\\"):
            # UWP / Windows Store app — launch via explorer
            subprocess.Popen(
                ["explorer.exe", path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif path.endswith(".lnk"):
            # Windows shortcut — use os.startfile equivalent
            subprocess.Popen(
                ["cmd", "/c", "start", "", path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return ActionResult(
            success=True,
            message=f"Opened {name}.",
        )
    except FileNotFoundError:
        return ActionResult(
            success=False,
            message=f"Could not find executable for '{name}' at '{path}'.")
    except PermissionError:
        return ActionResult(
            success=False,
            message=f"Permission denied when launching '{name}'.")
    except Exception as e:
        return ActionResult(success=False, message=f"Failed to launch '{name}': {e}")


def _launch_direct(target: str) -> ActionResult:
    """Try launching target directly as a command name."""
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", target],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return ActionResult(
            success=True,
            message=f"Attempted to open '{target}'.",
        )
    except Exception as e:
        return ActionResult(
            success=False,
            message=f"Could not open '{target}'. Application not found.",
            data={"error": str(e)},
        )
