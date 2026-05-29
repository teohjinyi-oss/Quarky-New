"""
Quarky_Ai — Entry Point

python -m quarky_ai
Supports: --mode cli|api|both (default: interactive menu)
"""

import argparse
import sys
import os
import time

# ─── ASCII Logo ──────────────────────────────────────────────
QUARKY_LOGO = r"""
                          . o .
                     .  /       \  .
               . o .  /   . - .   \  . o .
                   \ /  .       .  \ /
                    \/  .   @   .  \/
                    /\  .       .  /\
                   / \  .       .  / \
               . o .  \   . - .   /  . o .
                     .  \       /  .
                          . o .

      .d8888b.  888     888        d8888 8888888b.  888  d8P  Y888b
     d88P  Y88b 888     888       d88888 888   Y88b 888 d8P    Y88b
     888    888 888     888      d88P888 888    888 888888      888
     888    888 888     888     d88P 888 8888888b.  888 88b     888
     888    888 888     888    d88P  888 888   Y88b 888  88b    888
     Y88q  d88P Y88b. .d88P  d88P   888 888    888 888   88b  d88P
      "Y8888P"   "Y88888P"  d8888888888 888   d88P 888    88 d88P
"""

QUARKY_TAGLINE = "    Your Personal AI Assistant -- Zero LLM, Pure Brain"


def _print_banner() -> None:
    """Print the Quarky startup banner."""
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    print(QUARKY_LOGO)
    print(QUARKY_TAGLINE)
    print()


def _init_systems() -> list[str]:
    """
    Initialize all background systems.
    Returns list of init status messages.
    """
    steps: list[str] = []

    # 1. Memory decay engine
    try:
        from core.memory.manager import start_decay_engine
        start_decay_engine()
        steps.append("  [+] Memory decay engine started")
    except Exception as e:
        steps.append(f"  [!] Memory decay engine failed: {e}")

    # 2. Load balancer monitoring
    try:
        from runtime.workers.load_balancer import LoadBalancer
        lb = LoadBalancer()
        lb.start_monitoring()
        steps.append("  [+] Load balancer monitoring started")
    except Exception as e:
        steps.append(f"  [!] Load balancer failed: {e}")

    # 3. App discovery
    try:
        from core.capabilities.action.app_discovery import refresh
        count = refresh()
        steps.append(f"  [+] App discovery: {count} apps found")
    except Exception as e:
        steps.append(f"  [!] App discovery failed: {e}")

    # 4. Action registry
    try:
        from core.capabilities.action.registry import ensure_builtins
        ensure_builtins()
        steps.append("  [+] Action registry loaded")
    except Exception as e:
        steps.append(f"  [!] Action registry failed: {e}")

    # 5. Session
    try:
        from core.session.session import get_session
        get_session()
        steps.append("  [+] Session initialized")
    except Exception as e:
        steps.append(f"  [!] Session failed: {e}")

    # 6. Voice system (lazy — only reports availability)
    try:
        import importlib.util
        sd_avail = importlib.util.find_spec("sounddevice") is not None
        vosk_avail = importlib.util.find_spec("vosk") is not None
        pyttsx3_avail = importlib.util.find_spec("pyttsx3") is not None
        if sd_avail and vosk_avail and pyttsx3_avail:
            steps.append("  [+] Voice system available")
        else:
            missing = [n for n, a in [("sounddevice", sd_avail), ("vosk", vosk_avail), ("pyttsx3", pyttsx3_avail)] if not a]
            steps.append(f"  [~] Voice system partial (missing: {', '.join(missing)})")
    except Exception as e:
        steps.append(f"  [!] Voice check failed: {e}")

    return steps


def _run_cli() -> None:
    """Launch CLI mode."""
    from interfaces.cli.cli import run_cli
    run_cli()


def _run_api() -> None:
    """Launch API server."""
    try:
        import uvicorn
        from interfaces.api.server import app
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except ImportError:
        print("  [!] uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)


def _run_voice() -> None:
    """Launch voice mode."""
    from interfaces.voice.start.state_manager import start_voice, stop_voice, voice_status
    print("  Starting voice pipeline...")
    if not start_voice():
        status = voice_status()
        print(f"  [!] Voice failed: {status.get('last_error', 'unknown')}")
        print("  Falling back to CLI mode.")
        _run_cli()
        return
    print("  [+] Voice active — say 'Quarky' to begin")
    print("  Press Ctrl+C to stop.")
    print()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping voice...")
        stop_voice()


def _run_both() -> None:
    """Launch CLI + API in parallel."""
    import threading
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    print("  [+] API server started on http://127.0.0.1:8000")
    print()
    _run_cli()


def _interactive_menu() -> str:
    """Show interactive mode selection menu."""
    print("  Select mode:")
    print("    1) CLI    — Chat in terminal")
    print("    2) API    — REST API server")
    print("    3) Both   — CLI + API together")
    print("    4) Voice  — Hands-free voice mode")
    print("    q) Quit")
    print()

    while True:
        choice = input("  > ").strip().lower()
        if choice in ("1", "cli"):
            return "cli"
        elif choice in ("2", "api"):
            return "api"
        elif choice in ("3", "both"):
            return "both"
        elif choice in ("4", "voice"):
            return "voice"
        elif choice in ("q", "quit", "exit"):
            print("  Goodbye!")
            sys.exit(0)
        else:
            print("  Invalid choice. Enter 1, 2, 3, 4, or q.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="quarky_ai",
        description="Quarky AI — Your Personal AI Assistant",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["cli", "api", "both", "voice"],
        default=None,
        help="Launch mode: cli, api, both, or voice (default: interactive menu)",
    )
    args = parser.parse_args()

    # Banner
    _print_banner()

    # Init systems
    print("  Initializing systems...")
    steps = _init_systems()
    for step in steps:
        print(step)
    print()

    # Mode selection
    mode = args.mode or _interactive_menu()

    print(f"  Starting {mode.upper()} mode...")
    print("─" * 50)
    print()

    if mode == "cli":
        _run_cli()
    elif mode == "api":
        _run_api()
    elif mode == "both":
        _run_both()
    elif mode == "voice":
        _run_voice()


if __name__ == "__main__":
    main()
