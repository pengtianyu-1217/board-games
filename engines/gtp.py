"""KataGo（GTP 协议）——围棋。"""

from __future__ import annotations

from .base import MOVE_PASS, MOVE_RESIGN, EngineBase

COLUMNS = "ABCDEFGHJKLMNOPQRST"  # GTP 跳过字母 I

# 用卷积网 g170-b10c128（见 manager.KATAGO_NET）后每访问约 25ms，
# 有充裕预算；难度同时给时间与访问上限，谁先到谁停。
_VISITS_BY_LEVEL = (100, 400, 1200)
_TIME_BY_LEVEL = (0.8, 2.0, 4.0)   # 秒：简单 / 普通 / 困难


def gtp_to_xy(text, size):
    text = (text or "").strip().upper()
    if not text or text in ("PASS", "RESIGN"):
        return None
    col = COLUMNS.index(text[0])
    row = int(text[1:])
    return col, size - row


def xy_to_gtp(x, y, size):
    return COLUMNS[x] + str(size - y)


class GtpEngine(EngineBase):
    def __init__(self, program, model, config, size=19, komi=7.5, visits=800,
                 max_time=3.0, cwd=None, parent=None):
        super().__init__(
            "KataGo", program,
            ["gtp", "-model", str(model), "-config", str(config)],
            cwd=cwd, parent=parent,
        )
        self.size = size
        self.komi = komi
        self.visits = visits
        self.max_time = max_time
        self._color = "B"

    def set_difficulty(self, level):
        level = max(0, min(2, int(level)))
        self.visits = _VISITS_BY_LEVEL[level]
        self.max_time = _TIME_BY_LEVEL[level]

    def handshake(self):
        return [
            "boardsize %d" % self.size,
            "komi %s" % self.komi,
            "kata-set-param maxVisits %d" % self.visits,
            "kata-set-param maxTime %s" % self.max_time,
        ]

    def request(self, state, time_ms=1200):
        if self._proc is None and not self.start():
            return False
        self.send("kata-set-param maxVisits %d" % self.visits)
        self.send("kata-set-param maxTime %s" % self.max_time)
        self.send("clear_board")
        self.send("komi %s" % getattr(state, "komi", self.komi))
        player = 1
        for mv in state.moves:
            if mv is None:
                self.send("play %s pass" % ("B" if player == 1 else "W"))
            else:
                self.send("play %s %s" % ("B" if player == 1 else "W",
                                          xy_to_gtp(mv[0], mv[1], self.size)))
            player = 3 - player
        self._color = "B" if state.to_move == 1 else "W"
        self.send("genmove %s" % self._color, callback=self._on_move)
        return True

    def _on_move(self, line):
        ok = line.startswith("=")
        payload = line[1:].strip()
        if not ok:
            self.failed.emit("KataGo: %s" % payload)
            self.bestMove.emit(None)
            return
        upper = payload.upper()
        if upper == "PASS":
            self.bestMove.emit(MOVE_PASS)      # 引擎主动停一手
        elif upper == "RESIGN":
            self.bestMove.emit(MOVE_RESIGN)    # 引擎认输
        else:
            self.bestMove.emit(gtp_to_xy(payload, self.size))
