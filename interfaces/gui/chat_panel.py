"""
Chat panel — glassmorphism message bubbles, input bar, and auto-scroll.
"""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QFrame, QGraphicsOpacityEffect,
)
from PySide6.QtGui import QFont, QKeyEvent

from interfaces.gui import theme


class ChatBubble(QFrame):
    """Single chat message bubble with fade-in animation."""

    def __init__(self, text: str, is_user: bool, parent: QWidget | None = None, *,
                 metadata: dict | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMaximumWidth(theme.BUBBLE_MAX_WIDTH)

        self._is_user = is_user
        self._metadata = metadata or {}

        if is_user:
            bg = theme.USER_BUBBLE_BG
            border = theme.USER_BUBBLE_BORDER
        else:
            bg = theme.BOT_BUBBLE_BG
            border = theme.BOT_BUBBLE_BORDER

        self.setStyleSheet(f"""
            ChatBubble {{
                background: {bg};
                border: 1px solid {border};
                border-radius: {theme.BORDER_RADIUS}px;
                padding: 10px 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(self._render(text))
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
        self._label.setOpenExternalLinks(True)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self._label)

        ts = QLabel(datetime.now().strftime("%H:%M"))
        ts.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; background: transparent; border: none;")
        ts.setAlignment(Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(ts)

        # ── Expandable detail section (bot messages only) ─────
        if not is_user and self._metadata:
            self._detail_frame = QFrame()
            self._detail_frame.setStyleSheet(
                f"background: rgba(255,255,255,0.03); border: none; "
                f"border-top: 1px solid {theme.GLASS_BORDER}; padding: 6px 4px;"
            )
            self._detail_frame.hide()
            detail_layout = QVBoxLayout(self._detail_frame)
            detail_layout.setContentsMargins(4, 4, 4, 0)
            detail_layout.setSpacing(2)
            for key, val in self._metadata.items():
                row = QLabel(f"<b>{html.escape(str(key))}:</b> {html.escape(str(val))}")
                row.setWordWrap(True)
                row.setTextFormat(Qt.TextFormat.RichText)
                row.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent; border: none;")
                detail_layout.addWidget(row)
            layout.addWidget(self._detail_frame)

            toggle = QPushButton("▸ details")
            toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle.setFlat(True)
            toggle.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: 10px; text-align: left; "
                f"background: transparent; border: none; padding: 0;"
            )
            toggle.clicked.connect(lambda: self._toggle_detail(toggle))
            layout.addWidget(toggle)
        else:
            self._detail_frame = None

        # Fade-in animation
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _toggle_detail(self, btn: QPushButton):
        if self._detail_frame is None:
            return
        visible = self._detail_frame.isVisible()
        self._detail_frame.setVisible(not visible)
        btn.setText("▾ details" if not visible else "▸ details")

    @staticmethod
    def _render(text: str) -> str:
        """Convert plain text to displayable HTML, supporting **bold** and `code`."""
        safe = html.escape(text)
        # Bold: **text**
        import re
        safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
        # Inline code: `text`
        safe = re.sub(r'`(.+?)`', r'<code style="background:rgba(255,255,255,0.08);border-radius:3px;padding:1px 4px;">\1</code>', safe)
        # Newlines
        safe = safe.replace('\n', '<br>')
        return safe


class StreamingBubble(QFrame):
    """Bot bubble that reveals tokens progressively (cinematic streaming)."""

    stream_finished = Signal()

    # Target ~25ms per token for cinematic feel
    _TOKEN_INTERVAL_MS = 25

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMaximumWidth(theme.BUBBLE_MAX_WIDTH)
        self.setStyleSheet(f"""
            StreamingBubble {{
                background: {theme.BOT_BUBBLE_BG};
                border: 1px solid {theme.BOT_BUBBLE_BORDER};
                border-radius: {theme.BORDER_RADIUS}px;
                padding: 10px 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self._label)

        self._ts_label = QLabel(datetime.now().strftime("%H:%M"))
        self._ts_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; background: transparent; border: none;"
        )
        self._ts_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._ts_label)

        # Token queue and reveal timer
        self._tokens: list[str] = []
        self._revealed: list[str] = []
        self._full_text = ""
        self._finished = False

        self._timer = QTimer(self)
        self._timer.setInterval(self._TOKEN_INTERVAL_MS)
        self._timer.timeout.connect(self._reveal_next)

        # Fade in
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def append_token(self, token: str):
        """Add a token chunk to the streaming queue."""
        self._tokens.append(token)
        if not self._timer.isActive():
            self._timer.start()

    def finish(self):
        """Signal that no more tokens are coming."""
        self._finished = True
        # If timer is idle and tokens are empty, emit immediately
        if not self._tokens and not self._timer.isActive():
            self.stream_finished.emit()

    def _reveal_next(self):
        if self._tokens:
            chunk = self._tokens.pop(0)
            self._revealed.append(chunk)
            self._label.setText(ChatBubble._render("".join(self._revealed)))
        elif self._finished:
            self._timer.stop()
            self.stream_finished.emit()
        else:
            # No tokens yet but not finished; keep timer running
            pass

    @property
    def full_text(self) -> str:
        return "".join(self._revealed)


class TypingIndicator(QFrame):
    """Animated 'Quarky is typing...' indicator."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            TypingIndicator {{
                background: {theme.BOT_BUBBLE_BG};
                border: 1px solid {theme.BOT_BUBBLE_BORDER};
                border-radius: {theme.BORDER_RADIUS}px;
                padding: 8px 14px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Quarky is thinking...")
        lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-style: italic; background: transparent; border: none;")
        layout.addWidget(lbl)
        self.setMaximumWidth(220)
        self.hide()


class ChatPanel(QWidget):
    """Full chat panel: scrollable message area + input bar."""

    message_sent = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Scroll area with messages ─────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._container = QWidget()
        self._msg_layout = QVBoxLayout(self._container)
        self._msg_layout.setContentsMargins(16, 16, 16, 16)
        self._msg_layout.setSpacing(10)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._container)
        main_layout.addWidget(self._scroll, 1)

        self._active_stream: StreamingBubble | None = None

        # Typing indicator
        self._typing = TypingIndicator()
        self._msg_layout.addWidget(self._typing, alignment=Qt.AlignmentFlag.AlignLeft)

        # ── Input bar ─────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.GLASS_BG};
                border-top: 1px solid {theme.GLASS_BORDER};
            }}
        """)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message...")
        self._input.setFixedHeight(theme.INPUT_HEIGHT)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                border: 1px solid {theme.GLASS_BORDER};
                border-radius: {theme.BORDER_RADIUS}px;
                padding: 0 14px;
                color: {theme.TEXT_PRIMARY};
                font-size: {theme.FONT_SIZE_NORMAL}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT};
            }}
        """)
        self._input.returnPressed.connect(self._send)
        input_layout.addWidget(self._input, 1)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(theme.INPUT_HEIGHT, theme.INPUT_HEIGHT)
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06);
                border: 1px solid {theme.GLASS_BORDER};
                border-radius: {theme.INPUT_HEIGHT // 2}px;
                font-size: 18px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); }}
        """)
        input_layout.addWidget(self._mic_btn)

        self._send_btn = QPushButton("▶")
        self._send_btn.setFixedSize(theme.INPUT_HEIGHT, theme.INPUT_HEIGHT)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme.ACCENT};
                border: none;
                border-radius: {theme.INPUT_HEIGHT // 2}px;
                color: white;
                font-size: 18px;
            }}
            QPushButton:hover {{ background: {theme.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: {theme.ACCENT_PRESSED}; }}
        """)
        self._send_btn.clicked.connect(self._send)
        input_layout.addWidget(self._send_btn)

        main_layout.addWidget(input_bar)

    # ── Public API ───────────────────────────────────────────

    def add_user_message(self, text: str):
        self._add_bubble(text, is_user=True)

    def add_bot_message(self, text: str, *, metadata: dict | None = None):
        self._add_bubble(text, is_user=False, metadata=metadata)

    def start_streaming(self) -> StreamingBubble:
        """Insert a streaming bubble and return it. Caller feeds tokens via append_token()."""
        self.show_typing(False)
        bubble = StreamingBubble(self._container)
        self._active_stream = bubble
        idx = self._msg_layout.count() - 2
        if idx < 0:
            idx = 0
        self._msg_layout.insertWidget(idx, bubble, alignment=Qt.AlignmentFlag.AlignLeft)
        bubble.stream_finished.connect(self._on_stream_finished)
        self._scroll_to_bottom()
        return bubble

    def _on_stream_finished(self):
        self._active_stream = None
        self._scroll_to_bottom()

    def show_typing(self, visible: bool = True):
        self._typing.setVisible(visible)
        if visible:
            self._scroll_to_bottom()

    @property
    def mic_button(self) -> QPushButton:
        return self._mic_btn

    # ── Internals ─────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool, *, metadata: dict | None = None):
        bubble = ChatBubble(text, is_user, self._container, metadata=metadata)
        alignment = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
        # Insert before the typing indicator
        idx = self._msg_layout.count() - 2  # before stretch-end and typing
        if idx < 0:
            idx = 0
        self._msg_layout.insertWidget(idx, bubble, alignment=alignment)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll to bottom with a short delay to let layout settle."""
        QTimer.singleShot(30, self._do_scroll)

    def _do_scroll(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.message_sent.emit(text)
