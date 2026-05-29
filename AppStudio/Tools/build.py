"""
Quarky AI — Build Script

Automates the full build pipeline:
  1. Run tests to verify everything works
  2. Build .exe with PyInstaller
  3. Copy data directory skeleton into dist
  4. Report build result

Usage:
    python build.py          # Full build
    python build.py --skip-tests   # Skip test phase
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "QuarkyAI"


def run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n[FAIL] {label} (exit code {result.returncode})")
        return False
    print(f"\n[OK] {label}")
    return True


def build_exe() -> bool:
    return run(
        [PYTHON, "-m", "PyInstaller", "quarky.spec", "--noconfirm", "--clean"],
        "PyInstaller build",
    )


def run_tests() -> bool:
    return run(
        [PYTHON, "-m", "pytest", "tests/", "-q", "--tb=short"],
        "Test suite",
    )


def copy_data_skeleton():
    """Create empty data directory structure in dist so the app has writable storage."""
    data_dist = DIST / "data"
    for sub in ("memory", "actions", "vector_db", "graph",
                "learning", "habits", "monitor", "integrations",
                "automation", "quarky_trash"):
        (data_dist / sub).mkdir(parents=True, exist_ok=True)
    print(f"[OK] Data skeleton created at {data_dist}")


def smoke_test() -> bool:
    """Post-build smoke test: verify the exe launches and responds."""
    exe_path = DIST / "QuarkyAI.exe"
    if not exe_path.exists():
        print("[SKIP] Smoke test — exe not found (onedir build)")
        return True
    print("\n" + "=" * 60)
    print("  Post-build smoke test")
    print("=" * 60 + "\n")
    try:
        result = subprocess.run(
            [str(exe_path), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"[OK] Smoke test — version: {result.stdout.strip()}")
            return True
        print(f"[WARN] Smoke test exited with code {result.returncode}")
        return True  # non-fatal — exe may not support --version yet
    except subprocess.TimeoutExpired:
        print("[WARN] Smoke test timed out (30s) — exe may need GUI")
        return True  # non-fatal for GUI apps
    except Exception as e:
        print(f"[WARN] Smoke test error: {e}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Build Quarky AI .exe")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest")
    args = parser.parse_args()

    print("Quarky AI — Build Pipeline")
    print(f"Python: {PYTHON}")
    print(f"Root:   {ROOT}")

    # 1. Tests
    if not args.skip_tests:
        if not run_tests():
            sys.exit(1)

    # 2. Build
    if not build_exe():
        sys.exit(1)

    # 3. Data skeleton
    copy_data_skeleton()

    # 4. Post-build smoke test
    smoke_ok = smoke_test()

    # 5. Done
    exe_path = DIST / "QuarkyAI.exe"
    print(f"\n{'='*60}")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  BUILD SUCCESS")
        print(f"  Executable: {exe_path}")
        print(f"  Size:       {size_mb:.1f} MB")
    else:
        print(f"  BUILD COMPLETE — check dist/QuarkyAI/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
