"""Rapfi（Piskvork / Gomocup 协议）——五子棋。

坐标映射用「发送与解析同一个变换」，即引擎坐标 = 我们把棋盘做一次上下翻转。
只要收发一致，等价棋局下引擎给出的着法映射回来就是正确的；具体原点约定
由 tools/engine_check.py 实测确认。
"""

from __future__ import annotations

import re

from .base import EngineBase

_MOVE_RE = re.compile(r"^\s*(-?\d+)\s*,\s*(-?\d+)\s*$")


class PiskvorkEngine(EngineBase):
    def __init__(self, program, cwd=None, size=15, flip_y=True, parent=None):
        super().__init__("Rapfi", program, cwd=cwd, parent=parent)
        self.size = size
        self.flip_y = flip_y
        self.timeout = 1000

    def set_difficulty(self, level):
        self.timeout = (300, 1000, 2500)[max(0, min(2, int(level)))]

    def _map(self, x, y):
        return x, (self.size - 1 - y) if self.flip_y else y

    def handshake(self):
        return ["START %d" % self.size]

    def quit_command(self):
        return "END"

    def request(self, state, time_ms=None):
        if self._proc is None and not self.start():
            return False
        self.send("INFO timeout_turn %d" % self.timeout)
        self.send("BOARD")
        engine_color = state.to_move
        for i, mv in enumerate(state.moves):
            player = 1 if i % 2 == 0 else 2
            ex, ey = self._map(mv[0], mv[1])
            self.send("%d,%d,%d" % (ex, ey, 1 if player == engine_color else 2))
        self.send("DONE")
        self.send("BEGIN" if not state.moves else "TURN")
        return True

    def on_line(self, line):
        self._resolve(line)
        m = _MOVE_RE.match(line)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            self.bestMove.emit(self._map(x, y))
