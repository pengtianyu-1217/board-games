"""引擎自检：分别向三个引擎要一步棋，验证协议与坐标映射。

    python tools/engine_check.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

from core.games import go as go_mod  # noqa: E402
from core.games import gomoku as gomoku_mod  # noqa: E402
from core.games import xiangqi as xiangqi_mod  # noqa: E402
from engines import manager as M  # noqa: E402
from engines.gtp import GtpEngine  # noqa: E402
from engines.piskvork import PiskvorkEngine  # noqa: E402
from engines.uci import UciEngine  # noqa: E402

app = QCoreApplication([])
results = []
KEEP = []   # 持有引擎引用，避免被 GC 掉


def finish(tag, text):
    results.append("%-8s %s" % (tag, text))
    print(results[-1])
    QTimer.singleShot(200, next_step)


def check_xiangqi():
    s = xiangqi_mod.new_game()
    eng = UciEngine(M.PIKAFISH, cwd=str(M.PIKAFISH.parent), movetime_ms=800)
    eng.bestMove.connect(lambda mv: finish("XIANGQI", "move=%s legal=%s" % (
        mv, mv in s.legal_moves() if mv else False)))
    eng.failed.connect(lambda msg: finish("XIANGQI", "FAILED %s" % msg))
    if not eng.request(s, 800):
        finish("XIANGQI", "request failed")
    else:
        KEEP.append(eng)


def check_gomoku():
    # 黑在 y=3 连成四子，白（引擎）必须挡在 (2,3) 或 (7,3)
    s = gomoku_mod.new_game(15)
    for m in [(3, 3), (3, 0), (4, 3), (4, 0), (5, 3), (5, 0), (6, 3)]:
        s = s.play(m)
    eng = PiskvorkEngine(M.RAPFI, cwd=str(M.RAPFI.parent), size=15)
    eng.bestMove.connect(lambda mv: finish("GOMOKU", "move=%s blocks=%s" % (
        mv, mv in ((2, 3), (7, 3)))))
    eng.failed.connect(lambda msg: finish("GOMOKU", "FAILED %s" % msg))
    if not eng.request(s):
        finish("GOMOKU", "request failed")
    else:
        KEEP.append(eng)


def check_go():
    s = go_mod.new_game(19)
    eng = GtpEngine(M.KATAGO, M.KATAGO_NET, M.KATAGO_CFG, size=19, visits=60,
                    cwd=str(M.KATAGO.parent))
    eng.bestMove.connect(lambda mv: finish("GO", "move=%s on_board=%s" % (
        mv, mv is not None and 0 <= mv[0] < 19 and 0 <= mv[1] < 19)))
    eng.failed.connect(lambda msg: finish("GO", "FAILED %s" % msg))
    if not eng.request(s):
        finish("GO", "request failed")
    else:
        KEEP.append(eng)


def check_controller():
    from controller import GameController
    c = GameController()
    c._engine.bestMove.connect(lambda g, m: print("DEBUG manager.bestMove", g, m))
    c._engine.statusChanged.connect(lambda s: print("DEBUG engine status", s))
    c.newGame("xiangqi")
    c.clickCell(0, 6)   # 选红兵
    c.clickCell(0, 5)   # 走一步，轮到引擎
    tries = {"n": 0}

    def poll():
        if c.moveCount >= 2:
            finish("CONTROLLER", "human+engine moves=%d status=%s" % (c.moveCount, c.status))
            KEEP.append(c)
            return
        tries["n"] += 1
        if tries["n"] > 150:
            finish("CONTROLLER", "timeout, moves=%d" % c.moveCount)
            return
        QTimer.singleShot(100, poll)

    QTimer.singleShot(100, poll)


steps = [check_xiangqi, check_gomoku, check_go, check_controller]


def next_step():
    if not steps:
        for obj in KEEP:
            if hasattr(obj, "shutdown"):
                obj.shutdown()
            elif hasattr(obj, "stop"):
                obj.stop()
        print("\n=== engine check done ===")
        app.quit()
        return
    steps.pop(0)()


QTimer.singleShot(100, next_step)
QTimer.singleShot(60000, app.quit)
app.exec()
