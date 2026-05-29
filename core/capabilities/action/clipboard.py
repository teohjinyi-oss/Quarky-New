"""
Action System: Clipboard

Read and write system clipboard via pyperclip.
"""

from core.decision.action_resolver import ActionRequest
from core.capabilities.result_reporter import ActionResult


def execute(action_request: ActionRequest) -> ActionResult:
    """
    Main handler for clipboard actions.
    Routes based on keywords: copy/write → set clipboard, paste/read → get clipboard.
    """
    command = action_request.command.lower()
    target = action_request.target.strip()

    if "paste" in command or "read" in command or "get" in command:
        return _read_clipboard()

    if "copy" in command or "write" in command or "set" in command:
        if target:
            return _write_clipboard(target)
        return ActionResult(success=False, message="No text specified to copy.")

    # Default: if there's target text, copy it; otherwise read
    if target:
        return _write_clipboard(target)
    return _read_clipboard()


def _read_clipboard() -> ActionResult:
    """Read current clipboard content."""
    try:
        import pyperclip
        content = pyperclip.paste()
        if not content:
            return ActionResult(
                success=True,
                message="Clipboard is empty.",
                data={"content": ""},
            )
        return ActionResult(
            success=True,
            message=f"Clipboard content: {content[:200]}{'...' if len(content) > 200 else ''}",
            data={"content": content},
        )
    except ImportError:
        return ActionResult(
            success=False,
            message="Clipboard unavailable. Install: pip install pyperclip",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Clipboard read error: {e}")


def _write_clipboard(text: str) -> ActionResult:
    """Write text to clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        preview = text[:100] + ("..." if len(text) > 100 else "")
        return ActionResult(
            success=True,
            message=f"Copied to clipboard: {preview}",
            data={"copied_length": len(text)},
        )
    except ImportError:
        return ActionResult(
            success=False,
            message="Clipboard unavailable. Install: pip install pyperclip",
        )
    except Exception as e:
        return ActionResult(success=False, message=f"Clipboard write error: {e}")
