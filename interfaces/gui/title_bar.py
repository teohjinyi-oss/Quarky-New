"""
Custom title bar widget for frameless window.
Provides drag, minimize, maximize/restore, and close functionality.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)

from interfaces.gui import theme


class TitleBar(QWidget):
    """Frameless-window custom title bar with glassmorphism styling."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(theme.TITLE_BAR_HEIGHT)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(0)

        # App icon / title
        self._title = QLabel("  Quarky AI")
        self._title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(self._title)
        layout.addStretch()

        # Window buttons
        btn_style = f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
                color: {theme.TEXT_SECONDARY};
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.08); }}
        """
        close_style = f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
                color: {theme.TEXT_SECONDARY};
            }}
            QPushButton:hover {{ background: {theme.ERROR}; color: white; }}
        """

        self._btn_min = QPushButton("─")
        self._btn_max = QPushButton("□")
        self._btn_close = QPushButton("✕")
        for btn in (self._btn_min, self._btn_max, self._btn_close):
            btn.setFixedSize(36, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_min.setStyleSheet(btn_style)
        self._btn_max.setStyleSheet(btn_style)
        self._btn_close.setStyleSheet(close_style)

        self._btn_min.clicked.connect(self._on_minimize)
        self._btn_max.clicked.connect(self._on_maximize)
        self._btn_close.clicked.connect(self._on_close)

        layout.addWidget(self._btn_min)
        layout.addWidget(self._btn_max)
        layout.addWidget(self._btn_close)

        self.setStyleSheet(
            f"background: rgba(15, 15, 26, 0.95); border-bottom: 1px solid {theme.GLASS_BORDER};"
        )

    # ── Dragging ─────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._on_maximize()

    # ── Button actions ───────────────────────────────────────

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._btn_max.setText("□")
        else:
            win.showMaximized()
            self._btn_max.setText("❐")

    def _on_close(self):
        self.window().close()
