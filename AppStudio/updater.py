"""
Quarky_Ai — Local Version & Update Checker

Compares the running version against a local manifest file
(data/version.json). No cloud dependency — the manifest is
updated by the build pipeline or manual drop.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from AppStudio.Config import VERSION, CHANNEL, DATA_DIR

log = logging.getLogger(__name__)

_MANIFEST_PATH = DATA_DIR / "version.json"


@dataclass
class UpdateInfo:
    current: str
    latest: str
    channel: str
    update_available: bool
    notes: str = ""


def get_current_version() -> str:
    """Return the running application version."""
    return VERSION


def get_current_channel() -> str:
    """Return the running release channel."""
    return CHANNEL


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    parts: list[int] = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts)


def _read_manifest() -> Optional[dict]:
    """Read the local version manifest if it exists."""
    if not _MANIFEST_PATH.exists():
        return None
    try:
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict) or "version" not in data:
            log.warning("Invalid version manifest: missing 'version' key")
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to read version manifest: %s", exc)
        return None


def write_manifest(version: str, channel: str = "stable", notes: str = "") -> Path:
    """Write a version manifest (called by build pipeline)."""
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": version, "channel": channel, "notes": notes}
    _MANIFEST_PATH.write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    log.info("Wrote version manifest %s → %s", version, _MANIFEST_PATH)
    return _MANIFEST_PATH


def check_for_update() -> UpdateInfo:
    """
    Compare running version against the local manifest.

    Returns an UpdateInfo with update_available=True when the
    manifest version is strictly newer than the running version.
    """
    manifest = _read_manifest()
    if manifest is None:
        return UpdateInfo(
            current=VERSION,
            latest=VERSION,
            channel=CHANNEL,
            update_available=False,
            notes="No version manifest found.",
        )

    latest = manifest.get("version", VERSION)
    notes = manifest.get("notes", "")
    manifest_channel = manifest.get("channel", "stable")

    current_tuple = _parse_version(VERSION)
    latest_tuple = _parse_version(latest)

    return UpdateInfo(
        current=VERSION,
        latest=latest,
        channel=manifest_channel,
        update_available=latest_tuple > current_tuple,
        notes=notes,
    )
