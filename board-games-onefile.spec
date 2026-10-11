# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（Windows · **单文件 onefile**）。

    python -m PyInstaller board-games-onefile.spec --noconfirm --clean

产物是一个独立的 三棋对弈.exe，可直接拷给别人用。
代价：每次启动会把内置资源（Qt + 引擎 + 网络，约 300MB）解压到临时目录，
启动明显慢于 onedir；对交互式 GUI 应用，onedir + zip 通常是更好的分发方式。
"""

import os
from pathlib import Path

import PySide6

HERE = Path(SPECPATH)
PY_SIDE = Path(PySide6.__file__).parent
USED_NET = "g170-b10c128-s197428736-d67404019.bin.gz"

_RAPFI_DEAD = {"pbrain-rapfi-windows-avxvnni.exe", "pbrain-rapfi-windows-avx512vnni.exe"}


def _skip_bin(p: Path) -> bool:
    name = p.name
    if "gtp_logs" in p.parts:
        return True
    if name.startswith("Pikafish-") and not name.endswith(".exe"):
        return True
    if name.startswith("pbrain-rapfi-") and not name.endswith(".exe"):
        return True
    return name in _RAPFI_DEAD


def _collect(src: Path, dst: str, skip=None):
    out = []
    for root, _dirs, files in os.walk(src):
        for f in files:
            full = Path(root) / f
            if skip and skip(full):
                continue
            rel = full.relative_to(src).parent
            out.append((str(full), str(Path(dst) / rel) if str(rel) != "." else dst))
    return out


datas = [
    (str(HERE / "qml"), "qml"),
    (str(HERE / "assets"), "assets"),
]
datas += _collect(HERE / "engines" / "bin", "engines/bin", _skip_bin)
datas.append((str(HERE / "engines" / "nets" / USED_NET), "engines/nets"))
for mod in ("Qt", "QtCore", "QtQml", "QtQuick", "QtMultimedia"):
    p = PY_SIDE / "qml" / mod
    if p.exists():
        datas.append((str(p), "PySide6/qml/" + mod))

hiddenimports = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2",
    "PySide6.QtMultimedia",
]
excludes = [
    "tkinter", "unittest", "pydoc", "doctest",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.QtWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtQuick3D", "PySide6.Qt3DCore", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtDesigner",
    "PySide6.QtTest", "PySide6.QtSql", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtRemoteObjects", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtWebSockets", "PySide6.QtWebView", "PySide6.QtTextToSpeech",
]

a = Analysis(
    [str(HERE / "main.py")],
    pathex=[str(HERE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

_DROP_TOKENS = (
    "webengine", "qt6pdf", "qtpdf", "qt6widgets", "qtwidgets",
    "qt6quick3d", "qtquick3d", "qt63dcore", "qt6designer", "qtdesigner",
    "qt6charts", "qt6datavisualization", "qt6graphs", "qt6test",
    "qt6sql", "qtsqlite", "qtsql", "qt6bluetooth", "qt6nfc", "qt6scxml",
    "qt6sensors", "qt6texttospeech", "qt6serialport", "qt6remoteobjects",
    "qt6location", "qt6positioning", "qt6websockets", "qt6webchannel",
    "qt6webview", "qt6virtualkeyboard", "qt6quicktimeline",
)
a.binaries = [b for b in a.binaries
              if not any(t in os.path.basename(b[0]).lower() for t in _DROP_TOKENS)]
a.datas = [d for d in a.datas
           if "translations" not in d[0].replace("\\", "/").lower()]

pyz = PYZ(a.pure)

# onefile：不生成 COLLECT，把 binaries/datas 全部塞进单个 exe
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="三棋对弈",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
