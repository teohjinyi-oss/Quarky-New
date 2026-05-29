"""
Action System: App Discovery

Scans the Windows Start Menu and PATH for installed applications.
Builds a searchable registry with fuzzy matching and alias support.
Loads user-custom apps from data/actions/custom_apps.json.
"""

import os
import re
import difflib
import json
import threading
from pathlib import Path
from typing import Any

from runtime.config.config import ACTIONS_DIR


_CUSTOM_APPS_FILE = ACTIONS_DIR / "custom_apps.json"
_lock = threading.Lock()

# name_lower → {"name": display_name, "path": exe_path, "source": "scan"|"custom"|"alias"}
_app_registry: dict[str, dict[str, str]] = {}

# Built-in aliases: alias → canonical name
_ALIASES: dict[str, str] = {
    "browser": "chrome",
    "google": "chrome",
    "chrome": "google chrome",
    "firefox": "mozilla firefox",
    "code": "visual studio code",
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "telegram": "telegram",
    "word": "microsoft word",
    "excel": "microsoft excel",
    "powerpoint": "microsoft powerpoint",
    "paint": "paint",
    "calc": "calculator",
    "calculator": "calculator",
    "terminal": "windows terminal",
    "cmd": "command prompt",
    "powershell": "windows powershell",
    "explorer": "file explorer",
    "files": "file explorer",
    "steam": "steam",
    "obs": "obs studio",
    "vlc": "vlc media player",
    "zoom": "zoom",
    "teams": "microsoft teams",
    "edge": "microsoft edge",
    "brave": "brave",
    "opera": "opera",
    "git": "git",
    "blender": "blender",
    "photoshop": "adobe photoshop",
    "illustrator": "adobe illustrator",
}


def scan_start_menu() -> dict[str, str]:
    """
    Scan Windows Start Menu folders for .lnk shortcut files.
    Returns {display_name: shortcut_path}.
    """
    apps: dict[str, str] = {}
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
    ]

    for start_dir in start_dirs:
        if not start_dir.exists():
            continue
        try:
            for lnk in start_dir.rglob("*.lnk"):
                name = lnk.stem
                # Skip uninstallers and updaters
                lower = name.lower()
                if any(skip in lower for skip in ("uninstall", "update", "readme", "help", "license")):
                    continue
                apps[name] = str(lnk)
        except (PermissionError, OSError):
            continue

    return apps


def scan_path() -> dict[str, str]:
    """
    Scan system PATH for common executables.
    Returns {display_name: exe_path}.
    """
    apps: dict[str, str] = {}
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    # Only scan the most relevant directories
    for dir_path in path_dirs:
        p = Path(dir_path)
        try:
            if not p.exists() or not p.is_dir():
                continue
        except (PermissionError, OSError):
            continue
        try:
            for f in p.iterdir():
                if f.suffix.lower() in (".exe", ".cmd", ".bat") and f.is_file():
                    name = f.stem
                    if len(name) > 2 and not name.startswith("_"):
                        apps[name] = str(f)
        except (PermissionError, OSError):
            continue

    return apps


def scan_uwp_apps() -> dict[str, str]:
    """
    Discover Windows Store / UWP apps via PowerShell Get-StartApps.
    Returns {display_name: "shell:AppsFolder\\AppUserModelId"}.
    Falls back to empty dict if PowerShell is unavailable.
    """
    apps: dict[str, str] = {}
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return apps
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        for entry in data:
            name = entry.get("Name", "")
            app_id = entry.get("AppID", "")
            if name and app_id:
                lower = name.lower()
                if any(skip in lower for skip in ("uninstall", "update")):
                    continue
                apps[name] = f"shell:AppsFolder\\{app_id}"
    except Exception:
        pass
    return apps


def _load_custom_apps() -> dict[str, str]:
    """Load user-defined custom apps from JSON."""
    if not _CUSTOM_APPS_FILE.exists():
        _CUSTOM_APPS_FILE.write_text("{}", encoding="utf-8")
        return {}
    try:
        data = json.loads(_CUSTOM_APPS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_custom_apps(apps: dict[str, str]) -> None:
    _CUSTOM_APPS_FILE.write_text(
        json.dumps(apps, indent=2), encoding="utf-8")


def add_custom_app(name: str, path: str) -> bool:
    """Register a custom app by name and executable path."""
    with _lock:
        custom = _load_custom_apps()
        custom[name] = path
        _save_custom_apps(custom)
        _app_registry[name.lower()] = {
            "name": name, "path": path, "source": "custom"}
    return True


def remove_custom_app(name: str) -> bool:
    """Remove a custom app."""
    with _lock:
        custom = _load_custom_apps()
        if name in custom:
            custom.pop(name)
            _save_custom_apps(custom)
            _app_registry.pop(name.lower(), None)
            return True
    return False


def refresh() -> int:
    """
    Re-scan all sources and rebuild the registry.
    Returns the number of apps discovered.
    """
    with _lock:
        _app_registry.clear()

        # Scan Start Menu
        for name, path in scan_start_menu().items():
            _app_registry[name.lower()] = {
                "name": name, "path": path, "source": "scan"}

        # Scan PATH
        for name, path in scan_path().items():
            key = name.lower()
            if key not in _app_registry:
                _app_registry[key] = {
                    "name": name, "path": path, "source": "scan"}

        # Scan UWP / Windows Store apps
        for name, app_uri in scan_uwp_apps().items():
            key = name.lower()
            if key not in _app_registry:
                _app_registry[key] = {
                    "name": name, "path": app_uri, "source": "uwp"}

        # Load custom apps (override scanned)
        for name, path in _load_custom_apps().items():
            _app_registry[name.lower()] = {
                "name": name, "path": path, "source": "custom"}

        return len(_app_registry)


def find_app(query: str) -> dict[str, str] | None:
    """
    Find an app by exact name or alias.
    Returns {"name", "path", "source"} or None.
    """
    q = query.lower().strip()

    # Direct match
    if q in _app_registry:
        return _app_registry[q]

    # Alias match
    canonical = _ALIASES.get(q)
    if canonical and canonical.lower() in _app_registry:
        return _app_registry[canonical.lower()]

    # Partial match: check if query is contained in any app name
    for key, info in _app_registry.items():
        if q in key or key in q:
            return info

    return None


def fuzzy_find(query: str, cutoff: float = 0.5,
               max_results: int = 5) -> list[dict[str, Any]]:
    """
    Fuzzy search for apps. Returns list of {name, path, source, score}.
    """
    q = query.lower().strip()
    all_names = list(_app_registry.keys())

    # Try exact/alias first
    exact = find_app(q)
    if exact:
        return [{"name": exact["name"], "path": exact["path"],
                 "source": exact["source"], "score": 1.0}]

    # Fuzzy match
    matches = difflib.get_close_matches(q, all_names, n=max_results, cutoff=cutoff)

    results = []
    for match_name in matches:
        info = _app_registry[match_name]
        score = difflib.SequenceMatcher(None, q, match_name).ratio()
        results.append({
            "name": info["name"],
            "path": info["path"],
            "source": info["source"],
            "score": round(score, 3),
        })

    return results


def list_apps(source: str | None = None) -> list[dict[str, str]]:
    """List all registered apps, optionally filtered by source."""
    with _lock:
        if source:
            return [info for info in _app_registry.values()
                    if info["source"] == source]
        return list(_app_registry.values())


def app_count() -> int:
    """Return the number of registered apps."""
    return len(_app_registry)
