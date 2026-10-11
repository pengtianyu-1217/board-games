"""围棋规则（纯 Python，零 Qt）。

坐标 (x, y)：x 向右、y 向下。棋盘 size×size（9 / 13 / 19）。
棋子：0 空，1 黑（先手），2 白。默认中国规则（数子），白贴 7.5 目。
允许停一手；连续两手停着即终局。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .base import DRAW, EMPTY, FIRST, SECOND, opponent


def _idx(size, x, y):
    return y * size + x


def _neighbors(size, x, y):
    if x > 0:
        yield x - 1, y
    if x < size - 1:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y < size - 1:
        yield x, y + 1


def _group(board, size, x, y):
    """返回 (同色棋串坐标集合, 气坐标集合)。"""
    color = board[_idx(size, x, y)]
    seen = {(x, y)}
    stack = [(x, y)]
    libs = set()
    while stack:
        cx, cy = stack.pop()
        for nx, ny in _neighbors(size, cx, cy):
            v = board[_idx(size, nx, ny)]
            if v == EMPTY:
                libs.add((nx, ny))
            elif v == color and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen, libs


def group_and_liberties(board, size, x, y):
    """对外：返回 (同色棋串坐标集合, 气坐标集合)。用于「打吃」判定等。"""
    return _group(board, size, x, y)


def _remove_dead(board, size, color):
    """提掉 board（就地修改）中 color 的无气棋串，返回 (提子数, 被提位置列表)。"""
    captured = []
    checked = set()
    for y in range(size):
        for x in range(size):
            if board[_idx(size, x, y)] == color and (x, y) not in checked:
                stones, libs = _group(board, size, x, y)
                checked |= stones
                if not libs:
                    for sx, sy in stones:
                        board[_idx(size, sx, sy)] = EMPTY
                    captured.extend(stones)
    return len(captured), captured


def _flood_empty(board, size, start, visited):
    """空区洪泛，返回 (该空区坐标集合, 边界唯一颜色 或 0 表示双方都有)。"""
    seen = {start}
    stack = [start]
    border = 0
    while stack:
        cx, cy = stack.pop()
        for nx, ny in _neighbors(size, cx, cy):
            v = board[_idx(size, nx, ny)]
            if v == EMPTY:
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
            else:
                if border == 0:
                    border = v
                elif border != v:
                    border = -1  # 双方都有
    visited |= seen
    return seen, (border if border > 0 else 0)


def compute_score(board, size, komi):
    """中国规则数子：己方棋子数 + 己方独占空区。返回 (黑分, 白分含贴目)。"""
    first = sum(1 for v in board if v == FIRST)
    second = sum(1 for v in board if v == SECOND)
    visited = set()
    for y in range(size):
        for x in range(size):
            if board[_idx(size, x, y)] == EMPTY and (x, y) not in visited:
                region, color = _flood_empty(board, size, (x, y), visited)
                if color == FIRST:
                    first += len(region)
                elif color == SECOND:
                    second += len(region)
    return first, second + komi


@dataclass(frozen=True)
class GoState:
    size: int = 19
    board: tuple = ()
    to_move: int = FIRST
    ko: tuple | None = None
    captures: tuple = (0, 0)   # (先手提子数, 后手提子数)
    passes: int = 0
    last_move: tuple | None = None
    winner: int = 0
    komi: float = 7.5
    moves: tuple = ()
    score: tuple | None = None

    def __post_init__(self):
        if not self.board:
            object.__setattr__(self, "board", (EMPTY,) * (self.size * self.size))

    # ---------- 查询 ----------
    def cell(self, x, y):
        return self.board[_idx(self.size, x, y)]

    @property
    def is_over(self):
        return self.winner != 0

    @property
    def move_count(self):
        return len(self.moves)

    def empties(self):
        return [(x, y) for y in range(self.size) for x in range(self.size)
                if self.board[_idx(self.size, x, y)] == EMPTY]

    def is_legal(self, move):
        if self.winner:
            return False
        if move is None:
            return True
        x, y = move
        size = self.size
        if not (0 <= x < size and 0 <= y < size):
            return False
        if self.board[_idx(size, x, y)] != EMPTY:
            return False
        if self.ko == (x, y):
            return False
        b = list(self.board)
        b[_idx(size, x, y)] = self.to_move
        _remove_dead(b, size, opponent(self.to_move))
        _, libs = _group(b, size, x, y)
        return bool(libs)

    def legal_moves(self):
        return [pt for pt in self.empties() if self.is_legal(pt)]

    # ---------- 走子 ----------
    def play(self, move):
        if self.winner:
            raise ValueError("对局已结束")
        if move is None:
            return self._pass()
        x, y = move
        size = self.size
        if not (0 <= x < size and 0 <= y < size) or self.board[_idx(size, x, y)] != EMPTY:
            raise ValueError(f"非法落子：{move}")
        if self.ko == (x, y):
            raise ValueError("打劫：此处暂不能落子")

        b = list(self.board)
        b[_idx(size, x, y)] = self.to_move
        captured, captured_pos = _remove_dead(b, size, opponent(self.to_move))
        own, libs = _group(b, size, x, y)
        if not libs:
            raise ValueError("禁着点：自杀")

        ko = None
        if captured == 1 and len(own) == 1 and len(libs) == 1:
            ko = captured_pos[0]

        caps = list(self.captures)
        caps[self.to_move - 1] += captured
        return replace(
            self,
            board=tuple(b),
            to_move=opponent(self.to_move),
            ko=ko,
            captures=tuple(caps),
            passes=0,
            last_move=(x, y),
            moves=self.moves + ((x, y),),
        )

    def _pass(self):
        passes = self.passes + 1
        moves = self.moves + (None,)
        if passes >= 2:
            sc = compute_score(self.board, self.size, self.komi)
            if sc[0] > sc[1]:
                winner = FIRST
            elif sc[1] > sc[0]:
                winner = SECOND
            else:
                winner = DRAW
            return replace(self, to_move=opponent(self.to_move), passes=passes,
                           winner=winner, ko=None, last_move=None, score=sc, moves=moves)
        return replace(self, to_move=opponent(self.to_move), passes=passes,
                       ko=None, last_move=None, moves=moves)

    # ---------- SGF ----------
    def to_sgf(self):
        def coord(pt):
            if pt is None:
                return ""
            x, y = pt
            return chr(ord("a") + x) + chr(ord("a") + y)

        head = f"(;GM[1]FF[4]SZ[{self.size}]KM[{self.komi}]"
        body = "".join(
            f";{'B' if (i % 2 == 0) else 'W'}[{coord(m)}]"
            for i, m in enumerate(self.moves)
        )
        return head + body + ")"


def new_game(size: int = 19, komi: float = 7.5):
    return GoState(size=size, komi=komi)
