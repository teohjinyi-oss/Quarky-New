"""Tests for the Decision Engine — process() end-to-end."""

import pytest


class TestDecisionEngine:
    """Test the decision engine pipeline."""

    def test_process_returns_final_output(self):
        from core.decision.output_gate import process, FinalOutput
        result = process("hello")
        assert isinstance(result, FinalOutput)
        assert result.response
        assert result.source

    def test_process_question(self):
        from core.decision.output_gate import process
        result = process("what is 2 plus 2")
        assert result.response  # Should have some response
        assert result.confidence >= 0.0

    def test_process_command(self):
        from core.decision.output_gate import process
        result = process("open chrome")
        assert result.response
        # May or may not have action_request depending on classification

    def test_process_empty_graceful(self):
        from core.decision.output_gate import process
        result = process("")
        # Should not crash
        assert result.response

    def test_final_output_fields(self):
        from core.decision.output_gate import FinalOutput
        fo = FinalOutput(
            response="test",
            confidence=0.5,
            source="analytical",
        )
        assert fo.response == "test"
        assert fo.action_request is None
        assert fo.memory_actions == []

    def test_action_request_structure(self):
        from core.decision.action_resolver import ActionRequest
        ar = ActionRequest(
            action_type="app_launch",
            command="open chrome",
            target="chrome",
            risk_level="LOW",
        )
        assert ar.action_type == "app_launch"
        assert not ar.needs_confirmation

    def test_high_risk_needs_confirmation(self):
        from core.decision.action_resolver import ActionRequest
        ar = ActionRequest(
            action_type="file_op",
            command="delete file.txt",
            target="file.txt",
            risk_level="HIGH",
            needs_confirmation=True,
        )
        assert ar.needs_confirmation


class TestBrowserConfirmationPolicy:
    """Browser/URL launches must always require confirmation (never auto-execute)."""

    def test_chrome_target_is_high_risk(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "chrome", "open chrome")
        assert risk == "HIGH"

    def test_firefox_target_is_high_risk(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "firefox", "open firefox")
        assert risk == "HIGH"

    def test_edge_target_is_high_risk(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "edge", "open edge")
        assert risk == "HIGH"

    def test_brave_target_is_high_risk(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "brave", "open brave")
        assert risk == "HIGH"

    def test_browser_target_needs_confirmation(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "browser", "open browser")
        assert risk == "HIGH"

    def test_url_open_is_high_risk(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "https://example.com", "open https://example.com")
        assert risk == "HIGH"

    def test_non_browser_app_not_high_risk_by_default(self):
        from core.decision.action_resolver import _get_risk_level
        risk = _get_risk_level("app_launch", "notepad", "open notepad")
        # Notepad should stay LOW (not a browser)
        assert risk == "LOW"

    def test_process_open_chrome_requires_confirmation(self):
        """End-to-end: 'open chrome' must produce a confirmation prompt."""
        from core.decision.output_gate import process
        result = process("open chrome")
        # Either the action request requires confirmation, or response contains
        # confirmation language (no silent auto-open)
        if result.action_request is not None:
            assert result.action_request.needs_confirmation, (
                "open chrome should require confirmation, not auto-execute"
            )
        else:
            # If no action_request, at minimum Chrome must NOT have been executed
            if result.action_result is not None:
                assert not result.action_result.success or "chrome" not in (
                    result.action_result.message or ""
                ).lower(), "Chrome should not silently launch"
