"""
Quarky_Ai — Orchestrator (v2)

Central wiring: builds all subsystems, connects them, and provides
a single `process(text) -> str` entry point used by CLI, voice, and GUI.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class Orchestrator:
    """Wires all v2 subsystems together and processes user input."""

    def __init__(self):
        self._ready = False
        # subsystem references (lazy-loaded)
        self._memory: Any = None
        self._tracker: Any = None
        self._scorer: Any = None
        self._classifier: Any = None
        self._session: Any = None
        self._context_mgr: Any = None
        self._spell: Any = None
        self._entities: Any = None
        self._nlp_cls: Any = None
        self._router: Any = None
        self._forwarder: Any = None
        self._output_gate: Any = None
        self._feedback: Any = None
        self._correction: Any = None
        self._trainer: Any = None
        self._pattern_extractor: Any = None
        self._habits_tracker: Any = None
        self._notifications: Any = None
        self._integrations: Any = None
        self._voice: Any = None
        self._models_warming = False
        self._models_warmed = False
        self._progress_callback: Any = None  # GUI progress phrase callback

    # ── bootstrap ────────────────────────────────────────────

    def boot(self) -> list[str]:
        """
        Initialize all subsystems in dependency order.
        Returns list of status messages.
        """
        log: list[str] = []

        # 1. Intelligence core
        try:
            from MAIINNN.Intelligence.tracker import TokenTracker
            from MAIINNN.Intelligence.scorer import TokenScorer
            from MAIINNN.Intelligence.classifier import SpecificityClassifier
            self._tracker = TokenTracker()
            self._scorer = TokenScorer()
            self._classifier = SpecificityClassifier()
            log.append("[+] Intelligence core")
        except Exception as e:
            log.append(f"[!] Intelligence core: {e}")

        # 2. Memory
        try:
            from MAIINNN.Memory.manager_v2 import MemoryManagerV2
            self._memory = MemoryManagerV2()
            log.append("[+] Memory v2")
        except Exception as e:
            log.append(f"[!] Memory v2: {e}")

        # 3. NLP
        try:
            from MAIINNN.NLP.context_manager import ContextManager
            from MAIINNN.NLP import spell_check as _spell_mod
            from MAIINNN.NLP.entity_extractor import EntityExtractor
            from MAIINNN.NLP import classifier as _nlp_cls_mod
            self._context_mgr = ContextManager()
            self._spell = _spell_mod  # module with correct() function
            self._entities = EntityExtractor()
            self._nlp_cls = _nlp_cls_mod  # module with classify() function
            log.append("[+] NLP v2")
        except Exception as e:
            log.append(f"[!] NLP v2: {e}")

        # 4. Brain (router, forwarder, output gate)
        try:
            from MAIINNN.Connectors.intent_router import IntentRouter
            from MAIINNN.Connectors.forwarder import Forwarder
            from MAIINNN.Decision import output_gate as _output_gate_mod
            self._router = IntentRouter()
            self._forwarder = Forwarder()
            if self._memory and hasattr(self._forwarder, "set_memory"):
                self._forwarder.set_memory(self._memory)
            self._output_gate = _output_gate_mod  # module with process() function
            log.append("[+] Brain pipeline")
        except Exception as e:
            log.append(f"[!] Brain pipeline: {e}")

        # 5. Learning
        try:
            from MAIINNN.Learning.feedback import FeedbackProcessor
            from MAIINNN.Learning.correction import CorrectionEngine
            from MAIINNN.Learning.trainer import Trainer
            from MAIINNN.Learning.pattern_extractor import PatternExtractor
            self._feedback = FeedbackProcessor()
            self._correction = CorrectionEngine()
            self._trainer = Trainer()
            self._pattern_extractor = PatternExtractor()
            # Wire dependencies into learning subsystems
            if self._memory:
                self._feedback.set_memory(self._memory)
                self._correction.set_memory(self._memory)
                self._pattern_extractor.set_memory(self._memory)
            if self._tracker:
                self._feedback.set_tracker(self._tracker)
            log.append("[+] Learning system")
        except Exception as e:
            log.append(f"[!] Learning system: {e}")

        # 6. Session
        try:
            from MAIINNN.session_v2 import get_session_v2
            self._session = get_session_v2()
            if self._memory:
                self._session.set_memory(self._memory)
            log.append("[+] Session v2")
        except Exception as e:
            log.append(f"[!] Session v2: {e}")

        # 7. Habits
        try:
            from MAIINNN.Functions.habits.tracker import HabitTracker
            self._habits_tracker = HabitTracker()
            if self._session:
                self._session.set_habits(self._habits_tracker)
            log.append("[+] Habits tracker")
        except Exception as e:
            log.append(f"[!] Habits tracker: {e}")

        # 8. Notifications
        try:
            from MAIINNN.Functions.notifications.manager import NotificationManager
            self._notifications = NotificationManager()
            log.append("[+] Notification manager")
        except Exception as e:
            log.append(f"[!] Notifications: {e}")

        # 9. Integrations (email / calendar)
        try:
            from MAIINNN.Functions.integrations.unified import UnifiedIntegrations
            self._integrations = UnifiedIntegrations()
            providers = self._integrations.connected_providers()
            if providers:
                log.append(f"[+] Integrations ({', '.join(providers)})")
            else:
                log.append("[+] Integrations (no providers connected)")
        except Exception as e:
            log.append(f"[!] Integrations: {e}")

        self._ready = True

        # Start health heartbeat collector
        self._health_status: dict[str, Any] = {}
        threading.Thread(target=self._health_heartbeat, daemon=True).start()

        return log

    def prewarm_async(self) -> None:
        """Warm heavy NLP/semantic models in background to reduce first-query lag."""
        if self._models_warming or self._models_warmed:
            return
        self._models_warming = True
        threading.Thread(target=self._prewarm_models, daemon=True).start()

    def _health_heartbeat(self) -> None:
        """Collect subsystem health every 30s."""
        while self._ready:
            status: dict[str, Any] = {"timestamp": time.time()}
            status["intelligence"] = "ok" if self._tracker else "unavailable"
            status["memory"] = "ok" if self._memory else "unavailable"
            status["nlp"] = "ok" if self._spell else "unavailable"
            status["brain"] = "ok" if self._forwarder else "unavailable"
            status["learning"] = "ok" if self._trainer else "unavailable"
            status["voice"] = "active" if self._voice and self._voice.is_running() else "off"
            # System metrics
            try:
                from MAIINNN.Functions.monitor.collector import SystemCollector
                metrics = SystemCollector().collect()
                status["system"] = {
                    "cpu": metrics.cpu_percent,
                    "ram": metrics.memory_percent,
                    "disk": metrics.disk_percent,
                }
            except Exception:
                status["system"] = "unavailable"
            self._health_status = status
            time.sleep(30)

    def get_health(self) -> dict[str, Any]:
        """Return latest health snapshot."""
        return dict(self._health_status)

    def _prewarm_models(self) -> None:
        try:
            from MAIINNN.Connectors.forwarder import think
            think("hello")
        except Exception:
            pass
        finally:
            self._models_warming = False
            self._models_warmed = True

    def _looks_like_question(self, text: str) -> bool:
        lower = text.lower().strip()
        if "?" in lower:
            return True
        return any(
            lower.startswith(w)
            for w in ("what", "who", "where", "when", "why", "how", "which", "tell me", "explain", "define", "describe")
        )

    def _should_use_warmup_fastpath(self, text: str) -> bool:
        """Only intercept likely-unknown questions while models are warming."""
        if self._models_warmed:
            return False
        if not self._looks_like_question(text):
            return False

        lower = text.lower().strip()

        # Let common built-in questions pass through normal reasoning path.
        quick_known_patterns = (
            "who are you",
            "what is your name",
            "what time",
            "current time",
            "what day",
            "what date",
            "hello",
            "hi",
            "how are you",
        )
        if any(p in lower for p in quick_known_patterns):
            return False

        # Route only longer factual questions to fastpath during warmup.
        return len(lower.split()) >= 6

    def set_progress_callback(self, cb):
        """Set a callback invoked to stream a progress phrase to the UI."""
        self._progress_callback = cb

    def _emit_progress(self, text: str):
        """Emit a progress phrase to the UI immediately."""
        if self._progress_callback:
            try:
                self._progress_callback(text)
            except Exception:
                pass

    # ── integration handling ────────────────────────────────

    _EMAIL_PATTERNS = (
        "check my email", "check email", "check my mail", "read my email",
        "any new emails", "unread emails", "inbox", "show my emails",
        "how many emails", "email count",
    )
    _SEND_EMAIL_PATTERNS = ("send email", "send an email", "send mail", "email to")
    _CALENDAR_PATTERNS = (
        "check my calendar", "check calendar", "my schedule", "upcoming events",
        "what's on my calendar", "next meeting", "show my events",
        "any meetings", "today's events", "events today",
    )
    _CREATE_EVENT_PATTERNS = (
        "create event", "create an event", "schedule a meeting",
        "add to calendar", "new event", "book a meeting",
    )

    def _detect_integration_intent(self, text: str) -> str | None:
        """Return integration intent type or None."""
        lower = text.lower().strip()
        if any(p in lower for p in self._SEND_EMAIL_PATTERNS):
            return "send_email"
        if any(p in lower for p in self._EMAIL_PATTERNS):
            return "check_email"
        if any(p in lower for p in self._CREATE_EVENT_PATTERNS):
            return "create_event"
        if any(p in lower for p in self._CALENDAR_PATTERNS):
            return "check_calendar"
        return None

    def _handle_integration(self, intent: str, text: str) -> str:
        """Execute an integration action and return a human-readable reply."""
        integ = self._integrations
        if not integ:
            return "Integrations are not available. Please check your setup."
        providers = integ.connected_providers()
        if not providers:
            return ("No email or calendar providers are connected yet. "
                    "Please set up Google or Microsoft credentials first.")

        if intent == "check_email":
            emails = integ.emails(max_per_provider=5)
            if not emails:
                return "Your inbox is empty — no new emails."
            unread = integ.unread_count()
            lines = [f"You have {unread} unread email(s). Here are the latest:"]
            for e in emails[:5]:
                lines.append(f"  • **{e.subject}** from {e.sender}")
            return "\n".join(lines)

        if intent == "send_email":
            return ("I can send emails, but I need more details. "
                    "Please say: send email to <address> subject <subject> body <message>")

        if intent == "check_calendar":
            events = integ.events(max_per_provider=5)
            if not events:
                return "No upcoming events on your calendar."
            lines = ["Here are your upcoming events:"]
            for ev in events[:5]:
                loc = f" at {ev.location}" if ev.location else ""
                lines.append(f"  • **{ev.summary}** — {ev.start}{loc}")
            return "\n".join(lines)

        if intent == "create_event":
            return ("I can create calendar events. "
                    "Please say: create event <title> on <date> from <start> to <end>")

        return "I'm not sure how to handle that integration request."

    # ── web-search fallback ──────────────────────────────────

    def _web_fallback(self, query: str) -> str:
        """
        Search the web for query, store facts in memory, return best fact as reply.
        Uses adaptive-depth research first, falls back to basic web learner.
        Returns empty string if search is unavailable or yields nothing.
        """
        # Try adaptive-depth researcher first
        try:
            from MAIINNN.Functions.web.deep_researcher import AdaptiveResearcher
            researcher = AdaptiveResearcher()
            if researcher.is_available:
                result = researcher.research(query, timeout=6.0)
                if result.answer:
                    # Store facts in memory for future recall
                    if self._memory and result.facts:
                        for fact in result.facts[:3]:
                            try:
                                self._memory.store(
                                    text=fact,
                                    source="web_research",
                                    importance=0.5,
                                    topic=query[:50],
                                )
                            except Exception:
                                pass
                    if self._trainer:
                        try:
                            self._trainer.add_example(query, "WEB_LOOKUP", source="adaptive_research")
                        except Exception:
                            pass
                    return f"{result.answer}\n_(Learned from the web — stored in memory)_"
        except Exception:
            pass

        # Fallback to basic web learner
        try:
            from MAIINNN.Learning.web_learner import WebLearner
            learner = WebLearner()
            if self._memory:
                learner.set_memory(self._memory)
            if not learner.is_available:
                return ""
            facts = learner.search_and_learn(query, max_results=3, timeout_seconds=4.0)
            if facts:
                best = facts[0]
                if self._trainer:
                    try:
                        self._trainer.add_example(query, "WEB_LOOKUP", source="web_fallback")
                    except Exception:
                        pass
                return f"{best.text}\n_(Learned from the web — stored in memory)_"
        except Exception:
            pass
        return ""

    # ── main entry point ─────────────────────────────────────

    def process(self, text: str) -> str:
        """
        Process user input end-to-end.

        Pipeline:
        1. Spell-check
        2. Context resolve (pronouns)
        3. Check correction history
        4. Detect feedback
        5. Classify specificity
        6. Route + forward through brain
        7. Output gate
        8. Record session
        """
        if not self._ready:
            return "Quarky is still booting up. Please try again in a moment."

        # 1. Spell correction
        corrected = text
        if self._spell:
            corrected = self._spell.correct(text)  # module-level function

        # 2. Context resolution
        resolved = corrected
        if self._context_mgr:
            resolved = self._context_mgr.resolve_pronouns(corrected)

        # Fast path while heavy models are still warming:
        # keep app responsive for factual questions instead of stalling.
        if self._should_use_warmup_fastpath(resolved):
            if not self._models_warming:
                web_reply = self._web_fallback(resolved)
                if web_reply:
                    self._record(text, web_reply, "web", 0.5, "")
                    return web_reply
            if self._trainer:
                try:
                    self._trainer.add_example(
                        resolved,
                        "UNKNOWN_QUESTION",
                        source="prewarm_fast_path",
                    )
                except Exception:
                    pass
            reply = (
                "I am still warming up my deeper reasoning. I saved your question and "
                "I can learn from it. Please ask again in a few seconds."
            )
            self._record(text, reply, "warmup", 0.2, "")
            return reply

        # 2b. Integration routing (email / calendar)
        integration_intent = self._detect_integration_intent(resolved)
        if integration_intent:
            try:
                from AppStudio.Config import FEATURES
                if FEATURES.get("integrations", True):
                    reply = self._handle_integration(integration_intent, resolved)
                    self._record(text, reply, "integration", 0.8, "")
                    return reply
            except Exception:
                pass

        # 3. Correction lookup
        if self._correction:
            cached = self._correction.check(resolved)
            if cached:
                self._record(text, cached, "correction")
                return cached

        # 4. Feedback detection
        if self._feedback:
            fb = self._feedback.detect_feedback(resolved)
            if fb and fb.feedback_type in ("positive", "negative", "correction"):
                self._feedback.apply_feedback(fb)
                if fb.feedback_type == "correction" and fb.correction:
                    self._record(text, f"Got it! I'll remember: {fb.correction}", "learning")
                    return f"Got it! I'll remember: {fb.correction}"
                if fb.feedback_type == "positive":
                    return "Glad that helped!"
                if fb.feedback_type == "negative":
                    return "Sorry about that. What's the right answer?"

        # 5. Classify
        tier = ""
        if self._classifier:
            score = self._classifier.classify_query(resolved)
            if score >= 0.65:
                tier = "SS"
            elif score >= 0.55:
                tier = "GS"
            elif score >= 0.40:
                tier = "SG"
            else:
                tier = "GG"
        # 5b. Pre-query memory — check if we already know the answer
        memory_context = ""
        if self._memory:
            try:
                mem_results = self._memory.search(resolved, top_k=3)
                if mem_results and mem_results.best:
                    memory_context = mem_results.best.text
            except Exception:
                pass

        # 6. Route and process — enrich input with memory context if available
        response = ""
        source = "fallback"
        confidence = 0.0
        enriched = resolved
        if memory_context:
            enriched = f"{resolved}\n[Memory context: {memory_context}]"

        try:
            if self._output_gate:
                final = self._output_gate.process(enriched)
                if hasattr(final, "response") and final.response:
                    response = final.response
                    source = getattr(final, "source", "analytical")
                    confidence = getattr(final, "confidence", 0.5)
        except Exception:
            pass

        if not response:
            try:
                if self._forwarder:
                    from MAIINNN.Connectors.forwarder import think
                    result = think(enriched)
                    if result is not None and hasattr(result, "analytical") and result.analytical:
                        response = result.analytical.response
                        source = result.analytical.source
                        confidence = result.analytical.confidence
            except Exception:
                pass

        if not response:
            response = "I'm not sure how to help with that. Could you rephrase?"
            source = "fallback"

        # Web fallback: if confidence is too low and query looks informational,
        # search the web and supersede the fallback response
        _WEB_FALLBACK_THRESHOLD = 0.35
        if confidence < _WEB_FALLBACK_THRESHOLD and source in ("fallback", "creative"):
            # Only trigger for questions/informational queries, not commands
            is_question = self._looks_like_question(resolved)
            if is_question:
                # Immediate progress phrase to keep user informed
                self._emit_progress("Oh wait, let me look into that...")
                web_reply = self._web_fallback(resolved)
                if web_reply:
                    response = web_reply
                    source = "web"
                    confidence = 0.5
                else:
                    if self._trainer:
                        try:
                            self._trainer.add_example(
                                resolved,
                                "UNKNOWN_QUESTION",
                                source="fallback_timeout_or_no_result",
                            )
                        except Exception:
                            pass
                    response = (
                        "I could not find a reliable answer quickly, but I saved this question "
                        "to learn from it. Please try rephrasing or ask me again."
                    )
                    source = "fallback"
                    confidence = 0.2

        # 7. Continuous learning: record every interaction for improvement
        self._record(text, response, source, confidence, tier)
        self._learn_from_interaction(resolved, response, source, confidence)

        return response

    def _learn_from_interaction(
        self,
        query: str,
        response: str,
        source: str,
        confidence: float,
    ):
        """Record learning signals after every interaction."""
        def _do_learn():
            try:
                # Store high-confidence responses in memory for reuse
                if confidence >= 0.6 and source not in ("fallback", "warmup") and self._memory:
                    self._memory.store(
                        text=f"Q: {query}\nA: {response}",
                        source=f"learned:{source}",
                        importance=min(0.7, confidence),
                        topic=query[:50],
                    )
                # Extract patterns from Q&A pair
                if confidence >= 0.5 and source not in ("fallback", "warmup"):
                    pe = getattr(self, "_pattern_extractor", None)
                    if pe:
                        pe.extract_from_pair(query, response)
                # Track training example
                if self._trainer:
                    label = source.upper() if source != "fallback" else "UNKNOWN_QUESTION"
                    self._trainer.add_example(query, label, source="continuous")
                    # Trigger retrain if enough new examples
                    if self._trainer.should_retrain():
                        self._trainer.retrain_classifier()
            except Exception:
                pass
        threading.Thread(target=_do_learn, daemon=True).start()

    def _record(
        self,
        user_text: str,
        response: str,
        source: str,
        confidence: float = 0.0,
        tier: str = "",
    ):
        if self._session:
            threading.Thread(
                target=self._safe_add_session_turn,
                args=(user_text, response, source, confidence, tier),
                daemon=True,
            ).start()
        if self._context_mgr:
            # Context/topic tracking can trigger heavy similarity model loads.
            # Keep it off the hot response path so UI/voice never appears frozen.
            threading.Thread(
                target=self._safe_add_context_turn,
                args=(user_text, response),
                daemon=True,
            ).start()

    def _safe_add_context_turn(self, user_text: str, response: str) -> None:
        try:
            if self._context_mgr:
                self._context_mgr.add_turn("user", user_text)
                self._context_mgr.add_turn("quarky", response)
        except Exception:
            pass

    def _safe_add_session_turn(
        self,
        user_text: str,
        response: str,
        source: str,
        confidence: float,
        tier: str,
    ) -> None:
        try:
            if self._session:
                self._session.add_turn(
                    user_text=user_text,
                    response=response,
                    source=source,
                    confidence=confidence,
                    specificity_tier=tier,
                )
        except Exception:
            pass

    # ── accessors ────────────────────────────────────────────

    @property
    def session(self) -> Any:
        return self._session

    @property
    def memory(self) -> Any:
        return self._memory

    @property
    def notifications(self) -> Any:
        return self._notifications

    @property
    def integrations(self) -> Any:
        return self._integrations

    @property
    def voice(self) -> Any:
        return self._voice

    def start_voice(self) -> bool:
        """Start the voice pipeline."""
        try:
            from AppStudio.Voice.pipeline import VoicePipeline
            self._voice = VoicePipeline()
            self._voice.set_process_fn(self.process)
            return self._voice.start()
        except Exception:
            return False

    def stop_voice(self):
        if self._voice:
            self._voice.stop()


# ─── module-level singleton ──────────────────────────────────

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
        _orchestrator.boot()
    return _orchestrator
