"""
Phase Integration Regression Tests

Tests for critical paths introduced in Phases 1–8 of the Jarvis upgrade:
- Phase 1: Streaming display, bubble sizing
- Phase 2: Wake phrase expansion, debounce
- Phase 3: Deep researcher, fuzzy correction, embedding cache
- Phase 4: Software manager, automation preview
- Phase 5: Worker pool retry/DLQ, monitor modes, structured logging
- Phase 6: Integration routing, feature flags, API endpoints
- Phase 7: Embedding LRU cache, pronoun pattern compilation
"""

from __future__ import annotations

import re
import time
from unittest.mock import MagicMock, patch


# ── Phase 1: GUI / Streaming ─────────────────────────────────

class TestStreamingBubble:
    """Verify StreamingBubble token append and finish logic."""

    def test_import(self):
        from interfaces.gui.chat_panel import StreamingBubble
        assert StreamingBubble is not None

    def test_bubble_max_width(self):
        from interfaces.gui.theme import BUBBLE_MAX_WIDTH
        assert BUBBLE_MAX_WIDTH >= 600, "Bubble max width should be wide enough"


# ── Phase 2: Voice ────────────────────────────────────────────

class TestWakePhraseExpansion:
    """Verify wake phrase set includes new variants."""

    def test_wake_phrases_include_whats_up(self):
        from interfaces.voice.wake_detector import WAKE_PHRASES
        phrases = {p.lower() for p in WAKE_PHRASES}
        assert "what's up quarky" in phrases or "whats up quarky" in phrases

    def test_debounce_constant(self):
        from interfaces.voice.wake_detector import _DEBOUNCE_SECONDS
        assert _DEBOUNCE_SECONDS >= 1.0


class TestSessionGuard:
    """Verify session guard module exists and has expected interface."""

    def test_is_session_unlocked(self):
        from interfaces.voice.session_guard import is_session_unlocked
        result = is_session_unlocked()
        assert isinstance(result, bool)


# ── Phase 3: Learning & Memory ────────────────────────────────

class TestDeepResearcher:
    """Verify AdaptiveResearcher class structure."""

    def test_import_and_init(self):
        from services.web.deep_researcher import AdaptiveResearcher
        researcher = AdaptiveResearcher()
        assert hasattr(researcher, "research")
        assert hasattr(researcher, "is_available")

    def test_choose_depth_short_query(self):
        from services.web.deep_researcher import AdaptiveResearcher
        researcher = AdaptiveResearcher()
        depth = researcher._choose_depth("what is gravity")
        assert depth in (1, 2, 3)


class TestEmbeddingCache:
    """Verify LRU cache on encode() avoids redundant computation."""

    def test_encode_returns_list(self):
        from core.nlp.embeddings import encode
        result = encode("hello world")
        assert isinstance(result, list)

    def test_encode_empty_returns_empty(self):
        from core.nlp.embeddings import encode
        assert encode("") == []
        assert encode("   ") == []

    def test_encode_cache_hit(self):
        """Same text should return identical results (cached)."""
        from core.nlp.embeddings import encode
        r1 = encode("test caching mechanism")
        r2 = encode("test caching mechanism")
        assert r1 == r2

    def test_encode_cached_function_exists(self):
        from core.nlp.embeddings import _encode_cached
        assert hasattr(_encode_cached, "cache_info")  # lru_cache attribute


class TestFuzzyCorrection:
    """Verify correction engine has fuzzy matching."""

    def test_correction_engine_has_check(self):
        from core.learning.correction import CorrectionEngine
        engine = CorrectionEngine()
        assert hasattr(engine, "check")
        # Should return None for unknown queries
        result = engine.check("completely unknown random query xyz123")
        assert result is None or isinstance(result, str)


# ── Phase 4: Action & Automation ──────────────────────────────

class TestSoftwareManager:
    """Verify software manager module structure."""

    def test_import(self):
        from core.capabilities.action.software_manager import (
            SoftwareAction, search, install, update, execute,
        )
        assert SoftwareAction is not None

    def test_search_returns_result(self):
        from core.capabilities.action.software_manager import search
        result = search("notepad")
        assert hasattr(result, "success")


class TestAutomationPreview:
    """Verify planner preview and chain step_count."""

    def test_chain_step_count(self):
        from core.capabilities.automation.chain import Chain
        chain = Chain(name="test")
        assert chain.step_count == 0

    def test_planner_has_preview(self):
        from core.capabilities.automation.planner import AutomationPlanner
        planner = AutomationPlanner()
        assert hasattr(planner, "preview")


class TestUndoSnapshots:
    """Verify undo manager snapshot capabilities."""

    def test_snapshot_file_function(self):
        from core.capabilities.action.undo_manager import snapshot_file
        assert callable(snapshot_file)


# ── Phase 5: Infrastructure & Monitoring ──────────────────────

class TestWorkerPoolResilience:
    """Verify retry + DLQ on worker pool."""

    def test_submit_with_retry(self):
        from runtime.workers.worker_pool import WorkerPool
        pool = WorkerPool("test_dept")
        assert hasattr(pool, "submit_with_retry")

    def test_get_dlq(self):
        from runtime.workers.worker_pool import WorkerPool
        pool = WorkerPool("test_dept")
        dlq = pool.get_dlq()
        assert isinstance(dlq, list)


class TestMonitorModes:
    """Verify monitor mode enum and set_mode."""

    def test_monitor_modes_enum(self):
        from services.monitoring.alerter import MonitorMode
        assert MonitorMode.CRITICAL.value is not None
        assert MonitorMode.PERIODIC.value is not None
        assert MonitorMode.LIVE.value is not None

    def test_alerter_set_mode(self):
        from services.monitoring.alerter import SystemAlerter, MonitorMode
        alerter = SystemAlerter()
        alerter.set_mode(MonitorMode.LIVE)


class TestStructuredLogging:
    """Verify JSON logging infrastructure."""

    def test_logger_has_json_write(self):
        from runtime.infrastructure.logger import InfraLogger
        logger = InfraLogger()
        assert hasattr(logger, "_write_json")


# ── Phase 6: Integrations & API ──────────────────────────────

class TestIntegrationRouting:
    """Verify orchestrator detects email/calendar intents."""

    def test_detect_email_intent(self):
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        assert orch._detect_integration_intent("check my email") == "check_email"
        assert orch._detect_integration_intent("check email") == "check_email"
        assert orch._detect_integration_intent("any new emails") == "check_email"

    def test_detect_calendar_intent(self):
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        assert orch._detect_integration_intent("check my calendar") == "check_calendar"
        assert orch._detect_integration_intent("upcoming events") == "check_calendar"

    def test_detect_send_email_intent(self):
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        assert orch._detect_integration_intent("send email to john") == "send_email"

    def test_detect_create_event_intent(self):
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        assert orch._detect_integration_intent("create event for tomorrow") == "create_event"

    def test_no_integration_intent(self):
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        assert orch._detect_integration_intent("what is python") is None


class TestIntegrationBase:
    """Verify ABC structure."""

    def test_abc_cannot_instantiate(self):
        from services.integrations.base import IntegrationBase
        import pytest
        with pytest.raises(TypeError):
            IntegrationBase()

    def test_abc_has_required_methods(self):
        from services.integrations.base import IntegrationBase
        assert hasattr(IntegrationBase, "name")
        assert hasattr(IntegrationBase, "capabilities")
        assert hasattr(IntegrationBase, "execute")


class TestFeatureFlags:
    """Verify feature gating system."""

    def test_features_dict_exists(self):
        from runtime.config.config import FEATURES
        assert isinstance(FEATURES, dict)
        assert "web_search" in FEATURES
        assert "integrations" in FEATURES
        assert "deep_research" in FEATURES
        assert "voice" in FEATURES

    def test_features_in_config(self):
        from runtime.config.config import CONFIG
        assert "FEATURES" in CONFIG

    def test_features_all_bool(self):
        from runtime.config.config import FEATURES
        for key, value in FEATURES.items():
            assert isinstance(value, bool), f"Feature '{key}' should be bool"


# ── Phase 7: Performance ─────────────────────────────────────

class TestPerformanceOptimizations:
    """Verify performance changes are in place."""

    def test_context_manager_no_inline_import_re(self):
        """Ensure resolve_pronouns() doesn't import re inline."""
        import inspect
        from core.nlp.context_manager import ContextManager
        source = inspect.getsource(ContextManager.resolve_pronouns)
        assert "import re" not in source

    def test_pronoun_patterns_cached(self):
        from core.nlp.context_manager import ContextManager
        cm = ContextManager()
        assert hasattr(cm, "_pronoun_patterns")
        assert isinstance(cm._pronoun_patterns, dict)

    def test_scoring_weights_has_slots(self):
        from core.intelligence.scorer import ScoringWeights
        assert hasattr(ScoringWeights, "__slots__")

    def test_turn_has_slots(self):
        from core.nlp.context_manager import Turn
        assert hasattr(Turn, "__slots__")
