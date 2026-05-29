"""
Quarky_Ai — Interactive CLI

ChatGPT-style terminal interface with slash commands, action confirmation,
duplicate detection, memory integration, debug mode, and session tracking.
"""

import os
import sys
import time
import random
from typing import Any

from MAIINNN.Decision.output_gate import process, confirm_action, FinalOutput
from MAIINNN.Decision.action_resolver import ActionRequest
from MAIINNN.session import get_session, end_session, Session


# ─── State ───────────────────────────────────────────────────

_debug_mode = False
_pending_confirmation: ActionRequest | None = None


# ─── Personality Responses ───────────────────────────────────

_EMPTY_RESPONSES = [
    "Hmm, that's an interesting way to say nothing.",
    "I'm here whenever you're ready to type something.",
    "The void stares back... try typing something?",
    "Blank input detected. Brain cells standing by.",
    "I appreciate the silence, but I work better with words.",
]

_FAREWELL_MESSAGES = [
    "See you later!",
    "Until next time!",
    "Goodbye! I'll keep your memories safe.",
    "Take care! Quarky out.",
]


# ─── Formatting Helpers ─────────────────────────────────────

def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _print_separator() -> None:
    print("─" * 50)


def _print_quarky(text: str) -> None:
    """Print a Quarky response."""
    for line in text.split("\n"):
        print(f"  {line}")
    print()


def _print_error(message: str, detail: str = "") -> None:
    """Two-tier error: friendly message + optional debug detail."""
    print(f"  Oops: {message}")
    if _debug_mode and detail:
        print(f"  [debug] {detail}")
    print()


def _print_debug(label: str, value: Any) -> None:
    """Print debug info if debug mode is on."""
    if _debug_mode:
        print(f"  [debug] {label}: {value}")


# ─── Slash Command Handlers ─────────────────────────────────

def _cmd_help() -> None:
    """Show all available commands."""
    print()
    print("  Commands:")
    _print_separator()
    cmds = [
        ("/help",                "Show this help message"),
        ("/status",              "System health & stats"),
        ("/clear",               "Clear the screen"),
        ("/mode <cli|api|both>", "Switch launch mode"),
        ("/config",              "Show current config values"),
        ("/debug",               "Toggle debug output"),
        ("/about",               "Version & system info"),
        ("/memory",              "Memory layer stats"),
        ("/recall <keyword>",    "Search across all memory layers"),
        ("/forget <layer> <id>", "Delete a memory entry"),
        ("/remember <text>",     "Force-store to permanent memory"),
        ("/history",             "Show conversation history"),
        ("/history search <kw>", "Search conversation history"),
        ("/replay [count]",      "Replay recent conversation"),
        ("/actions",             "Recent action log"),
        ("/actions stats",       "Action success/failure stats"),
        ("/undo",                "Undo last reversible action"),
        ("/app add <name> <path>", "Register a custom app"),
        ("/export",              "Export all data to zip"),
        ("/quit",                "Exit Quarky"),
    ]
    for cmd, desc in cmds:
        print(f"  {cmd:<26} {desc}")
    print()


def _cmd_status() -> None:
    """Show system health dashboard."""
    session = get_session()
    s_stats = session.get_stats()

    print()
    print("  Quarky System Status")
    _print_separator()
    print(f"  Uptime:        {s_stats['uptime']}")
    print(f"  Turns:         {s_stats['turn_count']}")
    print(f"  Actions:       {s_stats['actions_performed']}")

    # Memory stats
    try:
        from MAIINNN.Memory.manager import stats as mem_stats
        m = mem_stats()
        total = sum(m.values())
        print(f"  Memory:        {total} entries "
              f"(T:{m['temporary']} F:{m['flexible']} "
              f"P:{m['priority']} Perm:{m['permanent']})")
    except Exception:
        print("  Memory:        unavailable")

    # Action stats
    try:
        from MAIINNN.Functions.action.action_logger import get_stats as action_stats
        a = action_stats()
        print(f"  Action Log:    {a['total_actions']} total, "
              f"{a['success_rate']*100:.0f}% success")
    except Exception:
        print("  Action Log:    unavailable")

    # Response sources
    if s_stats["response_sources"]:
        sources = ", ".join(f"{k}:{v}" for k, v in
                            s_stats["response_sources"].items())
        print(f"  Sources:       {sources}")

    print()


def _cmd_debug() -> None:
    """Toggle debug mode."""
    global _debug_mode
    _debug_mode = not _debug_mode
    state = "ON" if _debug_mode else "OFF"
    _print_quarky(f"Debug mode: {state}")


def _cmd_about() -> None:
    """Show version and system info."""
    print()
    print("  Quarky AI v1.0.0")
    print("  Architecture: Zero-LLM Custom Brain")
    print("  Systems: NLP → Core Brain → Memory → Decision → Action")
    print("  Built with: Pure Python, no external AI dependencies")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Platform: {sys.platform}")
    print()


def _cmd_memory() -> None:
    """Show memory layer stats."""
    try:
        from MAIINNN.Memory.manager import stats as mem_stats
        m = mem_stats()
        print()
        print("  Memory Layers:")
        _print_separator()
        print(f"  Temporary  (Layer 1):  {m['temporary']} entries")
        print(f"  Flexible   (Layer 2):  {m['flexible']} entries")
        print(f"  Priority   (Layer 3):  {m['priority']} entries")
        print(f"  Permanent  (Layer 4):  {m['permanent']} entries")
        print(f"  Total:                 {sum(m.values())} entries")
        print()
    except Exception as e:
        _print_error("Could not load memory stats", str(e))


def _cmd_recall(keyword: str) -> None:
    """Search across all memory layers."""
    if not keyword:
        _print_quarky("Usage: /recall <keyword>")
        return

    try:
        from MAIINNN.Memory.manager import recall
        results = recall(keyword.split(), max_per_layer=5)

        if results.total == 0:
            _print_quarky(f"No memories found for '{keyword}'.")
            return

        print()
        print(f"  Memory search: '{keyword}' ({results.total} results)")
        _print_separator()

        for layer_name, items in [
            ("Permanent", results.permanent),
            ("Priority", results.priority),
            ("Flexible", results.flexible),
            ("Temporary", results.temporary),
        ]:
            if items:
                print(f"  [{layer_name}]")
                for item in items:
                    content = str(item)[:80]
                    print(f"    - {content}")
        print()
    except Exception as e:
        _print_error("Memory search failed", str(e))


def _cmd_forget(args: str) -> None:
    """Delete a memory entry: /forget <layer> <id>"""
    parts = args.split(None, 1)
    if len(parts) < 2:
        _print_quarky("Usage: /forget <layer> <id>\n"
                      "Layers: temporary, flexible, priority, permanent")
        return

    layer, entry_id = parts[0].lower(), parts[1].strip()

    try:
        from MAIINNN.Memory import manager as mm
        forget_fn = {
            "temporary": mm.forget_temporary,
            "flexible": mm.forget_flexible,
            "priority": mm.forget_priority,
            "permanent": lambda eid: mm.forget_permanent(eid, user_confirmed=True),
        }.get(layer)

        if not forget_fn:
            _print_quarky(f"Unknown layer: {layer}")
            return

        result = forget_fn(entry_id)
        _print_quarky(result.message)
    except Exception as e:
        _print_error("Forget failed", str(e))


def _cmd_remember(text: str) -> None:
    """Force-store to permanent memory."""
    if not text:
        _print_quarky("Usage: /remember <text to store permanently>")
        return

    try:
        from MAIINNN.Memory.manager import store_permanent
        result = store_permanent(text, tags=["user-saved"], source="cli")
        _print_quarky(f"Saved to permanent memory. ({result.data})")
    except Exception as e:
        _print_error("Could not store memory", str(e))


def _cmd_history(args: str) -> None:
    """Show or search conversation history."""
    session = get_session()

    if args.startswith("search "):
        keyword = args[7:].strip()
        turns = session.get_history(count=50, search=keyword)
        if not turns:
            _print_quarky(f"No history matching '{keyword}'.")
            return
        print()
        print(f"  History search: '{keyword}' ({len(turns)} matches)")
        _print_separator()
        for t in turns:
            print(f"  [{t.time_str}] You: {t.user_text}")
            print(f"  [{t.time_str}] Quarky: {t.response[:80]}...")
            print()
        return

    turns = session.get_history(count=20)
    if not turns:
        _print_quarky("No conversation history yet.")
        return

    print()
    print(f"  Conversation History (last {len(turns)} turns)")
    _print_separator()
    for t in turns:
        print(f"  [{t.time_str}] You: {t.user_text}")
        resp = t.response if len(t.response) <= 100 else t.response[:100] + "..."
        print(f"  [{t.time_str}] Quarky: {resp}")
        if t.action_performed:
            print(f"            Action: {t.action_performed}")
        print()


def _cmd_replay(args: str) -> None:
    """Replay recent conversation."""
    session = get_session()
    count = 0
    if args.strip().isdigit():
        count = int(args.strip())
    print()
    print(session.format_replay(count))


def _cmd_actions(args: str) -> None:
    """Show action log or stats."""
    if args.strip() == "stats":
        try:
            from MAIINNN.Functions.action.action_logger import get_stats
            s = get_stats()
            print()
            print("  Action Statistics")
            _print_separator()
            print(f"  Total:        {s['total_actions']}")
            print(f"  Successful:   {s['successful']}")
            print(f"  Failed:       {s['failed']}")
            print(f"  Success Rate: {s['success_rate']*100:.1f}%")
            if s["by_type"]:
                print(f"  By Type:      {s['by_type']}")
            if s["by_risk"]:
                print(f"  By Risk:      {s['by_risk']}")
            print()
        except Exception as e:
            _print_error("Could not load action stats", str(e))
        return

    try:
        from MAIINNN.Functions.action.action_logger import get_recent
        entries = get_recent(20)
        if not entries:
            _print_quarky("No actions logged yet.")
            return

        print()
        print(f"  Recent Actions (last {len(entries)})")
        _print_separator()
        for e in reversed(entries):
            status = "OK" if e.get("success") else "FAIL"
            ts = e.get("time_str", "")
            at = e.get("action_type", "?")
            tgt = e.get("target", "")[:40]
            dur = e.get("duration_ms", 0)
            print(f"  [{ts}] {status:4} {at} → {tgt} ({dur:.0f}ms)")
        print()
    except Exception as e:
        _print_error("Could not load action log", str(e))


def _cmd_undo() -> None:
    """Undo last reversible action."""
    try:
        from MAIINNN.Functions.action.undo_manager import undo_last
        result = undo_last()
        _print_quarky(result.message)
    except Exception as e:
        _print_error("Undo failed", str(e))


def _cmd_app_add(args: str) -> None:
    """Register a custom app: /app add <name> <path>"""
    parts = args.split(None, 1)
    if len(parts) < 2:
        _print_quarky("Usage: /app add <name> <path>")
        return

    name, path = parts[0], parts[1].strip()
    try:
        from MAIINNN.Functions.action.app_discovery import add_custom_app
        add_custom_app(name, path)
        _print_quarky(f"Registered app '{name}' → {path}")
    except Exception as e:
        _print_error("Could not register app", str(e))


def _cmd_export() -> None:
    """Export all data to zip."""
    try:
        from AppStudio.backup import export_all
        zip_path = export_all()
        _print_quarky(f"Exported to: {zip_path}")
    except ImportError:
        _print_quarky("Export module not available yet.")
    except Exception as e:
        _print_error("Export failed", str(e))


def _cmd_config() -> None:
    """Show current config values."""
    try:
        from AppStudio import Config as config
        print()
        print("  Configuration")
        _print_separator()
        print(f"  Data Dir:      {config.DATA_DIR}")
        print(f"  DB Path:       {config.DB_PATH}")
        print(f"  Fast Threshold: {config.FAST_MODE_THRESHOLD}")
        print(f"  Deep Threshold: {config.DEEP_MODE_THRESHOLD}")
        print(f"  Workers:       {config.WORKER_POOL['default_max_workers']}")
        print(f"  Decay Interval: {config.MEMORY['decay_interval_seconds']}s")
        print(f"  Code Timeout:  {config.ACTION['code_runner_timeout']}s")
        print(f"  Log Level:     {config.LOG['log_level']}")
        print()
    except Exception as e:
        _print_error("Could not load config", str(e))


# ─── Slash Command Router ───────────────────────────────────

def _handle_slash_command(text: str) -> bool:
    """
    Handle a slash command. Returns True if handled, False if not a command.
    """
    if not text.startswith("/"):
        return False

    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handlers = {
        "/help": lambda: _cmd_help(),
        "/status": lambda: _cmd_status(),
        "/clear": lambda: _clear_screen(),
        "/debug": lambda: _cmd_debug(),
        "/about": lambda: _cmd_about(),
        "/memory": lambda: _cmd_memory(),
        "/recall": lambda: _cmd_recall(args),
        "/forget": lambda: _cmd_forget(args),
        "/remember": lambda: _cmd_remember(args),
        "/history": lambda: _cmd_history(args),
        "/replay": lambda: _cmd_replay(args),
        "/actions": lambda: _cmd_actions(args),
        "/undo": lambda: _cmd_undo(),
        "/export": lambda: _cmd_export(),
        "/config": lambda: _cmd_config(),
    }

    if cmd in handlers:
        handlers[cmd]()
        return True

    # /app add <name> <path>
    if cmd == "/app" and args.lower().startswith("add "):
        _cmd_app_add(args[4:])
        return True

    # /mode — just inform for now
    if cmd == "/mode":
        _print_quarky(f"Mode switching requires restart. "
                      f"Use: python -m quarky_ai --mode {args or 'cli'}")
        return True

    # /quit, /exit
    if cmd in ("/quit", "/exit"):
        return False  # Let the main loop handle exit

    # Unknown slash command → treat as brain input (smart fallback)
    return False


# ─── Confirmation Flow ───────────────────────────────────────

def _handle_confirmation(text: str) -> bool:
    """Handle y/n confirmation for pending actions. Returns True if handled."""
    global _pending_confirmation

    if _pending_confirmation is None:
        return False

    action = _pending_confirmation
    _pending_confirmation = None

    lower = text.lower().strip()
    if lower in ("y", "yes"):
        result = confirm_action(action)
        if result.success:
            _print_quarky(f"Done: {result.message}")
        else:
            _print_quarky(f"Failed: {result.message}")
        return True
    elif lower in ("n", "no"):
        _print_quarky("Cancelled.")
        return True

    # Not a y/n answer — fall through to normal processing
    _pending_confirmation = None
    return False


# ─── Main Processing ────────────────────────────────────────

def _process_input(text: str) -> None:
    """Process a normal (non-command) user input through the brain."""
    global _pending_confirmation
    session = get_session()

    # Duplicate detection
    duplicate = session.check_duplicate(text)
    if duplicate:
        _print_quarky(f"You already asked that. Here's what I said:\n"
                      f"{duplicate.response}")
        return

    # Process through the decision engine
    try:
        result: FinalOutput = process(text)
    except Exception as e:
        _print_error("Something went wrong processing that", str(e))
        return

    # Debug info
    _print_debug("source", result.source)
    _print_debug("confidence", f"{result.confidence:.3f}")
    if result.reasoning:
        _print_debug("reasoning", " → ".join(result.reasoning))
    if result.memory_actions:
        _print_debug("memory", ", ".join(result.memory_actions))

    # Print response
    _print_quarky(result.response)

    # Track action performed
    action_msg = ""
    if result.action_result and result.action_result.success:
        action_msg = result.action_result.message

    # Set pending confirmation if needed
    if result.action_request and result.action_request.needs_confirmation:
        _pending_confirmation = result.action_request

    # Record turn in session
    session.add_turn(
        user_text=text,
        response=result.response,
        source=result.source,
        confidence=result.confidence,
        action_performed=action_msg,
    )


# ─── Main Loop ──────────────────────────────────────────────

def run_cli() -> None:
    """Main interactive CLI loop."""
    print("  Type /help for commands, or just start talking.")
    print()

    try:
        while True:
            try:
                text = input("  You > ").strip()
            except EOFError:
                break

            # Empty input → personality
            if not text:
                _print_quarky(random.choice(_EMPTY_RESPONSES))
                continue

            # Quit commands
            if text.lower() in ("quit", "exit", "/quit", "/exit"):
                _shutdown()
                break

            # Confirmation flow
            if _handle_confirmation(text):
                continue

            # Slash commands
            if text.startswith("/"):
                handled = _handle_slash_command(text)
                if not handled:
                    # Smart fallback: strip the / and process as text
                    _process_input(text.lstrip("/"))
                continue

            # Normal input → brain
            _process_input(text)

    except KeyboardInterrupt:
        print()
        _shutdown()


def _shutdown() -> None:
    """Graceful shutdown with stats summary."""
    print()
    _print_separator()

    stats = end_session()
    print(f"  Session: {stats['turn_count']} turns in {stats['uptime']}")
    print(f"  Actions performed: {stats['actions_performed']}")
    print()

    # Stop background systems
    try:
        from MAIINNN.Memory.manager import stop_decay_engine
        stop_decay_engine()
    except Exception:
        pass

    print(f"  {random.choice(_FAREWELL_MESSAGES)}")
    print()


if __name__ == "__main__":
    run_cli()
