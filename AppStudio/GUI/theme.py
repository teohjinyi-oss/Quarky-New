"""
GUI Theme: Glassmorphism color palette, fonts, and shared QSS constants.
"""

from __future__ import annotations

# ── Colour palette ───────────────────────────────────────────

# Primary accent (Quarky AI blue-violet)
ACCENT = "#7C5CFC"
ACCENT_HOVER = "#9B7DFF"
ACCENT_PRESSED = "#6344D4"

# Glass surface
GLASS_BG = "rgba(30, 30, 46, 0.82)"
GLASS_BORDER = "rgba(255, 255, 255, 0.08)"
GLASS_HIGHLIGHT = "rgba(255, 255, 255, 0.04)"

# Text
TEXT_PRIMARY = "#E0E0E8"
TEXT_SECONDARY = "#A0A0B8"
TEXT_MUTED = "#707088"

# Chat bubbles
USER_BUBBLE_BG = "rgba(124, 92, 252, 0.35)"
USER_BUBBLE_BORDER = "rgba(124, 92, 252, 0.45)"
BOT_BUBBLE_BG = "rgba(255, 255, 255, 0.06)"
BOT_BUBBLE_BORDER = "rgba(255, 255, 255, 0.10)"

# Background (deep dark)
WINDOW_BG = "#0F0F1A"
SIDEBAR_BG = "rgba(18, 18, 30, 0.92)"

# Status
SUCCESS = "#4ADE80"
WARNING = "#FACC15"
ERROR = "#F87171"

# ── Fonts ────────────────────────────────────────────────────

FONT_FAMILY = "Segoe UI, Helvetica Neue, Arial, sans-serif"
FONT_SIZE_NORMAL = 14
FONT_SIZE_SMALL = 12
FONT_SIZE_LARGE = 18
FONT_SIZE_TITLE = 24

# ── Dimensions ───────────────────────────────────────────────

SIDEBAR_WIDTH = 280
SIDEBAR_COLLAPSED_WIDTH = 48
BORDER_RADIUS = 12
INPUT_HEIGHT = 48
BUBBLE_MAX_WIDTH = 640
TITLE_BAR_HEIGHT = 38

# ── Global QSS ──────────────────────────────────────────────

GLOBAL_QSS = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_NORMAL}px;
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.12);
    min-height: 30px;
    border-radius: 3px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QToolTip {{
    background: {GLASS_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {GLASS_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
}}
"""
