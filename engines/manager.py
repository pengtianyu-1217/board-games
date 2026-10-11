"""引擎管理：按棋种选择引擎；不可用时由控制器回退到占位 AI。

失败分两类：
- 硬失败（引擎文件缺失）：本会话不再尝试。
- 软失败（启动超时/协议异常）：允许重试一次，再失败才停用。
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal


def _engines_dir():
    # 打包（PyInstaller）后 bin/nets 随数据文件放在 _MEIPASS/engines 下
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "engines"
    return Path(__file__).resolve().parent


ROOT = _engines_dir()
BIN = ROOT / "bin"
NETS = ROOT / "nets"


def _cpu_flags():
    """Windows CPU 指令集能力（用于挑最合适的 Rapfi 构建）。"""
    flags = {"avx": False, "avx2": False, "avx512f": False}
    try:
        kernel32 = ctypes.windll.kernel32
        flags["avx"] = bool(kernel32.IsProcessorFeaturePresent(39))
        flags["avx2"] = bool(kernel32.IsProcessorFeaturePresent(40))
        flags["avx512f"] = bool(kernel32.IsProcessorFeaturePresent(41))
    except Exception:
        pass
    return flags


def _pick_rapfi():
    """按 CPU 能力挑 Rapfi：avx512 > avx2 > sse。

    在只支持 SSE 的机器上跑 avx2 版会直接崩溃，进而静默回退到很弱的占位 AI——
    这里显式挑选，避免那种「棋力突然变弱」的情况。
    """
    rapfi_dir = BIN / "rapfi"
    flags = _cpu_flags()
    if flags["avx512f"]:
        order = ("avx512", "avx2", "sse")
    elif flags["avx2"]:
        order = ("avx2", "sse")
    else:
        order = ("sse",)
    for tag in order:
        candidate = rapfi_dir / ("pbrain-rapfi-windows-%s.exe" % tag)
        if candidate.exists():
            return candidate
    found = sorted(rapfi_dir.glob("pbrain-rapfi-windows-*.exe"))
    return found[0] if found else rapfi_dir / "pbrain-rapfi-windows-avx2.exe"


KATAGO = BIN / "katago" / "katago.exe"
KATAGO_CFG = BIN / "katago" / "default_gtp.cfg"
# CPU 上跑卷积网（g170-b10c128）比变压器网（b10c384h6nbt）快约 50 倍，
# 同样时间内能搜几十倍的访问，实际棋力反而更高。
KATAGO_NET = NETS / "g170-b10c128-s197428736-d67404019.bin.gz"
PIKAFISH = BIN / "pikafish" / "Pikafish-Windows-x86-64-universal.exe"
RAPFI = _pick_rapfi()


class EngineManager(QObject):
    bestMove = Signal(str, object)      # (棋种, 着法)
    statusChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engines = {}
        self._active = None
        self._status = "内置 AI"
        self._failed = set()      # 硬失败，本会话不再尝试
        self._soft = {}           # 软失败计数，允许重试一次

    def _status_text(self):
        return self._status

    status = property(_status_text)

    # ---------------- 构建 ----------------
    def _build(self, game):
        if os.environ.get("BOARD_NO_ENGINE"):
            return None
        from .gtp import GtpEngine
        from .piskvork import PiskvorkEngine
        from .uci import UciEngine

        if game == "go":
            if not (KATAGO.exists() and KATAGO_CFG.exists() and KATAGO_NET.exists()):
                return None
            return GtpEngine(KATAGO, KATAGO_NET, KATAGO_CFG, size=19, visits=160,
                             cwd=str(KATAGO.parent))
        if game == "xiangqi":
            if not PIKAFISH.exists():
                return None
            return UciEngine(PIKAFISH, cwd=str(PIKAFISH.parent), movetime_ms=900)
        if game == "gomoku":
            if not RAPFI.exists():
                return None
            return PiskvorkEngine(RAPFI, cwd=str(RAPFI.parent), size=15)
        return None

    def _engine(self, game):
        if game in self._engines:
            return self._engines[game]
        if game in self._failed:
            return None
        eng = self._build(game)
        if eng is None:
            self._failed.add(game)
            return None
        eng.bestMove.connect(lambda mv, g=game: self._on_move(g, mv))
        eng.failed.connect(lambda msg, g=game: self._on_fail(g, msg))
        self._engines[game] = eng
        return eng

    # ---------------- 对外 ----------------
    def request(self, game, state, time_ms=1000, level=1):
        eng = self._engine(game)
        if eng is None:
            return False
        if self._active is not None and self._active is not eng:
            self._active.stop()
        self._active = eng
        try:
            eng.set_difficulty(level)
            ok = eng.request(state, time_ms)
        except Exception:
            ok = False
        if not ok:
            self._note_soft(game)
            return False
        self._set_status("%s 思考中" % eng.name)
        return True

    def engine_name(self, game):
        eng = self._engines.get(game)
        return eng.name if eng else None

    def prewarm(self, game):
        """提前拉起引擎（进程 + 模型加载 + 握手），把冷启动藏在对局准备阶段。"""
        if os.environ.get("BOARD_NO_ENGINE") or game in self._failed:
            return
        for g, eng in list(self._engines.items()):
            if g != game and eng is not self._active:
                eng.stop()
                del self._engines[g]
                self._soft.pop(g, None)
        eng = self._engine(game)
        if eng is None or eng.running:
            return
        try:
            if eng.start():
                self._set_status("%s 预热中" % eng.name)
        except Exception:
            self._note_soft(game)

    def shutdown(self):
        for eng in self._engines.values():
            eng.stop()
        self._engines.clear()
        self._active = None

    def note_timeout(self, game):
        """引擎单步超时：按软失败计数，累计两次后停用该引擎。

        由控制器看门狗调用，避免某个引擎卡住时界面一直停在「思考中」。
        """
        self._note_soft(game)

    def probe(self, game):
        """自检：报告该棋种引擎是否可用（供界面「检测引擎」按钮调用）。"""
        if os.environ.get("BOARD_NO_ENGINE"):
            return "已禁用引擎（BOARD_NO_ENGINE=1）"
        if game in self._failed:
            return "引擎本会话已停用（多次失败），正用内置 AI"
        eng = self._engine(game)
        if eng is None:
            return "未找到引擎文件，将用内置 AI"
        try:
            ok = eng.start()
        except Exception as exc:
            return "%s 启动异常：%s" % (eng.name, exc)
        if ok:
            return "%s 可用 · %s" % (eng.name, os.path.basename(str(eng.program)))
        return "%s 启动失败，将用内置 AI" % eng.name

    # ---------------- 内部 ----------------
    def _note_soft(self, game):
        n = self._soft.get(game, 0) + 1
        self._soft[game] = n
        if n >= 2:
            self._failed.add(game)
            eng = self._engines.pop(game, None)
            if eng is not None:
                if self._active is eng:
                    self._active = None
                eng.stop()

    def _on_move(self, game, move):
        self._soft.pop(game, None)
        self._set_status("就绪")
        self.bestMove.emit(game, move)

    def _on_fail(self, game, msg):
        self._note_soft(game)
        self._set_status(msg)
        self.bestMove.emit(game, None)

    def _set_status(self, text):
        if text != self._status:
            self._status = text
            self.statusChanged.emit(text)
