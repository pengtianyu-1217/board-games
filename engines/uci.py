"""Pikafish（UCI 协议）——中国象棋。"""

from __future__ import annotations

from .base import EngineBase

FILES = "abcdefghi"


def uci_to_move(text):
    """'b0e2' -> ((1, 9), (4, 7))。"""
    text = (text or "").strip()
    if len(text) < 4:
        return None
    fx = FILES.index(text[0].lower())
    fy = 9 - int(text[1])
    tx = FILES.index(text[2].lower())
    ty = 9 - int(text[3])
    return (fx, fy), (tx, ty)


def move_to_uci(move):
    (fx, fy), (tx, ty) = move
    return "%s%d%s%d" % (FILES[fx], 9 - fy, FILES[tx], 9 - ty)


class UciEngine(EngineBase):
    def __init__(self, program, cwd=None, depth=8, movetime_ms=1000, parent=None):
        super().__init__("Pikafish", program, cwd=cwd, parent=parent)
        self.depth = depth
        self.movetime_ms = movetime_ms
        self.skill = 10

    def set_difficulty(self, level):
        level = max(0, min(2, int(level)))
        self.skill = (3, 10, 20)[level]
        self.movetime_ms = (300, 900, 1800)[level]

    def handshake(self):
        return [
            "uci",
            "setoption name Threads value 2",
            "setoption name Hash value 128",
            "isready",
        ]

    def request(self, state, time_ms=None):
        if self._proc is None and not self.start():
            return False
        self.send("setoption name Skill Level value %d" % self.skill)
        # UCI 语义：position fen <起点局面> moves <随后所有着法>
        # 必须是「走这些着法之前」的局面，所以固定用标准初始局面。
        from core.games import xiangqi as xiangqi_mod
        start_fen = xiangqi_mod.new_game().to_fen()
        if state.moves:
            history = " ".join(move_to_uci(m) for m in state.moves)
            self.send("position fen %s moves %s" % (start_fen, history))
        else:
            self.send("position fen %s" % start_fen)
        self.send("go movetime %d" % (time_ms or self.movetime_ms))
        return True

    def on_line(self, line):
        if line.startswith("bestmove"):
            parts = line.split()
            self.bestMove.emit(uci_to_move(parts[1]) if len(parts) > 1 else None)
