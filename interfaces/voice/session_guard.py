"""
Voice: Session Guard — Windows session lock detection.

Returns True when the desktop session is unlocked (user can interact).
On non-Windows or if detection fails, defaults to unlocked (True).
"""

from __future__ import annotations

import sys


def is_session_unlocked() -> bool:
    """Check whether the Windows desktop session is currently unlocked."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        # If the foreground window handle is 0, the desktop is locked
        # (or the secure desktop is active).
        hwnd = user32.GetForegroundWindow()
        return hwnd != 0
    except Exception:
        return True  # fail-open: assume unlocked if detection breaks
