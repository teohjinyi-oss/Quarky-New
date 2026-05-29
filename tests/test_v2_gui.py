"""
Tests for Quarky_Ai v2 GUI module — widget creation and signal wiring.
These tests verify widgets can be instantiated and basic signals work
without requiring a display (uses offscreen rendering).
"""

import os
import sys
import pytest

# Force offscreen rendering so tests work in CI / headless
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

# Ensure a single QApplication for the whole test session
_app = QApplication.instance() or QApplication(sys.argv)


# ── Theme ────────────────────────────────────────────────────

class TestTheme:
    def test_palette_constants(self):
        from interfaces.gui.theme import ACCENT, WINDOW_BG, TEXT_PRIMARY, GLOBAL_QSS
        assert ACCENT.startswith("#")
        assert WINDOW_BG.startswith("#")
        assert TEXT_PRIMARY.startswith("#")
        assert "font-family" in GLOBAL_QSS

    def test_dimensions(self):
        from interfaces.gui.theme import SIDEBAR_WIDTH, BORDER_RADIUS, INPUT_HEIGHT
        assert SIDEBAR_WIDTH > 0
        assert BORDER_RADIUS > 0
        assert INPUT_HEIGHT > 0


# ── Title Bar ────────────────────────────────────────────────

class TestTitleBar:
    def test_creation(self):
        from interfaces.gui.title_bar import TitleBar
        tb = TitleBar()
        assert tb.height() > 0

    def test_has_close_button(self):
        from interfaces.gui.title_bar import TitleBar
        tb = TitleBar()
        assert tb._btn_close is not None


# ── Chat Panel ───────────────────────────────────────────────

class TestChatPanel:
    def test_creation(self):
        from interfaces.gui.chat_panel import ChatPanel
        cp = ChatPanel()
        assert cp is not None

    def test_add_messages(self):
        from interfaces.gui.chat_panel import ChatPanel
        cp = ChatPanel()
        cp.add_user_message("Hello")
        cp.add_bot_message("Hi there!")
        # No crash = success

    def test_signal_emitted(self):
        from interfaces.gui.chat_panel import ChatPanel
        cp = ChatPanel()
        received = []
        cp.message_sent.connect(lambda t: received.append(t))
        cp._input.setText("test")
        cp._send()
        assert received == ["test"]

    def test_typing_indicator(self):
        from interfaces.gui.chat_panel import ChatPanel
        cp = ChatPanel()
        cp.show_typing(True)
        assert not cp._typing.isHidden()
        cp.show_typing(False)
        assert cp._typing.isHidden()

    def test_bubble_render(self):
        from interfaces.gui.chat_panel import ChatBubble
        bubble = ChatBubble("**bold** and `code`", is_user=True)
        assert bubble is not None


# ── Sidebar ──────────────────────────────────────────────────

class TestSidebar:
    def test_creation(self):
        from interfaces.gui.sidebar import Sidebar
        sb = Sidebar()
        assert sb.width() > 0

    def test_tab_selection(self):
        from interfaces.gui.sidebar import Sidebar
        sb = Sidebar()
        sb._select_tab(2)
        assert sb._stack.currentIndex() == 2

    def test_collapse(self):
        from interfaces.gui.sidebar import Sidebar
        from interfaces.gui.theme import SIDEBAR_COLLAPSED_WIDTH
        sb = Sidebar()
        sb.toggle_collapsed()
        assert sb.width() == SIDEBAR_COLLAPSED_WIDTH
        sb.toggle_collapsed()  # restore


# ── Voice Overlay ────────────────────────────────────────────

class TestVoiceOverlay:
    def test_creation(self):
        from interfaces.gui.voice_overlay import VoiceOverlay
        vo = VoiceOverlay()
        assert vo is not None
        assert not vo.isVisible()

    def test_activate_deactivate(self):
        from interfaces.gui.voice_overlay import VoiceOverlay
        vo = VoiceOverlay()
        vo.activate()
        assert vo.isVisible()
        vo.deactivate()

    def test_orb(self):
        from interfaces.gui.voice_overlay import VoiceOrb
        orb = VoiceOrb()
        orb.set_level(0.5)
        orb.start()
        orb.stop()


# ── Toast Notifications ─────────────────────────────────────

class TestToast:
    def test_push(self):
        from interfaces.gui.toast import ToastContainer
        tc = ToastContainer()
        tc.push("Test", "Hello", "info")
        assert tc.layout().count() > 0

    def test_levels(self):
        from interfaces.gui.toast import Toast
        for level in ("info", "success", "warning", "error"):
            t = Toast("Title", "Body", level)
            assert t is not None


# ── System Tray ──────────────────────────────────────────────

class TestTray:
    def test_creation(self):
        from interfaces.gui.tray import TrayIcon
        tray = TrayIcon()
        assert tray.toolTip() == "Quarky AI — Always listening"

    def test_signals(self):
        from interfaces.gui.tray import TrayIcon
        tray = TrayIcon()
        received = []
        tray.show_requested.connect(lambda: received.append("show"))
        tray.show_requested.emit()
        assert received == ["show"]
