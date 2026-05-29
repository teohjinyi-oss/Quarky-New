"""
Action System: System Control

Volume, brightness, window management, and system power controls.
All gated through safety.py — every action passes the safety check.
Undo support for reversible actions (volume/brightness).
"""

import subprocess
import ctypes
from typing import Any

from MAIINNN.Decision.action_resolver import ActionRequest
from MAIINNN.Functions.result_reporter import ActionResult, UndoInfo


# ─── State tracking for undo ────────────────────────────────
_previous_volume: float | None = None
_previous_brightness: int | None = None


def execute(action_request: ActionRequest) -> ActionResult:
    """
    Main handler for system_control actions.
    Routes to the appropriate sub-handler based on target keywords.
    """
    target = action_request.target.lower().strip()
    command = action_request.command.lower()
    combined = target + " " + command

    if "volume" in combined or "mute" in combined or "unmute" in combined:
        return _handle_volume(combined, action_request.parameters)

    if "brightness" in combined:
        return _handle_brightness(combined, action_request.parameters)

    if any(w in combined for w in ("minimize", "maximize", "close window", "restore",
                                       "split", "arrange", "snap", "move to monitor",
                                       "minimize all", "focus")):
        return _handle_window(combined)

    if "shutdown" in combined:
        return _handle_shutdown()

    if "restart" in combined or "reboot" in combined:
        return _handle_restart()

    if "lock" in combined:
        return _handle_lock()

    if "sleep" in combined:
        return _handle_sleep()

    return ActionResult(
        success=False,
        message=f"Unknown system control command: {target}",
    )


# ═══════════════════════════════════════════════════════════════
#  Volume Control (pycaw)
# ═══════════════════════════════════════════════════════════════

def _get_volume_interface() -> Any:
    """Get the Windows volume interface via pycaw."""
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # type: ignore[union-attr]
    return interface.QueryInterface(IAudioEndpointVolume)


def _handle_volume(text: str, params: dict[str, Any]) -> ActionResult:
    """Handle volume-related commands."""
    global _previous_volume

    try:
        vol = _get_volume_interface()
        current = vol.GetMasterVolumeLevelScalar()
        _previous_volume = current

        if "mute" in text and "unmute" not in text:
            vol.SetMute(1, None)
            return ActionResult(
                success=True,
                message="Volume muted.",
                undo_info=UndoInfo(
                    undo_type="volume_revert",
                    previous_value={"muted": False},
                    description="Unmute volume",
                ),
            )

        if "unmute" in text:
            vol.SetMute(0, None)
            return ActionResult(
                success=True,
                message="Volume unmuted.",
                undo_info=UndoInfo(
                    undo_type="volume_revert",
                    previous_value={"muted": True},
                    description="Mute volume",
                ),
            )

        # Extract level from params or text
        level = params.get("level")
        if level is None:
            level = _extract_number(text)

        if level is not None:
            level = max(0, min(100, int(level)))
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return ActionResult(
                success=True,
                message=f"Volume set to {level}%.",
                undo_info=UndoInfo(
                    undo_type="volume_revert",
                    previous_value={"level": round(current * 100)},
                    description=f"Revert volume to {round(current * 100)}%",
                ),
            )

        if "up" in text or "increase" in text or "raise" in text:
            new_level = min(1.0, current + 0.1)
            vol.SetMasterVolumeLevelScalar(new_level, None)
            return ActionResult(
                success=True,
                message=f"Volume increased to {round(new_level * 100)}%.",
                undo_info=UndoInfo(
                    undo_type="volume_revert",
                    previous_value={"level": round(current * 100)},
                    description=f"Revert volume to {round(current * 100)}%",
                ),
            )

        if "down" in text or "decrease" in text or "lower" in text:
            new_level = max(0.0, current - 0.1)
            vol.SetMasterVolumeLevelScalar(new_level, None)
            return ActionResult(
                success=True,
                message=f"Volume decreased to {round(new_level * 100)}%.",
                undo_info=UndoInfo(
                    undo_type="volume_revert",
                    previous_value={"level": round(current * 100)},
                    description=f"Revert volume to {round(current * 100)}%",
                ),
            )

        return ActionResult(
            success=True,
            message=f"Current volume: {round(current * 100)}%.",
        )

    except ImportError:
        return ActionResult(
            success=False,
            message="Volume control unavailable. Install pycaw: pip install pycaw comtypes",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Volume control error: {e}")


# ═══════════════════════════════════════════════════════════════
#  Brightness Control
# ═══════════════════════════════════════════════════════════════

def _handle_brightness(text: str, params: dict[str, Any]) -> ActionResult:
    """Handle brightness-related commands."""
    global _previous_brightness

    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        _previous_brightness = current

        level = params.get("level")
        if level is None:
            level = _extract_number(text)

        if level is not None:
            level = max(0, min(100, int(level)))
            sbc.set_brightness(level)
            return ActionResult(
                success=True,
                message=f"Brightness set to {level}%.",
                undo_info=UndoInfo(
                    undo_type="brightness_revert",
                    previous_value=current,
                    description=f"Revert brightness to {current}%",
                ),
            )

        if "up" in text or "increase" in text:
            new_level = min(100, current + 10)
            sbc.set_brightness(new_level)
            return ActionResult(
                success=True,
                message=f"Brightness increased to {new_level}%.",
                undo_info=UndoInfo(
                    undo_type="brightness_revert",
                    previous_value=current,
                    description=f"Revert brightness to {current}%",
                ),
            )

        if "down" in text or "decrease" in text:
            new_level = max(0, current - 10)
            sbc.set_brightness(new_level)
            return ActionResult(
                success=True,
                message=f"Brightness decreased to {new_level}%.",
                undo_info=UndoInfo(
                    undo_type="brightness_revert",
                    previous_value=current,
                    description=f"Revert brightness to {current}%",
                ),
            )

        return ActionResult(
            success=True,
            message=f"Current brightness: {current}%.",
        )

    except ImportError:
        return ActionResult(
            success=False,
            message="Brightness control unavailable. Install: pip install screen-brightness-control",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Brightness control error: {e}")


# ═══════════════════════════════════════════════════════════════
#  Window Management (pygetwindow)
# ═══════════════════════════════════════════════════════════════

def _handle_window(text: str) -> ActionResult:
    """Handle window management: minimize/maximize/close/restore/split/arrange."""
    try:
        import pygetwindow as gw

        # ── Minimize-all-except ─────────────────────────────
        if "minimize all" in text:
            # Find an app name to keep (e.g. "minimize all except chrome")
            keep = ""
            if "except" in text:
                keep = text.split("except", 1)[1].strip()
            all_wins = gw.getAllWindows()
            count = 0
            for w in all_wins:
                if not w.title or w.isMinimized:
                    continue
                if keep and keep.lower() in w.title.lower():
                    continue
                try:
                    w.minimize()
                    count += 1
                except Exception:
                    pass
            msg = f"Minimized {count} windows"
            if keep:
                msg += f" (kept '{keep}')"
            return ActionResult(success=True, message=msg + ".")

        # ── Split screen ────────────────────────────────────
        if "split" in text or "snap" in text or "arrange" in text:
            return _split_screen(text, gw)

        # ── Single-window commands ──────────────────────────
        active = gw.getActiveWindow()
        if active is None:
            return ActionResult(success=False, message="No active window found.")

        title = active.title

        if "minimize" in text:
            active.minimize()
            return ActionResult(
                success=True, message=f"Minimized: {title}")

        if "maximize" in text:
            active.maximize()
            return ActionResult(
                success=True, message=f"Maximized: {title}")

        if "restore" in text:
            active.restore()
            return ActionResult(
                success=True, message=f"Restored: {title}")

        if "close" in text:
            active.close()
            return ActionResult(
                success=True, message=f"Closed: {title}")

        return ActionResult(success=False, message="Unknown window command.")

    except ImportError:
        return ActionResult(
            success=False,
            message="Window management unavailable. Install: pip install pygetwindow",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Window management error: {e}")


def _split_screen(text: str, gw: Any) -> ActionResult:
    """
    Split-screen arrangement.
    Supports: "split chrome and vscode", "snap left chrome", "snap right vscode"
    """
    import ctypes as _ct
    user32 = _ct.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    # Try to parse "split <app1> and <app2>"
    if " and " in text:
        parts = text.split(" and ")
        # Extract app names from the surrounding text
        left_name = parts[0].rsplit(maxsplit=1)[-1].strip()
        right_name = parts[1].split(maxsplit=1)[0].strip()
        left_win = _find_window_by_name(gw, left_name)
        right_win = _find_window_by_name(gw, right_name)
        if left_win and right_win:
            left_win.restore()
            left_win.moveTo(0, 0)
            left_win.resizeTo(screen_w // 2, screen_h)
            right_win.restore()
            right_win.moveTo(screen_w // 2, 0)
            right_win.resizeTo(screen_w // 2, screen_h)
            return ActionResult(
                success=True,
                message=f"Split screen: {left_win.title} | {right_win.title}")
        missing = []
        if not left_win:
            missing.append(left_name)
        if not right_win:
            missing.append(right_name)
        return ActionResult(
            success=False,
            message=f"Could not find window(s): {', '.join(missing)}")

    # Snap left/right for a single window
    if "left" in text or "right" in text:
        active = gw.getActiveWindow()
        if active is None:
            return ActionResult(success=False, message="No active window to snap.")
        active.restore()
        half_w = screen_w // 2
        if "left" in text:
            active.moveTo(0, 0)
            active.resizeTo(half_w, screen_h)
            return ActionResult(success=True, message=f"Snapped {active.title} to left half.")
        else:
            active.moveTo(half_w, 0)
            active.resizeTo(half_w, screen_h)
            return ActionResult(success=True, message=f"Snapped {active.title} to right half.")

    return ActionResult(success=False, message="Specify apps to split, e.g. 'split Chrome and VS Code'.")


def _find_window_by_name(gw: Any, name: str) -> Any:
    """Find a window whose title contains the given name (case-insensitive)."""
    name_lower = name.lower()
    for w in gw.getAllWindows():
        if w.title and name_lower in w.title.lower():
            return w
    return None


# ═══════════════════════════════════════════════════════════════
#  Power Controls (CRITICAL risk — gated)
# ═══════════════════════════════════════════════════════════════

def _handle_shutdown() -> ActionResult:
    """Shutdown the computer. CRITICAL risk."""
    try:
        subprocess.Popen(["shutdown", "/s", "/t", "5"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ActionResult(
            success=True,
            message="System will shut down in 5 seconds. Run 'shutdown /a' to cancel.",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Shutdown failed: {e}")


def _handle_restart() -> ActionResult:
    """Restart the computer. CRITICAL risk."""
    try:
        subprocess.Popen(["shutdown", "/r", "/t", "5"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ActionResult(
            success=True,
            message="System will restart in 5 seconds. Run 'shutdown /a' to cancel.",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Restart failed: {e}")


def _handle_lock() -> ActionResult:
    """Lock the workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return ActionResult(success=True, message="Workstation locked.")
    except Exception as e:
        return ActionResult(success=False, message=f"Lock failed: {e}")


def _handle_sleep() -> ActionResult:
    """Put the computer to sleep."""
    try:
        subprocess.Popen(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ActionResult(success=True, message="System entering sleep mode.")
    except Exception as e:
        return ActionResult(success=False, message=f"Sleep failed: {e}")


# ═══════════════════════════════════════════════════════════════
#  Undo support
# ═══════════════════════════════════════════════════════════════

def undo_volume() -> ActionResult:
    """Revert volume to the previous state."""
    if _previous_volume is None:
        return ActionResult(success=False, message="No previous volume to revert to.")
    try:
        vol = _get_volume_interface()
        vol.SetMasterVolumeLevelScalar(_previous_volume, None)
        return ActionResult(
            success=True,
            message=f"Volume reverted to {round(_previous_volume * 100)}%.",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Volume undo failed: {e}")


def undo_brightness() -> ActionResult:
    """Revert brightness to the previous state."""
    if _previous_brightness is None:
        return ActionResult(success=False, message="No previous brightness to revert to.")
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(_previous_brightness)
        return ActionResult(
            success=True,
            message=f"Brightness reverted to {_previous_brightness}%.",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Brightness undo failed: {e}")


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _extract_number(text: str) -> int | None:
    """Extract the first number from text."""
    import re
    match = re.search(r'\b(\d+)\b', text)
    return int(match.group(1)) if match else None
