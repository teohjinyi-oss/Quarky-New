"""
System tray icon — always-on, right-click menu, hide/show window.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget


def _create_tray_icon() -> QIcon:
    """Generate a simple coloured circle as the tray icon (no external asset)."""
    px = QPixmap(32, 32)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(124, 92, 252))
    p.setPen(QColor(155, 125, 255))
    p.drawEllipse(2, 2, 28, 28)
    # Q letter
    p.setPen(QColor(255, 255, 255))
    font = p.font()
    font.setPixelSize(18)
    font.setBold(True)
    p.setFont(font)
    p.drawText(px.rect(), 0x0084, "Q")  # AlignCenter
    p.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    """Quarky system tray icon with context menu."""

    show_requested = Signal()
    quit_requested = Signal()
    voice_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(_create_tray_icon(), parent)
        self.setToolTip("Quarky AI — Always listening")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1a1a2e;
                color: #e0e0e8;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(124,92,252,0.25);
            }
        """)

        show_action = QAction("Show Quarky", self)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)

        self._voice_action = QAction("Voice: ON", self)
        self._voice_action.setCheckable(True)
        self._voice_action.setChecked(True)
        self._voice_action.toggled.connect(self._on_voice_toggle)
        menu.addAction(self._voice_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    def _on_voice_toggle(self, checked: bool):
        self._voice_action.setText("Voice: ON" if checked else "Voice: OFF")
        self.voice_toggled.emit(checked)

    def set_voice_active(self, active: bool):
        """Update the tray voice-toggle state without firing the signal."""
        self._voice_action.blockSignals(True)
        self._voice_action.setChecked(active)
        self._voice_action.setText("Voice: ON" if active else "Voice: OFF")
        self._voice_action.blockSignals(False)
