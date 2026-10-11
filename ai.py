"""占位 AI：未接外部引擎时的兜底，随难度调整。

引擎就绪后由 engines/ 层接管；这里保证没有引擎也能完整跑通对局与测试。
`level`：0 简单 / 1 普通 / 2 困难。

五子棋用「形状打分」（连子数 + 开放端）做攻防，能识别活四/冲四/活三并主动做杀，
比原来的最近邻随机强得多——即便外部引擎不可用，也是能下的对手。
"""

from __future__ import annotations

import random

from core.games import xiangqi as xiangqi_mod
from core.games.base import opponent

_DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))

# 形状分值：键 (连子数, 开放端数)。min(连子数,5) 归一。
_SHAPE = {
    (5, 2): 10 ** 7, (5, 1): 10 ** 7, (5, 0): 10 ** 7,   # 成五
    (4, 2): 10 ** 6,      # 活四：必胜
    (4, 1): 10 ** 4,      # 冲四
    (3, 2): 10 ** 4,      # 活三
    (3, 1): 300,
    (2, 2): 320,
    (2, 1): 40,
    (1, 2): 8,
    (1, 1): 2,
}


def choose_move(game, state, level=1):
    if game == "gomoku":
        return _gomoku(state, level)
    moves = state.legal_moves()
    if not moves:
        return None
    if game == "go":
        return _go(state, moves, level)
    return _xiangqi(state, moves, level)


# ---------------------------------------------------------------- 五子棋
def _would_win(board, size, x, y, player):
    idx = lambda a, b: b * size + a
    if board[idx(x, y)] != 0:
        return False
    for dx, dy in _DIRS:
        cnt = 1
        for s in (1, -1):
            cx, cy = x + dx * s, y + dy * s
            while 0 <= cx < size and 0 <= cy < size and board[idx(cx, cy)] == player:
                cnt += 1
                cx += dx * s
                cy += dy * s
        if cnt >= 5:
            return True
    return False


def _placed_value(board, size, x, y, player):
    """若 player 落子在 (x,y)，四个方向形成的威胁总分。"""
    total = 0
    for dx, dy in _DIRS:
        count = 1
        open_ends = 0
        for sign in (1, -1):
            cx, cy = x + dx * sign, y + dy * sign
            while 0 <= cx < size and 0 <= cy < size and board[cy * size + cx] == player:
                count += 1
                cx += dx * sign
                cy += dy * sign
            if 0 <= cx < size and 0 <= cy < size and board[cy * size + cx] == 0:
                open_ends += 1
        total += _SHAPE.get((min(count, 5), open_ends), 0)
    return total


def _has_neighbour(board, size, x, y, radius):
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            cx, cy = x + dx, y + dy
            if 0 <= cx < size and 0 <= cy < size and board[cy * size + cx] != 0:
                return True
    return False


def _gomoku(state, level):
    size = state.size
    board = state.board
    moves = state.legal_moves()
    if not moves:
        return None
    me = state.to_move
    opp = opponent(me)

    if not any(board):                        # 空盘：占天元
        c = size // 2
        return (c, c)

    for m in moves:                           # 直接连五
        if _would_win(board, size, m[0], m[1], me):
            return m
    for m in moves:                           # 堵对手连五
        if _would_win(board, size, m[0], m[1], opp):
            return m

    radius = 2 if level >= 1 else 1
    cand = [m for m in moves if _has_neighbour(board, size, m[0], m[1], radius)]
    if not cand:
        cand = moves

    best, best_score = None, None
    for m in cand:
        x, y = m
        atk = _placed_value(board, size, x, y, me)
        dfn = _placed_value(board, size, x, y, opp)
        score = atk * 1.2 + dfn
        if level >= 2:
            score -= 0.001 * (abs(x - size // 2) + abs(y - size // 2))  # 略偏中心
        if best_score is None or score > best_score:
            best, best_score = m, score
    return best


# ---------------------------------------------------------------- 围棋
def _go(state, moves, level):
    if level <= 0:
        return random.choice(moves)
    stones = [(x, y) for y in range(state.size) for x in range(state.size)
              if state.board[y * state.size + x]]
    if not stones:
        c = state.size // 2
        return (c, c) if state.is_legal((c, c)) else random.choice(moves)
    moves.sort(key=lambda m: min(abs(m[0] - s[0]) + abs(m[1] - s[1]) for s in stones))
    k = 1 if level >= 2 else 4
    return moves[min(len(moves) - 1, random.randint(0, k - 1))]


# ---------------------------------------------------------------- 象棋
def _xiangqi(state, moves, level):
    if level <= 0:
        return random.choice(moves)
    board = state.board

    def score(mv):
        (_, _), (tx, ty) = mv
        s = 0
        if board[ty * 9 + tx] != ".":
            s += 10
        if level >= 2:
            try:
                if xiangqi_mod.is_check(_apply(board, mv), opponent(state.to_move)):
                    s += 6
            except Exception:
                pass
        return s

    best = max(score(m) for m in moves)
    pool = [m for m in moves if score(m) == best]
    return random.choice(pool)


def _apply(board, move):
    nb = list(board)
    (fx, fy), (tx, ty) = move
    nb[ty * 9 + tx] = nb[fy * 9 + fx]
    nb[fy * 9 + fx] = "."
    return tuple(nb)
