# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe. Normally run through `python build.py`, but
`uv run pyinstaller StockingScheduler.spec` works too.

Set ONEDIR=1 in the environment to build a folder instead of a single file.
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 - provided by PyInstaller
ONEDIR = os.environ.get("ONEDIR") == "1"
NAME = "StockingScheduler"

if sys.platform == "win32":
    ICON = str(ROOT / "assets" / "icon.ico")
elif sys.platform == "darwin":
    ICON = str(ROOT / "assets" / "icon.icns")
else:
    ICON = None

# Qt modules the app never imports — leaving them out keeps the build small.
EXCLUDES = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtSql",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.QtDBus",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "PySide6.QtDesigner",
    "PySide6.QtConcurrent",
    "PySide6.QtMultimedia",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.QtPdf",
    "PySide6.Qt3DCore",
    "PySide6.QtCharts",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech",
    "PySide6.QtHttpServer",
    "PySide6.QtWebSockets",
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
]

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "assets" / "icon.png"), "assets")],
    hiddenimports=["PySide6.QtPrintSupport"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)

common = dict(
    name=NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,  # no black terminal window behind the app
    icon=ICON,
)

if ONEDIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=NAME)
    target = coll
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **common)
    target = exe

if sys.platform == "darwin":
    app = BUNDLE(
        target,
        name="Stocking Scheduler.app",
        icon=ICON,
        bundle_identifier="com.stocking1.scheduler",
        # Installer compares this to decide whether a .pkg is an upgrade
        version=os.environ.get("APP_VERSION", "0.0.0"),
        info_plist={"NSHighResolutionCapable": True},
    )
