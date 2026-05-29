"""Tests for the Action System — registry, safety, executors, undo."""

import pytest
from pathlib import Path


class TestActionResultReporter:
    """Test action result dataclasses."""

    def test_action_result(self):
        from core.capabilities.result_reporter import ActionResult
        r = ActionResult(success=True, message="Done")
        assert r.success
        assert r.message == "Done"
        assert r.undo_info is None

    def test_undo_info(self):
        from core.capabilities.result_reporter import UndoInfo
        u = UndoInfo(undo_type="file_restore", description="Restore test.txt")
        assert u.undo_type == "file_restore"

    def test_action_plan(self):
        from core.capabilities.result_reporter import ActionPlan, ActionStep
        plan = ActionPlan(steps=[
            ActionStep(action_type="app_launch", target="chrome", risk_level="LOW", description="Open Chrome"),
            ActionStep(action_type="file_op", target="notes.txt", risk_level="MEDIUM", description="Create notes.txt"),
        ])
        preview = plan.format_preview()
        assert "chrome" in preview.lower() or "app_launch" in preview.lower()


class TestActionRegistry:
    """Test the action registry."""

    def test_ensure_builtins(self):
        from core.capabilities.action.registry import ensure_builtins, list_registered
        ensure_builtins()
        registered = list_registered()
        assert len(registered) > 0

    def test_get_handler(self):
        from core.capabilities.action.registry import ensure_builtins, get_handler
        ensure_builtins()
        handler = get_handler("app_launch")
        assert handler is not None
        assert callable(handler)

    def test_unknown_handler(self):
        from core.capabilities.action.registry import get_handler
        handler = get_handler("nonexistent_action_xyz")
        assert handler is None


class TestActionSafety:
    """Test the safety gate."""

    def test_low_risk_auto_allowed(self):
        from core.capabilities.action.safety import check_safety
        verdict = check_safety("app_launch", "chrome", "LOW")
        assert verdict.allowed

    def test_system_path_blocked(self):
        from core.capabilities.action.safety import is_system_path
        assert is_system_path("C:\\Windows\\System32\\cmd.exe")
        assert not is_system_path("C:\\Users\\test\\document.txt")

    def test_critical_needs_confirmation(self):
        from core.capabilities.action.safety import check_safety
        verdict = check_safety("system_control", "shutdown", "CRITICAL")
        assert verdict.needs_user_input


class TestActionLogger:
    """Test the action logger."""

    def test_log_and_retrieve(self, tmp_path, monkeypatch):
        import runtime.config.config as cfg
        monkeypatch.setitem(cfg.ACTION, "log_file", tmp_path / "test_log.json")

        from core.capabilities.action import action_logger
        # Force reload of the log file path
        monkeypatch.setattr(action_logger, "_LOG_FILE", tmp_path / "test_log.json")

        action_logger.log_action("test", "target", "LOW", True, "ok", 10.0)
        entries = action_logger.get_recent(5)
        assert len(entries) >= 1
        assert entries[-1]["action_type"] == "test"

    def test_get_stats_empty(self, tmp_path, monkeypatch):
        from core.capabilities.action import action_logger
        monkeypatch.setattr(action_logger, "_LOG_FILE", tmp_path / "empty_log.json")

        stats = action_logger.get_stats()
        assert stats["total_actions"] == 0


class TestCodeRunner:
    """Test the sandboxed code runner."""

    def test_simple_expression(self):
        from core.capabilities.action.code_runner import execute
        from core.decision.action_resolver import ActionRequest

        req = ActionRequest(
            action_type="code_run",
            command="run 2 + 2",
            target="2 + 2",
            risk_level="HIGH",
        )
        result = execute(req)
        assert result.success
        assert "4" in result.message

    def test_blocked_import(self):
        from core.capabilities.action.code_runner import execute
        from core.decision.action_resolver import ActionRequest

        req = ActionRequest(
            action_type="code_run",
            command="run import os",
            target="import os",
            risk_level="HIGH",
        )
        result = execute(req)
        assert not result.success

    def test_math_operations(self):
        from core.capabilities.action.code_runner import execute
        from core.decision.action_resolver import ActionRequest

        req = ActionRequest(
            action_type="code_run",
            command="run math.sqrt(16)",
            target="math.sqrt(16)",
            risk_level="HIGH",
        )
        result = execute(req)
        assert result.success
        assert "4" in result.message


class TestUndoManager:
    """Test the undo manager."""

    def test_empty_undo(self):
        from core.capabilities.action.undo_manager import undo_last
        result = undo_last()
        assert not result.success
        assert "nothing" in result.message.lower()

    def test_record_and_count(self):
        from core.capabilities.action.undo_manager import record, undo_count, clear
        from core.capabilities.result_reporter import UndoInfo

        clear()
        record("test_action", UndoInfo(
            undo_type="test",
            description="test undo",
        ))
        assert undo_count() >= 1
        clear()
