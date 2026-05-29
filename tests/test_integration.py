"""
Integration Tests — End-to-end pipeline verification.

Tests the full flow: NLP → Brain → Decision → Action → Output
across multiple input types and edge cases.
"""

import pytest
import time


class TestFullPipeline:
    """End-to-end: text input → NLP → Brain → Decision → output."""

    def test_greeting_flow(self):
        from core.decision.output_gate import process
        result = process("hello")
        assert result.response
        assert isinstance(result.response, str)
        assert result.source in ("analytical", "creative", "merged", "fallback")

    def test_question_flow(self):
        from core.decision.output_gate import process
        result = process("what is the capital of france")
        assert result.response
        assert result.confidence >= 0.0

    def test_math_flow(self):
        from core.decision.output_gate import process
        result = process("what is 5 plus 3")
        assert result.response

    def test_command_flow(self):
        from core.decision.output_gate import process
        result = process("open chrome")
        assert result.response

    def test_farewell_flow(self):
        from core.decision.output_gate import process
        result = process("goodbye")
        assert result.response

    def test_nonsense_input(self):
        from core.decision.output_gate import process
        result = process("asdfghjkl qwerty")
        assert result.response  # Should still produce a response

    def test_long_input(self):
        from core.decision.output_gate import process
        long_text = "hello " * 200
        result = process(long_text)
        assert result.response


class TestNLPToBrain:
    """Test NLP classification feeds correctly into brain processing."""

    def test_classifier_to_spinal(self):
        from core.nlp.classifier import classify
        from core.routing.forwarder import think
        classification = classify("what is python")
        assert classification.intent
        result = think("what is python")
        assert result is not None
        assert result.analytical is not None or result.creative is not None

    def test_cleaner_preserves_meaning(self):
        from core.nlp.cleaner import clean
        from core.decision.output_gate import process
        cleaned = clean("  What IS the weather TODAY?  ")
        result = process(cleaned)
        assert result.response


class TestMemoryIntegration:
    """Test that memory is properly read/written during processing."""

    def test_temporary_memory_stores(self):
        from core.memory.manager import store_temporary, recall
        store_temporary("integration test data", source="test")
        results = recall(["integration", "test"])
        assert results is not None

    def test_memory_recall_across_layers(self):
        from core.memory.manager import store_temporary, recall
        store_temporary("unique_test_marker_xyz", source="test")
        results = recall(["unique_test_marker_xyz"])
        assert results is not None

    def test_permanent_memory_roundtrip(self):
        from core.memory.manager import store_permanent, recall
        store_permanent("integration roundtrip value", tags=["integration_key"])
        results = recall(["integration_key"])
        assert results is not None


class TestSessionIntegration:
    """Test session tracking integrates with the pipeline."""

    def test_session_records_turn(self):
        from core.session.session import get_session
        from core.decision.output_gate import process
        session = get_session()
        initial = session.turn_count
        result = process("hello for session test")
        # Manually add turn (CLI does this, not process() directly)
        session.add_turn(
            user_text="hello for session test",
            response=result.response,
            source=result.source,
            confidence=result.confidence,
        )
        assert session.turn_count == initial + 1

    def test_session_history(self):
        from core.session.session import get_session
        session = get_session()
        session.add_turn("test q", "test a", "analytical", confidence=0.8)
        history = session.get_history(count=5)
        assert len(history) > 0
        assert history[-1].user_text == "test q"

    def test_duplicate_detection(self):
        from core.session.session import get_session
        session = get_session()
        session.add_turn("duplicate check", "response", "analytical")
        dup = session.check_duplicate("duplicate check")
        assert dup is not None


class TestActionIntegration:
    """Test the action system integrates with the decision pipeline."""

    def test_action_registry_loaded(self):
        from core.capabilities.action.registry import ensure_builtins, list_registered
        ensure_builtins()
        registered = list_registered()
        assert len(registered) > 0

    def test_safety_check_works(self):
        from core.capabilities.action.safety import check_safety
        verdict = check_safety("app_launch", "chrome", "LOW")
        assert verdict.allowed

    def test_action_logger_records(self):
        from core.capabilities.action.action_logger import log_action, get_recent
        log_action(
            action_type="test_action",
            target="test_target",
            risk_level="LOW",
            success=True,
            message="integration test",
        )
        recent = get_recent(5)
        assert len(recent) > 0
        assert any(r.get("action_type") == "test_action" for r in recent)


class TestVoiceBridge:
    """Test the voice-to-text bridge (no actual audio)."""

    def test_bridge_handles_text(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input("hello from voice")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_bridge_handles_empty(self):
        from interfaces.voice.start.text_bridge import handle_voice_input
        result = handle_voice_input("")
        assert "didn't catch" in result.lower()

    def test_bridge_command_structured(self):
        from interfaces.voice.start.text_bridge import handle_voice_command
        result = handle_voice_command("what is the time")
        assert "response" in result
        assert "success" in result


class TestInfrastructureIntegration:
    """Test infrastructure systems work together."""

    def test_gateway_message_roundtrip(self):
        from runtime.gateway.gateway import GatewayMessage
        msg = GatewayMessage(
            source="core",
            target="infrastructure",
            payload={"text": "test"},
        )
        d = msg.to_dict()
        assert d["source"] == "core"
        assert d["target"] == "infrastructure"

    def test_permissions_matrix(self):
        from runtime.permissions.permissions import is_allowed
        assert is_allowed("core", "infrastructure")
        assert is_allowed("decision", "action")
        # Action cannot touch memory directly
        assert not is_allowed("action", "memory")

    def test_transport_manager_routes(self):
        from runtime.transports.manager import decide_mode
        decision = decide_mode(payload={"text": "test"}, urgent=True, payload_size=100)
        assert decision is not None


class TestPerformance:
    """Basic performance sanity checks."""

    def test_process_latency(self):
        """Single process() call should complete within 2 seconds."""
        from core.decision.output_gate import process
        start = time.time()
        process("quick test")
        elapsed = time.time() - start
        assert elapsed < 2.0, f"process() took {elapsed:.2f}s"

    def test_nlp_classify_latency(self):
        """NLP classification should be fast."""
        from core.nlp.classifier import classify
        start = time.time()
        for _ in range(100):
            classify("what is the weather today")
        elapsed = time.time() - start
        assert elapsed < 1.0, f"100 classifications took {elapsed:.2f}s"

    def test_memory_store_latency(self):
        """Memory store should be fast."""
        from core.memory.manager import store_temporary
        start = time.time()
        for i in range(50):
            store_temporary(f"perf test {i}", source="test")
        elapsed = time.time() - start
        assert elapsed < 2.0, f"50 stores took {elapsed:.2f}s"
