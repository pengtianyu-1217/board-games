# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（Windows · onedir）。

    python -m PyInstaller board-games.spec --noconfirm --clean

只装应用真正需要的东西：
- 引擎：仅 Windows 二进制（剔除非 Windows 版、Rapfi 未使用的指令集、KataGo 运行日志），
  网络只带在用的卷积网 g170-b10c128。
- Qt：只带 QML 实际用到的模块（QtQml / QtQuick / QtMultimedia）与必要插件，
  剔掉 WebEngine（~194MB）、Widgets、Quick3D、Pdf、多余翻译等。
"""

import os
from pathlib import Path

import PySide6

HERE = Path(SPECPATH)
PY_SIDE = Path(PySide6.__file__).parent
USED_NET = "g170-b10c128-s197428736-d67404019.bin.gz"

# Rapfi 指令集变体：runtime 只挑 avx512 / avx2 / sse
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


# ---- 应用数据 ----
datas = [
    (str(HERE / "qml"), "qml"),
    (str(HERE / "assets"), "assets"),
]
datas += _collect(HERE / "engines" / "bin", "engines/bin", _skip_bin)
datas.append((str(HERE / "engines" / "nets" / USED_NET), "engines/nets"))

# ---- Qt QML 模块：只带用到的（QML 的 import 不会被 Python 依赖分析捕捉）----
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

# PySide6 钩子会把整套 Qt 收进来，这里按名字剔除不用的组件
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="三棋对弈",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="三棋对弈")
