"""
Quarky AI — PyInstaller Build Specification

Builds a single-directory distribution (.exe) with all dependencies,
data files, and the Vosk speech model bundled. No console window.

Build command:
    python -m PyInstaller quarky.spec --noconfirm

The output goes to dist/QuarkyAI/QuarkyAI.exe
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Paths ─────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(".")

# ── Hidden imports (dynamic imports the analysis can't detect) ─

hidden_imports = [
    # Core subsystems
    *collect_submodules("quarky_ai"),
    # PySide6 essentials
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    # ML / NLP
    "sentence_transformers",
    "sklearn",
    "sklearn.utils._cython_blas",
    "sklearn.neighbors._typedefs",
    "numpy",
    "torch",
    # Memory
    "chromadb",
    "networkx",
    "cryptography",
    # Voice
    "vosk",
    "pyttsx3",
    "sounddevice",
    # Monitoring
    "psutil",
    # Web
    "bs4",
    "lxml",
    "duckduckgo_search",
    # System
    "plyer.platforms.win.notification",
]

# ── Data files ────────────────────────────────────────────────

datas = [
    # Vosk speech model
    (os.path.join(PROJECT_ROOT, "models", "vosk-model-small-en-us-0.15"),
     os.path.join("models", "vosk-model-small-en-us-0.15")),
    # User data directory (ship empty structure, actual data is created at runtime)
]

# Add sentence-transformers data if available
try:
    st_data = collect_data_files("sentence_transformers")
    datas.extend(st_data)
except Exception:
    pass

# ── Analysis ──────────────────────────────────────────────────

a = Analysis(
    [os.path.join(PROJECT_ROOT, "quarky_ai", "gui", "app.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QuarkyAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # NO console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                # TODO: Add quarky.ico when available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="QuarkyAI",
)
