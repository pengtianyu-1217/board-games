"""五子棋规则（纯 Python，零 Qt）。

坐标 (x, y)：x 向右、y 向下，原点左上。
棋子：0 空，1 黑（先手），2 白。
自由规则：任一方先形成 5 连或以上即胜。
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import DRAW, EMPTY, FIRST, SECOND, opponent

_DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))


@dataclass(frozen=True)
class GomokuState:
    size: int = 15
    board: tuple = ()
    to_move: int = FIRST
    last_move: tuple | None = None
    winner: int = 0
    moves: tuple = ()
    win_line: tuple = ()
    forbidden: bool = False  # 黑棋禁手（Renju）；细判待实现

    def __post_init__(self):
        if not self.board:
            object.__setattr__(self, "board", (EMPTY,) * (self.size * self.size))

    # ---------- 查询 ----------
    def index(self, x: int, y: int) -> int:
        return y * self.size + x

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def cell(self, x: int, y: int) -> int:
        return self.board[self.index(x, y)]

    @property
    def is_over(self) -> bool:
        return self.winner != 0

    @property
    def move_count(self) -> int:
        return len(self.moves)

    def stones(self):
        for y in range(self.size):
            for x in range(self.size):
                v = self.board[self.index(x, y)]
                if v:
                    yield x, y, v

    def legal_moves(self):
        return [(x, y) for y in range(self.size) for x in range(self.size)
                if self.board[self.index(x, y)] == EMPTY]

    def is_legal(self, move):
        if self.winner:
            return False
        x, y = move
        return self.inside(x, y) and self.cell(x, y) == EMPTY

    # ---------- 走子 ----------
    def play(self, move):
        x, y = move
        if self.winner:
            raise ValueError("对局已结束")
        if not self.inside(x, y) or self.cell(x, y) != EMPTY:
            raise ValueError(f"非法落子：{move}")
        b = list(self.board)
        b[self.index(x, y)] = self.to_move
        line = self._win_line_at(b, x, y, self.to_move)
        winner = 0
        if line:
            if self.forbidden and self.to_move == FIRST and len(line) >= 6:
                winner = SECOND          # 黑棋长连禁手判负
            else:
                winner = self.to_move
        elif all(v != EMPTY for v in b):
            winner = DRAW
        return GomokuState(
            size=self.size,
            board=tuple(b),
            to_move=opponent(self.to_move),
            last_move=(x, y),
            winner=winner,
            moves=self.moves + ((x, y),),
            win_line=tuple(line),
            forbidden=self.forbidden,
        )

    def _win_line_at(self, board, x, y, player):
        best = []
        for dx, dy in _DIRS:
            pts = [(x, y)]
            for s in (1, -1):
                cx, cy = x + dx * s, y + dy * s
                while self.inside(cx, cy) and board[self.index(cx, cy)] == player:
                    pts.append((cx, cy))
                    cx += dx * s
                    cy += dy * s
            # 取最长的一条：同时成五与长连时以长连（≥6）为准
            if len(pts) >= 5 and len(pts) > len(best):
                best = sorted(pts, key=lambda p: (p[0] * dx + p[1] * dy))
        return best


def new_game(size: int = 15, forbidden: bool = False) -> GomokuState:
    return GomokuState(size=size, forbidden=forbidden)
