"""Tests for runtime.config.updater — local version check."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from runtime.config.updater import (
    check_for_update,
    get_current_version,
    get_current_channel,
    write_manifest,
    _parse_version,
    _MANIFEST_PATH,
)


def test_get_current_version():
    assert get_current_version() == "2.0.0"


def test_get_current_channel():
    assert get_current_channel() == "beta"


@pytest.mark.parametrize("ver,expected", [
    ("1.0.0", (1, 0, 0)),
    ("2.0.0", (2, 0, 0)),
    ("10.3.42", (10, 3, 42)),
    ("bad", ()),
])
def test_parse_version(ver, expected):
    assert _parse_version(ver) == expected


def test_check_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", tmp_path / "nope.json")
    info = check_for_update()
    assert not info.update_available
    assert "No version manifest" in info.notes


def test_check_same_version(tmp_path, monkeypatch):
    manifest = tmp_path / "version.json"
    manifest.write_text(json.dumps({"version": "2.0.0", "channel": "stable"}))
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", manifest)
    info = check_for_update()
    assert not info.update_available


def test_check_newer_available(tmp_path, monkeypatch):
    manifest = tmp_path / "version.json"
    manifest.write_text(json.dumps({"version": "2.1.0", "channel": "stable", "notes": "bugfix"}))
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", manifest)
    info = check_for_update()
    assert info.update_available
    assert info.latest == "2.1.0"
    assert info.notes == "bugfix"


def test_check_older_manifest(tmp_path, monkeypatch):
    manifest = tmp_path / "version.json"
    manifest.write_text(json.dumps({"version": "1.9.0", "channel": "stable"}))
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", manifest)
    info = check_for_update()
    assert not info.update_available


def test_write_manifest(tmp_path, monkeypatch):
    target = tmp_path / "sub" / "version.json"
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", target)
    path = write_manifest("3.0.0", channel="beta", notes="new")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["version"] == "3.0.0"
    assert data["channel"] == "beta"


def test_check_corrupt_manifest(tmp_path, monkeypatch):
    manifest = tmp_path / "version.json"
    manifest.write_text("NOT JSON")
    monkeypatch.setattr("runtime.config.updater._MANIFEST_PATH", manifest)
    info = check_for_update()
    assert not info.update_available
