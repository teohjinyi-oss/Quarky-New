"""
Full-screen voice overlay — Google-Assistant-style animated orb + live transcription.
Triggered by wake word or mic button. Tap anywhere to dismiss.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QBrush, QPen, QFont,
    QPaintEvent, QMouseEvent,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect,
)

from AppStudio.GUI import theme


class VoiceOrb(QWidget):
    """Animated circle that reacts to audio levels."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self._level: float = 0.0  # 0.0 – 1.0
        self._phase: float = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(33)  # ~30 fps

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def set_level(self, level: float):
        self._level = max(0.0, min(1.0, level))

    def _tick(self):
        self._phase += 0.08
        self.update()

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        base_r = 50 + self._level * 25
        pulse = math.sin(self._phase) * 5 * (0.3 + self._level)
        r = base_r + pulse

        # Outer glow
        for i in range(3):
            glow_r = r + 15 + i * 12
            alpha = int(30 - i * 10)
            glow_color = QColor(124, 92, 252, alpha)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow_color))
            p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # Main orb with gradient
        gradient = QRadialGradient(cx, cy, r)
        gradient.setColorAt(0.0, QColor(155, 125, 255, 200))
        gradient.setColorAt(0.6, QColor(124, 92, 252, 180))
        gradient.setColorAt(1.0, QColor(99, 68, 212, 140))
        p.setBrush(QBrush(gradient))
        p.setPen(QPen(QColor(200, 180, 255, 60), 1.5))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        p.end()


class VoiceOverlay(QWidget):
    """Full-screen translucent overlay for voice interaction."""

    dismissed = Signal()
    transcription_ready = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background: rgba(10, 10, 20, 0.88);")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        # Status label
        self._status = QLabel("Listening...")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"""
            color: {theme.TEXT_SECONDARY};
            font-size: 16px;
            font-weight: 500;
            background: transparent;
        """)
        layout.addWidget(self._status)

        # Animated orb
        self._orb = VoiceOrb()
        layout.addWidget(self._orb, alignment=Qt.AlignmentFlag.AlignCenter)

        # Transcription
        self._transcript = QLabel("")
        self._transcript.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._transcript.setWordWrap(True)
        self._transcript.setMaximumWidth(500)
        self._transcript.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
            font-size: 20px;
            font-weight: 400;
            background: transparent;
        """)
        layout.addWidget(self._transcript)

        # Response
        self._response = QLabel("")
        self._response.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._response.setWordWrap(True)
        self._response.setMaximumWidth(500)
        self._response.setStyleSheet(f"""
            color: {theme.ACCENT};
            font-size: 18px;
            background: transparent;
        """)
        layout.addWidget(self._response)

        # Hint
        hint = QLabel("Tap anywhere to dismiss")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; background: transparent;")
        layout.addWidget(hint)

        # Fade-in effect
        self._fade_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fade_effect)

    # ── Public API ───────────────────────────────────────────

    def activate(self):
        """Show the overlay and start the orb animation."""
        self.show()
        self.raise_()
        self._status.setText("Listening...")
        self._transcript.setText("")
        self._response.setText("")
        self._orb.start()

        self._fade_effect.setOpacity(0.0)
        anim = QPropertyAnimation(self._fade_effect, b"opacity")
        anim.setDuration(200)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._fade_anim = anim  # prevent GC

    def deactivate(self):
        """Fade out and hide."""
        self._orb.stop()
        anim = QPropertyAnimation(self._fade_effect, b"opacity")
        anim.setDuration(200)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.hide)
        anim.start()
        self._fade_anim = anim

    def set_audio_level(self, level: float):
        self._orb.set_level(level)

    def set_status(self, text: str):
        self._status.setText(text)

    def set_transcription(self, text: str):
        self._transcript.setText(text)

    def set_response(self, text: str):
        self._response.setText(text)
        self._status.setText("Quarky says:")

    # ── Events ───────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        self.deactivate()
        self.dismissed.emit()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
