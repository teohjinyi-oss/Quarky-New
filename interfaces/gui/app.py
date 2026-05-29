"""
Quarky AI — Desktop App Entry Point

Launch the PySide6 GUI application. This is what the .exe runs.
"""

from __future__ import annotations

import sys


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Quarky AI")
    app.setOrganizationName("QuarkyAI")

    from interfaces.gui import theme
    app.setStyleSheet(theme.GLOBAL_QSS)

    from interfaces.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
