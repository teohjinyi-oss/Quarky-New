"""
Action System: Code Runner

Full sandboxed Python execution with:
  - Restricted builtins (no open, exec, eval, __import__)
  - Blocked imports from config
  - Threading.Timer timeout
  - Stdout capture via io.StringIO
  - Multi-line code support
"""

import io
import sys
import threading
from typing import Any

from AppStudio.Config import ACTION
from MAIINNN.Decision.action_resolver import ActionRequest
from MAIINNN.Functions.result_reporter import ActionResult


_TIMEOUT = ACTION["code_runner_timeout"]
_BLOCKED_IMPORTS = set(ACTION["code_runner_blocked_imports"])

# Safe builtins whitelist
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "dir": dir, "divmod": divmod,
    "enumerate": enumerate, "filter": filter, "float": float,
    "format": format, "frozenset": frozenset, "hash": hash,
    "hex": hex, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len,
    "list": list, "map": map, "max": max, "min": min,
    "next": next, "oct": oct, "ord": ord, "pow": pow,
    "print": print,  # Will be redirected to StringIO
    "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "slice": slice, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "type": type,
    "zip": zip,
    "True": True, "False": False, "None": None,
}


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Custom __import__ that blocks dangerous modules."""
    if name in _BLOCKED_IMPORTS:
        raise ImportError(f"Import of '{name}' is blocked for safety.")
    # Allow safe imports like math, json, re, etc.
    return __builtins__.__import__(name, *args, **kwargs) if hasattr(__builtins__, '__import__') else __import__(name, *args, **kwargs)


def execute(action_request: ActionRequest) -> ActionResult:
    """
    Main handler for code_run actions.
    Executes Python code in a sandboxed environment.
    """
    code = action_request.target.strip()
    if not code:
        code = action_request.parameters.get("code", "")

    if not code:
        return ActionResult(success=False, message="No code provided to execute.")

    return _run_sandboxed(code)


def _run_sandboxed(code: str) -> ActionResult:
    """Execute code in a restricted sandbox with timeout."""
    stdout_capture = io.StringIO()
    result_container: dict[str, Any] = {"output": "", "error": None, "timed_out": False}

    # Build restricted globals
    restricted_globals: dict[str, Any] = {"__builtins__": {}}
    restricted_globals["__builtins__"].update(_SAFE_BUILTINS)
    restricted_globals["__builtins__"]["__import__"] = _safe_import
    # Redirect print to our capture
    restricted_globals["__builtins__"]["print"] = lambda *a, **kw: print(
        *a, **kw, file=stdout_capture)

    # Also provide common safe modules pre-imported
    try:
        import math
        restricted_globals["math"] = math
    except ImportError:
        pass
    try:
        import re
        restricted_globals["re"] = re
    except ImportError:
        pass
    try:
        import json
        restricted_globals["json"] = json
    except ImportError:
        pass
    try:
        import random
        restricted_globals["random"] = random
    except ImportError:
        pass
    try:
        import datetime
        restricted_globals["datetime"] = datetime
    except ImportError:
        pass

    def _exec_thread() -> None:
        try:
            # Try as expression first (for things like "2+2")
            try:
                val = eval(compile(code, "<quarky_sandbox>", "eval"),
                           restricted_globals)
                if val is not None:
                    print(repr(val), file=stdout_capture)
            except SyntaxError:
                # Not an expression — execute as statements
                exec(compile(code, "<quarky_sandbox>", "exec"),
                     restricted_globals)

            result_container["output"] = stdout_capture.getvalue()
        except Exception as e:
            result_container["error"] = f"{type(e).__name__}: {e}"

    # Run with timeout
    thread = threading.Thread(target=_exec_thread, daemon=True)
    thread.start()
    thread.join(timeout=_TIMEOUT)

    if thread.is_alive():
        result_container["timed_out"] = True

    if result_container["timed_out"]:
        return ActionResult(
            success=False,
            message=f"Code execution timed out after {_TIMEOUT} seconds.",
        )

    if result_container["error"]:
        return ActionResult(
            success=False,
            message=f"Code error: {result_container['error']}",
        )

    output = result_container["output"].strip()
    if not output:
        output = "(no output)"

    return ActionResult(
        success=True,
        message=f"Output:\n{output}",
        data={"output": output, "code": code},
    )
