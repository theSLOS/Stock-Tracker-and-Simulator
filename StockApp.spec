# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Stock App.
# Build: pyinstaller StockApp.spec
# Prereqs: pip install pyinstaller && python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── CmdStan bundling ──────────────────────────────────────────────────────────
# Prophet uses CmdStanPy which needs a compiled CmdStan distribution.
# We locate the one installed by `cmdstanpy.install_cmdstan()` and bundle it.
try:
    import cmdstanpy
    _cmdstan_path = cmdstanpy.cmdstan_path()
    cmdstan_datas = [(_cmdstan_path, "cmdstan")]
    print(f"[spec] Bundling CmdStan from: {_cmdstan_path}")
except Exception as e:
    cmdstan_datas = []
    print(f"[spec] WARNING: CmdStan not found ({e}). Prophet will fail at runtime.")

# ── Data files ────────────────────────────────────────────────────────────────
datas = [
    # Demo user accounts (profile.json files only — gitignored files are absent)
    ("Users", "Users"),
    # Prophet holiday calendars and model data
    *collect_data_files("prophet"),
    *collect_data_files("holidays"),
    # CmdStan executables (platform-specific binaries)
    *cmdstan_datas,
]

# ── Hidden imports ────────────────────────────────────────────────────────────
# Prophet, holidays, and several other packages use dynamic imports that
# PyInstaller's static analysis misses.
hiddenimports = [
    *collect_submodules("prophet"),
    *collect_submodules("holidays"),
    "cmdstanpy",
    "convertdate",
    "lunarcalendar",
    "scipy.stats",
    "scipy.sparse",
    "scipy.signal",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtSvg",
    "pyqtgraph",
    "pyqtgraph.graphicsItems",
    "yfinance",
    "anthropic",
    "requests",
    "lxml",
    "lxml.etree",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["runtime_hook_cmdstan.py"],
    excludes=["tkinter", "matplotlib.backends._backend_tk", "_pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StockApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can trigger antivirus false positives
    console=False,  # No terminal window for a GUI app
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="StockApp",
)

# macOS: wrap the collected folder in a .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="StockApp.app",
        bundle_identifier="com.ssavory.stockapp",
    )
