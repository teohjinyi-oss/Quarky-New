"""
QuarkyAi — Structure Migration Script
Moves MAIINNN/ + AppStudio/ into the clean architecture layout.

Usage:
  python migrate_structure.py --dry-run    # preview only
  python migrate_structure.py              # execute
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ──────────────────────────────────────────────────────────────────────────────
# 1.  FILE / DIRECTORY MOVES
#     Each entry: (src_relative, dst_relative) — both relative to ROOT
# ──────────────────────────────────────────────────────────────────────────────
DIR_MOVES: list[tuple[str, str]] = [
    # ── core/ ─────────────────────────────────────────────────────────────────
    ("MAIINNN/Intelligence",            "core/intelligence"),
    ("MAIINNN/NLP",                     "core/nlp"),
    ("MAIINNN/Memory",                  "core/memory"),
    ("MAIINNN/Connectors",              "core/routing"),
    ("MAIINNN/Louis",                   "core/analytical"),
    ("MAIINNN/Wednesday",               "core/creative"),
    ("MAIINNN/Decision",                "core/decision"),
    ("MAIINNN/Learning",                "core/learning"),
    # capabilities (non-service Functions)
    ("MAIINNN/Functions/action",        "core/capabilities/action"),
    ("MAIINNN/Functions/automation",    "core/capabilities/automation"),
    ("MAIINNN/Functions/habits",        "core/capabilities/habits"),
    # ── services/ ─────────────────────────────────────────────────────────────
    ("MAIINNN/Functions/web",           "services/web"),
    ("MAIINNN/Functions/monitor",       "services/monitoring"),
    ("MAIINNN/Functions/notifications", "services/notifications"),
    ("MAIINNN/Functions/integrations",  "services/integrations"),
    # ── runtime/infrastructure/ ───────────────────────────────────────────────
    ("AppStudio/Infrastructure/transport", "runtime/transports"),
    # ── interfaces/ ───────────────────────────────────────────────────────────
    ("AppStudio/API",                   "interfaces/api"),
    ("AppStudio/GUI",                   "interfaces/gui"),
    ("AppStudio/Voice",                 "interfaces/voice"),
    ("AppStudio/Start",                 "interfaces/voice/start"),
    # ── native/ ───────────────────────────────────────────────────────────────
    ("Migration/java-shell",            "native/java-shell"),
    ("Migration/native-core",           "native/native-core"),
]

FILE_MOVES: list[tuple[str, str]] = [
    # ── core/ root files ──────────────────────────────────────────────────────
    ("MAIINNN/orchestrator.py",             "core/orchestrator.py"),
    ("MAIINNN/learner.py",                  "core/learner.py"),
    ("MAIINNN/__init__.py",                 "core/__init__.py"),
    # session sub-package
    ("MAIINNN/session_v2.py",               "core/session/session_v2.py"),
    ("MAIINNN/session.py",                  "core/session/session.py"),
    # capabilities root file
    ("MAIINNN/Functions/result_reporter.py","core/capabilities/result_reporter.py"),
    ("MAIINNN/Functions/__init__.py",       "core/capabilities/__init__.py"),
    # ── interfaces/cli/ ───────────────────────────────────────────────────────
    ("MAIINNN/cli.py",                      "interfaces/cli/cli.py"),
    # ── runtime/infrastructure/ individual files ──────────────────────────────
    ("AppStudio/Infrastructure/base.py",       "runtime/infrastructure/base.py"),
    ("AppStudio/Infrastructure/classifier.py", "runtime/infrastructure/classifier.py"),
    ("AppStudio/Infrastructure/logger.py",     "runtime/infrastructure/logger.py"),
    ("AppStudio/Infrastructure/packer.py",     "runtime/infrastructure/packer.py"),
    ("AppStudio/Infrastructure/unpacker.py",   "runtime/infrastructure/unpacker.py"),
    ("AppStudio/Infrastructure/protocol.py",   "runtime/infrastructure/protocol.py"),
    ("AppStudio/Infrastructure/__init__.py",   "runtime/infrastructure/__init__.py"),
    # gateway gets its own sub-package
    ("AppStudio/Infrastructure/gateway.py",    "runtime/gateway/gateway.py"),
    # permissions gets its own sub-package
    ("AppStudio/Infrastructure/permissions.py","runtime/permissions/permissions.py"),
    # workers
    ("AppStudio/Infrastructure/load_balancer.py","runtime/workers/load_balancer.py"),
    ("AppStudio/Infrastructure/worker_pool.py",  "runtime/workers/worker_pool.py"),
    # transports (tcp sits alongside transport/ dir)
    ("AppStudio/Infrastructure/tcp_transport.py","runtime/transports/tcp_transport.py"),
    # config
    ("AppStudio/Config.py",             "runtime/config/config.py"),
    ("AppStudio/config_watcher.py",     "runtime/config/config_watcher.py"),
    ("AppStudio/backup.py",             "runtime/config/backup.py"),
    ("AppStudio/updater.py",            "runtime/config/updater.py"),
    ("AppStudio/__init__.py",           "runtime/__init__.py"),
]

# ──────────────────────────────────────────────────────────────────────────────
# 2.  IMPORT REPLACEMENTS
#     Applied in ORDER — more specific patterns MUST come before broader ones.
#     Each entry: (old_dotted_path, new_dotted_path)
# ──────────────────────────────────────────────────────────────────────────────
IMPORT_REPLACEMENTS: list[tuple[str, str]] = [
    # ── MAIINNN → core (specific sub-packages first) ──────────────────────────
    ("MAIINNN.orchestrator",                    "core.orchestrator"),
    ("MAIINNN.session_v2",                      "core.session.session_v2"),
    ("MAIINNN.session",                         "core.session.session"),
    ("MAIINNN.learner",                         "core.learner"),
    ("MAIINNN.cli",                             "interfaces.cli.cli"),
    ("MAIINNN.Intelligence",                    "core.intelligence"),
    ("MAIINNN.NLP",                             "core.nlp"),
    ("MAIINNN.Memory",                          "core.memory"),
    ("MAIINNN.Connectors",                      "core.routing"),
    ("MAIINNN.Louis",                           "core.analytical"),
    ("MAIINNN.Wednesday",                       "core.creative"),
    ("MAIINNN.Decision",                        "core.decision"),
    ("MAIINNN.Learning",                        "core.learning"),
    # Functions sub-packages (most specific first)
    ("MAIINNN.Functions.action",                "core.capabilities.action"),
    ("MAIINNN.Functions.automation",            "core.capabilities.automation"),
    ("MAIINNN.Functions.habits",                "core.capabilities.habits"),
    ("MAIINNN.Functions.result_reporter",       "core.capabilities.result_reporter"),
    ("MAIINNN.Functions.integrations",          "services.integrations"),
    ("MAIINNN.Functions.web",                   "services.web"),
    ("MAIINNN.Functions.monitor",               "services.monitoring"),
    ("MAIINNN.Functions.notifications",         "services.notifications"),
    ("MAIINNN.Functions",                       "core.capabilities"),
    ("MAIINNN",                                 "core"),

    # ── AppStudio → runtime/interfaces (specific first) ───────────────────────
    # Config
    ("AppStudio.Config",                        "runtime.config.config"),
    ("AppStudio.config_watcher",                "runtime.config.config_watcher"),
    ("AppStudio.backup",                        "runtime.config.backup"),
    ("AppStudio.updater",                       "runtime.config.updater"),
    # Infrastructure — split destinations
    ("AppStudio.Infrastructure.gateway",        "runtime.gateway.gateway"),
    ("AppStudio.Infrastructure.permissions",    "runtime.permissions.permissions"),
    ("AppStudio.Infrastructure.load_balancer",  "runtime.workers.load_balancer"),
    ("AppStudio.Infrastructure.worker_pool",    "runtime.workers.worker_pool"),
    ("AppStudio.Infrastructure.tcp_transport",  "runtime.transports.tcp_transport"),
    ("AppStudio.Infrastructure.transport",      "runtime.transports"),
    ("AppStudio.Infrastructure.base",           "runtime.infrastructure.base"),
    ("AppStudio.Infrastructure.classifier",     "runtime.infrastructure.classifier"),
    ("AppStudio.Infrastructure.logger",         "runtime.infrastructure.logger"),
    ("AppStudio.Infrastructure.packer",         "runtime.infrastructure.packer"),
    ("AppStudio.Infrastructure.unpacker",       "runtime.infrastructure.unpacker"),
    ("AppStudio.Infrastructure.protocol",       "runtime.infrastructure.protocol"),
    ("AppStudio.Infrastructure",                "runtime.infrastructure"),
    # Interface sub-packages
    ("AppStudio.API",                           "interfaces.api"),
    ("AppStudio.GUI",                           "interfaces.gui"),
    ("AppStudio.Voice",                         "interfaces.voice"),
    ("AppStudio.Start",                         "interfaces.voice.start"),
    # Catch-all for anything else under AppStudio
    ("AppStudio",                               "runtime"),
]

# ──────────────────────────────────────────────────────────────────────────────
# 3.  __init__.py files to auto-create for new packages
# ──────────────────────────────────────────────────────────────────────────────
INIT_DIRS: list[str] = [
    "core",
    "core/session",
    "core/capabilities",
    "core/intelligence",
    "core/nlp",
    "core/memory",
    "core/routing",
    "core/analytical",
    "core/creative",
    "core/decision",
    "core/learning",
    "core/capabilities/action",
    "core/capabilities/automation",
    "core/capabilities/habits",
    "runtime",
    "runtime/infrastructure",
    "runtime/gateway",
    "runtime/permissions",
    "runtime/workers",
    "runtime/transports",
    "runtime/config",
    "interfaces",
    "interfaces/api",
    "interfaces/gui",
    "interfaces/voice",
    "interfaces/voice/start",
    "interfaces/cli",
    "services",
    "services/web",
    "services/monitoring",
    "services/notifications",
    "services/integrations",
    "native",
]


# ──────────────────────────────────────────────────────────────────────────────
# 4.  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_parent(path: Path, dry: bool) -> None:
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)


def _copy_tree(src: Path, dst: Path, dry: bool) -> None:
    if not src.exists():
        print(f"  [SKIP]  {src} (not found)")
        return
    if dst.exists():
        print(f"  [EXISTS] {dst} (skipping dir copy — merge manually if needed)")
        return
    print(f"  [DIR]  {src}  →  {dst}")
    if not dry:
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "nul", "*.pdb"))
        except shutil.Error as e:
            # Log partial errors but continue — usually stray device files on Windows
            for item in e.args[0]:
                print(f"  [WARN] copy error: {item[2]}")


def _copy_file(src: Path, dst: Path, dry: bool) -> None:
    if not src.exists():
        print(f"  [SKIP]  {src} (not found)")
        return
    print(f"  [FILE] {src}  →  {dst}")
    if not dry:
        _ensure_parent(dst, dry)
        shutil.copy2(src, dst)


def _create_init(dirpath: Path, dry: bool) -> None:
    init = dirpath / "__init__.py"
    if init.exists():
        return
    print(f"  [INIT] {init}")
    if not dry:
        dirpath.mkdir(parents=True, exist_ok=True)
        init.write_text("", encoding="utf-8")


def _replace_imports_in_file(filepath: Path, replacements: list[tuple[str, str]],
                              dry: bool) -> bool:
    """Return True if any replacement was made."""
    try:
        original = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    text = original
    for old, new in replacements:
        # Match import / from statements only — avoids touching string literals
        # Handles: `import X.Y`, `from X.Y import`, `from X.Y.Z import`
        # The old path must appear as a complete dotted segment (word-boundary aware)
        escaped = re.escape(old)
        # Replaces occurrences that are:
        #   - preceded by: `import ` or `from ` or a dot
        #   - followed by: `.` or whitespace or end-of-line or `(`
        pattern = rf'(?<=["\s(,])({escaped})(?=[.\s(,\\)]|$)'
        text, n = re.subn(pattern, new, text)
        # Also handle lines that START with the module path right after import/from
        pattern2 = rf'(?<=import )({escaped})(?=[.\s\\]|$)'
        text, n2 = re.subn(pattern2, new, text)
        pattern3 = rf'(?<=from )({escaped})(?=[.\s\\]|$)'
        text, n3 = re.subn(pattern3, new, text)

    if text == original:
        return False

    print(f"  [IMPORTS] {filepath.relative_to(ROOT)}")
    if not dry:
        filepath.write_text(text, encoding="utf-8")
    return True


def _walk_python_files(root: Path) -> list[Path]:
    """Return all .py files under new dirs, skipping old dirs and tool scripts."""
    # Only walk the NEW directories — old ones are untouched originals
    new_dirs = ["core", "runtime", "interfaces", "services", "native"]
    # Root-level .py files that should have imports rewritten
    root_include = {"main.py"}
    # Root-level scripts that must NOT be rewritten (contain string literals with old paths)
    root_exclude = {"migrate_structure.py", "fix_imports.py"}

    results = []
    for subdir in new_dirs:
        target = root / subdir
        if not target.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fname in filenames:
                if fname.endswith(".py"):
                    results.append(Path(dirpath) / fname)

    for fname in root_include:
        p = root / fname
        if p.exists():
            results.append(p)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# 5.  Main
# ──────────────────────────────────────────────────────────────────────────────

def run(dry: bool) -> None:
    label = "[DRY RUN] " if dry else ""
    print(f"\n{'='*70}")
    print(f"  QuarkyAi Structure Migration  {label}")
    print(f"{'='*70}\n")

    # Step 1 — copy directories
    print("── Step 1: Copy directories ─────────────────────────────────────────")
    for src_rel, dst_rel in DIR_MOVES:
        _copy_tree(ROOT / src_rel, ROOT / dst_rel, dry)

    # Step 2 — copy individual files
    print("\n── Step 2: Copy files ───────────────────────────────────────────────")
    for src_rel, dst_rel in FILE_MOVES:
        _copy_file(ROOT / src_rel, ROOT / dst_rel, dry)

    # Step 3 — create __init__.py stubs
    print("\n── Step 3: Create __init__.py stubs ────────────────────────────────")
    for d in INIT_DIRS:
        _create_init(ROOT / d, dry)

    # Step 4 — move models/ into data/models/
    print("\n── Step 4: Move models/ → data/models/ ─────────────────────────────")
    _copy_tree(ROOT / "models", ROOT / "data" / "models", dry)

    # Step 5 — rewrite imports in ALL Python files under new dirs
    print("\n── Step 5: Rewrite import paths ─────────────────────────────────────")
    py_files = _walk_python_files(ROOT)
    changed = 0
    for f in py_files:
        if _replace_imports_in_file(f, IMPORT_REPLACEMENTS, dry):
            changed += 1
    print(f"  → {changed} file(s) had imports updated")

    # Step 6 — also update tests/ and main.py (they're excluded from walk above)
    print("\n── Step 6: Rewrite imports in tests/ and main.py ────────────────────")
    extra_files = list((ROOT / "tests").glob("**/*.py")) + [ROOT / "main.py"]
    for f in extra_files:
        if f.exists():
            _replace_imports_in_file(f, IMPORT_REPLACEMENTS, dry)

    print(f"\n{'='*70}")
    if dry:
        print("  DRY RUN complete — no files written.")
        print("  Run without --dry-run to apply changes.")
    else:
        print("  Migration complete.")
        print("  Next steps:")
        print("    1. Run: python -m pytest tests/ -x -q")
        print("    2. If green, delete old dirs:")
        print("       rmdir /s /q MAIINNN AppStudio\\Infrastructure AppStudio\\Voice")
        print("       rmdir /s /q AppStudio\\Start Migration AppStudio\\API AppStudio\\GUI")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QuarkyAi structure migration")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    args = parser.parse_args()
    run(dry=args.dry_run)
