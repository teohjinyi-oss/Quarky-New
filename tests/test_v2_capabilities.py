"""
Tests for v2 New Capabilities: Web, Monitor, Habits, Automation, Notifications
"""

import pytest


# ── Web ──────────────────────────────────────────────────────

class TestWebSummarizer:
    def test_summarize(self):
        from services.web.summarizer import TextSummarizer
        ts = TextSummarizer()
        text = (
            "Python is a programming language. "
            "It is widely used in data science. "
            "Python has a simple syntax. "
            "Many companies use Python for web development."
        )
        summary = ts.summarize(text, max_sentences=2)
        assert hasattr(summary, "summary")
        assert len(summary.summary) > 0
        assert len(summary.summary) < len(text)


class TestWebScraper:
    def test_scraper_init(self):
        from services.web.scraper import WebScraper
        ws = WebScraper()
        assert ws is not None


class TestWebSearch:
    def test_search_init(self):
        from services.web.search import WebSearch
        ws = WebSearch()
        assert ws is not None


# ── Monitor ──────────────────────────────────────────────────

class TestSystemCollector:
    def test_collect(self):
        from services.monitoring.collector import SystemCollector
        sc = SystemCollector()
        metrics = sc.collect()
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0

    def test_summary(self):
        from services.monitoring.collector import SystemCollector
        sc = SystemCollector()
        s = sc.summary()
        assert "CPU" in s


class TestSystemAlerter:
    def test_check_no_crash(self):
        from services.monitoring.alerter import SystemAlerter
        sa = SystemAlerter()
        alerts = sa.check()
        assert isinstance(alerts, list)


class TestMetricsHistory:
    def test_record_and_last(self):
        from services.monitoring.history import MetricsHistory
        from services.monitoring.collector import SystemCollector
        mh = MetricsHistory(max_entries=10)
        sc = SystemCollector()
        metrics = sc.collect()
        mh.record(metrics)
        last = mh.last(1)
        assert len(last) >= 1


# ── Habits ───────────────────────────────────────────────────

class TestHabitTracker:
    def test_record_and_count(self):
        from core.capabilities.habits.tracker import HabitTracker
        ht = HabitTracker()
        initial = ht.count
        ht.record("test_action", "testing")
        assert ht.count >= initial + 1

    def test_recent(self):
        from core.capabilities.habits.tracker import HabitTracker
        ht = HabitTracker()
        ht.record("action_a")
        ht.record("action_b")
        recent = ht.recent(2)
        assert len(recent) >= 2


class TestHabitAnalyzer:
    def test_top_actions(self):
        from core.capabilities.habits.tracker import HabitTracker
        from core.capabilities.habits.analyzer import HabitAnalyzer
        ht = HabitTracker()
        for _ in range(5):
            ht.record("chat")
        ha = HabitAnalyzer(ht)
        top = ha.top_actions(1)
        assert len(top) >= 1


class TestHabitPredictor:
    def test_predict(self):
        from core.capabilities.habits.tracker import HabitTracker
        from core.capabilities.habits.predictor import HabitPredictor
        ht = HabitTracker()
        for _ in range(10):
            ht.record("chat")
        hp = HabitPredictor(ht)
        preds = hp.predict_next(3)
        assert isinstance(preds, list)


class TestRoutineManager:
    def test_suggest_morning(self):
        from core.capabilities.habits.tracker import HabitTracker
        from core.capabilities.habits.routines import RoutineManager
        ht = HabitTracker()
        rm = RoutineManager(ht)
        routine = rm.suggest_morning()
        assert routine.name == "morning"


# ── Automation ───────────────────────────────────────────────

class TestChain:
    def test_chain_success(self):
        from core.capabilities.automation.chain import Chain
        ch = Chain("test")
        ch.add("double", lambda x: x * 2)
        ch.add("add10", lambda x: x + 10)
        result = ch.run(5)
        assert result.success
        assert result.final_output == 20

    def test_chain_failure(self):
        from core.capabilities.automation.chain import Chain
        ch = Chain("test")
        ch.add("fail", lambda x: 1 / 0)
        result = ch.run(5)
        assert not result.success

    def test_chain_empty(self):
        from core.capabilities.automation.chain import Chain
        ch = Chain("empty")
        result = ch.run()
        assert result.success
        assert result.final_output is None


class TestAutomationPlanner:
    def test_plan_no_templates(self):
        from core.capabilities.automation.planner import AutomationPlanner
        planner = AutomationPlanner()
        assert planner.plan("do something") is None


class TestMacroStore:
    def test_save_and_get(self):
        from core.capabilities.automation.macro import MacroStore, Macro
        ms = MacroStore()
        m = Macro(name="test_macro", steps=["step1", "step2"])
        ms.save(m)
        got = ms.get("test_macro")
        assert got is not None
        assert got.steps == ["step1", "step2"]


class TestAutomationExecutor:
    def test_run_unknown(self):
        from core.capabilities.automation.executor import AutomationExecutor
        ae = AutomationExecutor()
        result = ae.run("completely unknown request xyz")
        assert result is None


# ── Notifications ────────────────────────────────────────────

class TestToastNotifier:
    def test_init(self):
        from services.notifications.toast import ToastNotifier
        tn = ToastNotifier()
        assert tn is not None


class TestNotificationManager:
    def test_notify_and_flush(self):
        from services.notifications.manager import NotificationManager
        nm = NotificationManager()
        nm.notify("Test", "Hello", priority=1)
        assert nm.pending_count() == 1
        nm.flush()
        assert nm.pending_count() == 0
        assert len(nm.history) == 1

    def test_priority_ordering(self):
        from services.notifications.manager import NotificationManager
        nm = NotificationManager()
        nm.notify("Low", "msg", priority=0)
        nm.notify("High", "msg", priority=10)
        nm.notify("Mid", "msg", priority=5)
        # After flush, history should have high first
        nm.flush()
        assert nm.history[0].title == "High"


class TestNotificationScheduler:
    def test_schedule_and_tick(self):
        from services.notifications.manager import NotificationManager
        from services.notifications.scheduler import NotificationScheduler
        nm = NotificationManager()
        ns = NotificationScheduler(nm)
        ns.schedule("Test", "Hello", delay_seconds=0)
        ns.tick()
        assert nm.pending_count() >= 1
