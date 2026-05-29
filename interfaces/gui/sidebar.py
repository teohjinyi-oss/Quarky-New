"""
Collapsible tabbed sidebar — Chat History, Memory, Settings, System Monitor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QListWidget, QListWidgetItem, QLineEdit,
    QFrame, QScrollArea, QComboBox, QCheckBox, QSlider,
)

from interfaces.gui import theme


class SidebarTab(QPushButton):
    """A single icon-label tab button in the sidebar."""

    def __init__(self, icon: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon = icon
        self._label_text = label
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def set_collapsed(self, collapsed: bool):
        self.setText(self._icon if collapsed else f" {self._icon}  {self._label_text}")

    def _update_style(self):
        bg = f"rgba(124, 92, 252, 0.18)" if self._selected else "transparent"
        left_bar = f"border-left: 3px solid {theme.ACCENT};" if self._selected else "border-left: 3px solid transparent;"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                {left_bar}
                border: none;
                border-radius: 0;
                text-align: left;
                padding: 0 12px;
                font-size: 13px;
                color: {theme.TEXT_PRIMARY if self._selected else theme.TEXT_SECONDARY};
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.06); }}
        """)
        self.set_collapsed(False)


# ── Tab pages ────────────────────────────────────────────────

class ChatHistoryPage(QWidget):
    """List of recent conversations with search."""

    conversation_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        search = QLineEdit()
        search.setPlaceholderText("Search conversations...")
        search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                border: 1px solid {theme.GLASS_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(search)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
            QListWidget::item:selected {{
                background: rgba(124, 92, 252, 0.18);
            }}
        """)
        layout.addWidget(self._list, 1)

        # Placeholder items
        self._list.addItem("Today — 3 messages")
        self._list.addItem("Yesterday — 12 messages")

    def add_conversation(self, label: str):
        self._list.insertItem(0, label)


class MemoryBrowserPage(QWidget):
    """Browse what Quarky knows — search and delete facts."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        search = QLineEdit()
        search.setPlaceholderText("Search memory...")
        search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                border: 1px solid {theme.GLASS_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(search)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; }}
            QListWidget::item {{ padding: 6px; color: {theme.TEXT_PRIMARY}; border-radius: 4px; }}
            QListWidget::item:hover {{ background: rgba(255,255,255,0.06); }}
        """)
        layout.addWidget(self._list, 1)

        info = QLabel("Facts and knowledge Quarky has learned")
        info.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)


class SettingsPage(QWidget):
    """Theme, voice, habit, privacy, and integration settings."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # Voice settings
        layout.addWidget(self._section_header("Voice"))
        wake_row = self._label_toggle("Wake word detection", True)
        layout.addWidget(wake_row)
        tts_row = self._label_toggle("Text-to-speech responses", True)
        layout.addWidget(tts_row)

        # Appearance
        layout.addWidget(self._section_header("Appearance"))
        layout.addWidget(QLabel("Accent colour"))

        # Privacy
        layout.addWidget(self._section_header("Privacy"))
        mem_row = self._label_toggle("Store conversation history", True)
        layout.addWidget(mem_row)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @staticmethod
    def _section_header(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 15px; font-weight: 600; padding-top: 4px;")
        return lbl

    @staticmethod
    def _label_toggle(text: str, checked: bool) -> QWidget:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        hl.addWidget(lbl, 1)
        cb = QCheckBox()
        cb.setChecked(checked)
        hl.addWidget(cb)
        return row


class SystemMonitorPage(QWidget):
    """Real-time CPU/RAM mini-charts and alerts."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(self._metric_card("CPU", "—"))
        layout.addWidget(self._metric_card("RAM", "—"))
        layout.addWidget(self._metric_card("Disk", "—"))
        layout.addStretch()

        self._cpu_label: QLabel | None = None
        self._ram_label: QLabel | None = None

    def _metric_card(self, name: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {theme.GLASS_BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        hl = QHBoxLayout(card)
        title = QLabel(name)
        title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 13px; background: transparent; border: none;")
        val = QLabel(value)
        val.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 18px; font-weight: 600; background: transparent; border: none;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        hl.addWidget(title)
        hl.addWidget(val, 1)
        if name == "CPU":
            self._cpu_label = val
        elif name == "RAM":
            self._ram_label = val
        return card

    def update_metrics(self, cpu: float, ram: float, disk: float = 0.0):
        if self._cpu_label:
            self._cpu_label.setText(f"{cpu:.0f}%")
        if self._ram_label:
            self._ram_label.setText(f"{ram:.0f}%")


# ── Main sidebar ─────────────────────────────────────────────

class Sidebar(QWidget):
    """Collapsible left sidebar with tabbed navigation."""

    voice_button_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._collapsed = False
        self.setFixedWidth(theme.SIDEBAR_WIDTH)

        self.setStyleSheet(f"""
            Sidebar {{
                background: {theme.SIDEBAR_BG};
                border-right: 1px solid {theme.GLASS_BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Collapse button
        self._toggle_btn = QPushButton("◀")
        self._toggle_btn.setFixedSize(32, 28)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {theme.TEXT_MUTED};
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {theme.TEXT_PRIMARY}; }}
        """)
        self._toggle_btn.clicked.connect(self.toggle_collapsed)
        header = QHBoxLayout()
        header.addStretch()
        header.addWidget(self._toggle_btn)
        header.setContentsMargins(0, 0, 6, 4)
        layout.addLayout(header)

        # Tab buttons
        self._tabs: list[SidebarTab] = []
        tab_data = [
            ("💬", "Chat History"),
            ("🧠", "Memory"),
            ("⚙️", "Settings"),
            ("📊", "Monitor"),
        ]
        for i, (icon, label) in enumerate(tab_data):
            tab = SidebarTab(icon, label)
            tab.clicked.connect(lambda checked=False, idx=i: self._select_tab(idx))
            self._tabs.append(tab)
            layout.addWidget(tab)

        layout.addSpacing(8)

        # Stacked pages
        self._stack = QStackedWidget()
        self.history_page = ChatHistoryPage()
        self.memory_page = MemoryBrowserPage()
        self.settings_page = SettingsPage()
        self.monitor_page = SystemMonitorPage()

        self._stack.addWidget(self.history_page)
        self._stack.addWidget(self.memory_page)
        self._stack.addWidget(self.settings_page)
        self._stack.addWidget(self.monitor_page)

        layout.addWidget(self._stack, 1)

        # Select first tab
        self._select_tab(0)

    def toggle_collapsed(self):
        self._collapsed = not self._collapsed
        target_w = theme.SIDEBAR_COLLAPSED_WIDTH if self._collapsed else theme.SIDEBAR_WIDTH
        self._toggle_btn.setText("▶" if self._collapsed else "◀")
        self._stack.setVisible(not self._collapsed)
        for tab in self._tabs:
            tab.set_collapsed(self._collapsed)
        self.setFixedWidth(target_w)

    def _select_tab(self, idx: int):
        for i, tab in enumerate(self._tabs):
            tab.set_selected(i == idx)
        self._stack.setCurrentIndex(idx)
