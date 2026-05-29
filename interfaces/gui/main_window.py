"""
Quarky AI — Main Window

Frameless glassmorphism shell that wires together:
- Custom title bar (drag, min, max, close)
- Collapsible sidebar (history, memory, settings, monitor)
- Chat panel (bubbles, input, mic button)
- Voice overlay (full-screen orb + transcription)
- Toast notifications (top-right stack)
- System tray (always-on, right-click menu)

The backend orchestrator runs on a worker thread so the UI never freezes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
)
from PySide6.QtGui import QColor

from interfaces.gui import theme
from interfaces.gui.title_bar import TitleBar
from interfaces.gui.chat_panel import ChatPanel
from interfaces.gui.sidebar import Sidebar
from interfaces.gui.voice_overlay import VoiceOverlay
from interfaces.gui.toast import ToastContainer
from interfaces.gui.tray import TrayIcon


# ── Backend worker (runs orchestrator on separate thread) ────

class _BackendWorker(QObject):
    """Processes user queries on a background thread."""

    response_ready = Signal(str)              # full response (non-streaming fallback)
    stream_token = Signal(str)                # single token chunk for streaming
    stream_done = Signal(str, dict)           # (full_text, metadata) when stream ends
    progress_msg = Signal(str)                # interim status ("let me look into that...")
    boot_done = Signal(list)
    voice_state_changed = Signal(str)   # "idle","listening","processing","speaking","error","off"

    def __init__(self):
        super().__init__()
        self._orch = None

    @Slot()
    def boot(self):
        from core.orchestrator import Orchestrator
        self._orch = Orchestrator()
        log = self._orch.boot()
        # Wire progress callback so interim messages reach the UI
        self._orch.set_progress_callback(lambda msg: self.progress_msg.emit(msg))
        try:
            self._orch.prewarm_async()
        except Exception:
            pass
        self.boot_done.emit(log)

    @Slot(str)
    def process(self, text: str):
        if self._orch is None:
            self.response_ready.emit("Still starting up...")
            return
        try:
            reply = self._orch.process(text)
        except Exception as e:
            reply = f"Something went wrong: {e}"
        # Stream the reply token-by-token to the GUI
        self._stream_reply(reply)

    def _stream_reply(self, text: str):
        """Emit text as individual token signals for cinematic streaming."""
        import re
        tokens = re.findall(r'\S+|\s+', text)  # split preserving whitespace
        for tok in tokens:
            self.stream_token.emit(tok)
        metadata = {}  # can be enriched with source/confidence later
        self.stream_done.emit(text, metadata)

    @Slot()
    def start_voice(self):
        """Start the voice pipeline on the worker thread."""
        if self._orch is None:
            self.voice_state_changed.emit("error")
            return
        try:
            from interfaces.voice.pipeline import VoiceState
            pipeline = getattr(self._orch, "_voice", None)
            if pipeline is None:
                ok = self._orch.start_voice()
                pipeline = getattr(self._orch, "_voice", None)
            else:
                ok = pipeline.is_running()
            if ok and pipeline:
                pipeline.set_state_callback(
                    lambda s: self.voice_state_changed.emit(s.value)
                )
                self.voice_state_changed.emit("idle")
            else:
                self.voice_state_changed.emit("error")
        except Exception:
            self.voice_state_changed.emit("error")

    @Slot()
    def stop_voice(self):
        """Stop the voice pipeline on the worker thread."""
        if self._orch:
            try:
                self._orch.stop_voice()
            except Exception:
                pass
        self.voice_state_changed.emit("off")


class MainWindow(QMainWindow):
    """Top-level frameless window."""

    _query_requested = Signal(str)
    _voice_start_requested = Signal()
    _voice_stop_requested = Signal()
    _metrics_ready = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quarky AI")
        self.setMinimumSize(960, 640)
        self.resize(1200, 780)

        # Frameless + translucent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Central widget ────────────────────────────────────
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"""
            #central {{
                background: {theme.WINDOW_BG};
                border-radius: 10px;
                border: 1px solid {theme.GLASS_BORDER};
            }}
        """)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar()
        root.addWidget(self._title_bar)

        # Body = sidebar + chat
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        body.addWidget(self._sidebar)

        self._chat = ChatPanel()
        body.addWidget(self._chat, 1)

        root.addLayout(body, 1)

        # Voice overlay (stacked on top of everything)
        self._voice_overlay = VoiceOverlay(central)
        self._voice_overlay.dismissed.connect(self._on_voice_dismissed)

        # Toast container
        self._toasts = ToastContainer(central)

        # ── System tray ───────────────────────────────────────
        self._tray = TrayIcon(self)
        self._tray.show_requested.connect(self._show_from_tray)
        self._tray.quit_requested.connect(self._quit_app)
        self._tray.voice_toggled.connect(self._on_voice_enabled)
        self._tray.show()

        # ── Backend thread ────────────────────────────────────
        self._worker = _BackendWorker()
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.boot)
        self._worker.boot_done.connect(self._on_boot_done)
        self._worker.response_ready.connect(self._on_response)
        self._worker.stream_token.connect(self._on_stream_token)
        self._worker.stream_done.connect(self._on_stream_done)
        self._worker.progress_msg.connect(self._on_progress_msg)
        self._worker.voice_state_changed.connect(self._on_voice_state)
        self._query_requested.connect(self._worker.process)
        self._voice_start_requested.connect(self._worker.start_voice)
        self._voice_stop_requested.connect(self._worker.stop_voice)
        self._metrics_ready.connect(self._apply_monitor_metrics)

        self._thread.start()

        # ── Wire UI signals ───────────────────────────────────
        self._chat.message_sent.connect(self._on_user_message)
        self._chat.mic_button.clicked.connect(self._toggle_voice)

        # System monitor timer — runs off-thread to avoid UI stalls
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._schedule_monitor_update)
        self._monitor_timer.start(3000)
        self._monitor_running = False
        self._voice_active = False
        self._streaming_bubble = None

    # ── Slots ─────────────────────────────────────────────────

    @Slot(list)
    def _on_boot_done(self, log: list):
        ok = sum(1 for m in log if m.startswith("[+]"))
        fail = sum(1 for m in log if m.startswith("[!]"))
        self._toasts.push(
            "Quarky Ready",
            f"{ok} systems online, {fail} issues",
            "success" if fail == 0 else "warning",
        )
        self._chat.add_bot_message(
            "Hey! I'm Quarky — your personal AI assistant. Ask me anything."
        )
        # Auto-start voice pipeline after boot completes
        self._voice_start_requested.emit()

    @Slot(str)
    def _on_user_message(self, text: str):
        self._chat.show_typing(True)
        self._streaming_bubble = None
        self._query_requested.emit(text)

    @Slot(str)
    def _on_stream_token(self, token: str):
        """Receive a single token from the backend and feed it to the streaming bubble."""
        if self._streaming_bubble is None:
            self._streaming_bubble = self._chat.start_streaming()
        self._streaming_bubble.append_token(token)
        # Keep scroll pinned during streaming
        self._chat._scroll_to_bottom()

    @Slot(str, dict)
    def _on_stream_done(self, full_text: str, metadata: dict):
        """All tokens emitted — finalize the streaming bubble."""
        if self._streaming_bubble is not None:
            self._streaming_bubble.finish()
            self._streaming_bubble = None
        self._chat.show_typing(False)

    @Slot(str)
    def _on_response(self, text: str):
        """Non-streaming fallback (e.g. boot message)."""
        self._chat.show_typing(False)
        self._chat.add_bot_message(text)

    @Slot(str)
    def _on_progress_msg(self, msg: str):
        """Show an interim progress message (e.g. 'let me look into that...')."""
        self._chat.add_bot_message(msg)

    @Slot(str)
    def _on_voice_state(self, state: str):
        """React to real voice pipeline state changes."""
        if state == "idle":
            self._voice_active = True
            self._tray.set_voice_active(True)
            self._voice_overlay.set_status("Say 'Hey Quarky' to wake me...")
        elif state == "listening":
            self._voice_active = True
            self._tray.set_voice_active(True)
            self._voice_overlay.set_status("Listening...")
            if not self._voice_overlay.isVisible():
                self._voice_overlay.activate()
        elif state == "processing":
            self._voice_overlay.set_status("Thinking...")
        elif state == "speaking":
            self._voice_overlay.set_status("Quarky says:")
        elif state == "error":
            self._voice_active = False
            self._toasts.push(
                "Voice Unavailable",
                "Mic or Vosk model not found. Check setup.",
                "warning",
            )
            self._tray.set_voice_active(False)
        elif state == "off":
            self._voice_active = False
            self._tray.set_voice_active(False)
            if self._voice_overlay.isVisible():
                self._voice_overlay.deactivate()

    def _toggle_voice(self):
        """Called by mic button — toggle the real voice pipeline."""
        if self._voice_active:
            self._voice_stop_requested.emit()
            if self._voice_overlay.isVisible():
                self._voice_overlay.deactivate()
        else:
            self._voice_start_requested.emit()

    def _on_voice_dismissed(self):
        pass  # overlay dismissed; pipeline stays running in background

    def _on_voice_enabled(self, enabled: bool):
        """Called by tray toggle."""
        if enabled:
            self._voice_start_requested.emit()
        else:
            self._voice_stop_requested.emit()
            if self._voice_overlay.isVisible():
                self._voice_overlay.deactivate()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()

    def _quit_app(self):
        self._thread.quit()
        self._thread.wait(2000)
        QApplication.quit()

    def _schedule_monitor_update(self):
        """Fire off a daemon thread so psutil never blocks the UI thread."""
        if self._monitor_running:
            return
        import threading
        self._monitor_running = True
        threading.Thread(target=self._fetch_monitor_metrics, daemon=True).start()

    def _fetch_monitor_metrics(self):
        """Collect metrics on background thread, then post to UI thread."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)   # 0.5 s blocking — off-thread
            ram = psutil.virtual_memory().percent
            self._metrics_ready.emit(float(cpu), float(ram))
        except Exception:
            pass
        finally:
            self._monitor_running = False

    @Slot(float, float)
    def _apply_monitor_metrics(self, cpu: float, ram: float):
        """Update sidebar monitor on the UI thread (safe for Qt widgets)."""
        try:
            self._sidebar.monitor_page.update_metrics(cpu, ram)
        except Exception:
            pass

    # ── Layout events ─────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Stretch voice overlay to fill the window
        if self._voice_overlay:
            self._voice_overlay.setGeometry(self.centralWidget().rect())
        # Reposition toasts
        if self._toasts:
            self._toasts.reposition(self.centralWidget().size())

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "Quarky AI",
            "Still running in the system tray. Right-click to quit.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )


# Import needed for closeEvent
from PySide6.QtWidgets import QSystemTrayIcon  # noqa: E402
