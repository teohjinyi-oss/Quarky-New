"""
In-app glass toast notifications — slide in from top-right, auto-dismiss.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect,
)

from AppStudio.GUI import theme


class Toast(QWidget):
    """A single notification toast with auto-dismiss."""

    def __init__(
        self,
        title: str,
        body: str,
        level: str = "info",           # info | success | warning | error
        duration_ms: int = 4000,
        actions: list[tuple[str, Any]] | None = None,  # [(label, callback), ...]
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        accent_map = {
            "info": theme.ACCENT,
            "success": theme.SUCCESS,
            "warning": theme.WARNING,
            "error": theme.ERROR,
        }
        accent = accent_map.get(level, theme.ACCENT)

        self.setStyleSheet(f"""
            Toast {{
                background: {theme.GLASS_BG};
                border: 1px solid {theme.GLASS_BORDER};
                border-left: 3px solid {accent};
                border-radius: {theme.BORDER_RADIUS}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-weight: 600; font-size: 13px; background: transparent; border: none;")
        header.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {theme.TEXT_MUTED}; font-size: 11px; }}
            QPushButton:hover {{ color: {theme.TEXT_PRIMARY}; }}
        """)
        close_btn.clicked.connect(self._dismiss)
        header.addWidget(close_btn)
        layout.addLayout(header)

        body_lbl = QLabel(body)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(body_lbl)

        # Action buttons (e.g. "Show Processes", "Ignore")
        if actions:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            for label, callback in actions:
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(124, 92, 252, 0.2);
                        border: 1px solid {theme.ACCENT};
                        border-radius: 4px;
                        padding: 3px 10px;
                        color: {theme.ACCENT};
                        font-size: 11px;
                    }}
                    QPushButton:hover {{ background: rgba(124, 92, 252, 0.35); }}
                """)
                btn.clicked.connect(callback)
                btn.clicked.connect(self._dismiss)
                btn_row.addWidget(btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

        # Opacity for fade effect
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.setInterval(duration_ms)
        self._dismiss_timer.timeout.connect(self._dismiss)

    def show_animated(self):
        self.show()
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._show_anim = anim
        self._dismiss_timer.start()

    def _dismiss(self):
        self._dismiss_timer.stop()
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(200)
        anim.setEndValue(0.0)
        anim.finished.connect(self._remove)
        anim.start()
        self._hide_anim = anim

    def _remove(self):
        self.hide()
        self.deleteLater()


class ToastContainer(QWidget):
    """
    Manages stacking of toasts in the top-right corner of the parent.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 8, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

    def push(self, title: str, body: str, level: str = "info",
             duration_ms: int = 4000, actions: list[tuple[str, Any]] | None = None):
        toast = Toast(title, body, level, duration_ms, actions, self)
        self.layout().addWidget(toast)
        toast.show_animated()

    def reposition(self, parent_size):
        """Move to top-right of parent."""
        self.setGeometry(
            parent_size.width() - 340, 50,
            340, parent_size.height() - 60,
        )
