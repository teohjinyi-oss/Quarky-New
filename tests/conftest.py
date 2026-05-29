"""
Quarky_Ai — Test Fixtures

Shared fixtures for temp data dirs, clean memory, mock config.
"""

import json
import shutil
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _clean_temp_memory(tmp_path, monkeypatch):
    """
    Redirect all data directories to tmp_path for test isolation.
    This prevents tests from polluting real user data.
    """
    import runtime.config.config as cfg

    test_data = tmp_path / "data"
    test_memory = test_data / "memory"
    test_actions = test_data / "actions"

    for d in (test_data, test_memory, test_actions):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cfg, "DATA_DIR", test_data)
    monkeypatch.setattr(cfg, "MEMORY_DIR", test_memory)
    monkeypatch.setattr(cfg, "ACTIONS_DIR", test_actions)
    monkeypatch.setattr(cfg, "DB_PATH", test_data / "quarky_test.db")

    # Update nested config dicts that reference paths
    monkeypatch.setitem(cfg.MEMORY, "temporary_file", test_memory / "temporary.json")
    monkeypatch.setitem(cfg.MEMORY, "flexible_file", test_memory / "flexible.json")
    monkeypatch.setitem(cfg.MEMORY, "priority_file", test_memory / "priority.json")
    monkeypatch.setitem(cfg.MEMORY, "permanent_db", test_data / "quarky_test.db")
    monkeypatch.setitem(cfg.ACTION, "log_file", test_actions / "action_log.json")

    # Reset permanent store DB init flag so each test creates a fresh table
    try:
        from core.memory.permanent import store as perm_store
        perm_store._DB_INITIALIZED = False
    except Exception:
        pass
