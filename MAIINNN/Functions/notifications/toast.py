"""
Notifications: Toast

Cross-platform desktop toast notifications.
Uses plyer on Windows/macOS/Linux, falls back to print.
"""

from __future__ import annotations

_PLYER_AVAILABLE = False
try:
    from plyer import notification as plyer_notification  # type: ignore[import-untyped]
    _PLYER_AVAILABLE = True
except ImportError:
    pass


class ToastNotifier:
    """Show native desktop toast / banner notifications."""

    def __init__(self, app_name: str = "Quarky Ai"):
        self._app = app_name

    @property
    def available(self) -> bool:
        return _PLYER_AVAILABLE

    def show(self, title: str, message: str, timeout: int = 5):
        """Display a toast notification."""
        if _PLYER_AVAILABLE:
            plyer_notification.notify(
                title=title,
                message=message,
                app_name=self._app,
                timeout=timeout,
            )
        else:
            # fallback for environments without plyer
            print(f"[{self._app}] {title}: {message}")
