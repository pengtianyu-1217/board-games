"""棋谱记谱（纯 Python，零 Qt）。

- 象棋：中文纵线记谱（炮二平五 / 马8进7），带前/后、进/退/平。
- 围棋 / 五子棋：坐标记谱（D4 / H8）。

只依赖规则层常量，可脱离 GUI 单测。
"""

from __future__ import annotations

from .base import FIRST, SECOND

_CN = "一二三四五六七八九"
_GO_COLS = "ABCDEFGHJKLMNOPQRST"      # GTP 跳字母 I
_NAMES = {
    "K": "帅", "A": "仕", "B": "相", "N": "马", "R": "车", "C": "炮", "P": "兵",
}
_NAMES_BLACK = {
    "K": "将", "A": "士", "B": "象", "N": "马", "R": "车", "C": "炮", "P": "卒",
}


def _num(player, n):
    """红用汉字数字，黑用阿拉伯数字。"""
    if player == FIRST:
        if 1 <= n <= 9:
            return _CN[n - 1]
        return str(n)
    return str(n)


def _file_num(player, x, width=9):
    """红：右侧为一路（x 大 → 数字小）；黑：左侧为 1 路。"""
    return (width - x) if player == FIRST else (x + 1)


def _straight(up):
    """直线走子（进/退后缀是步数）还是斜线走子（后缀是目标纵线）。"""
    return up in ("R", "C", "P", "K")


def xiangqi_move_text(board, move):
    """中文纵线记谱。board 为走此着之前的 90 字符局面。"""
    (fx, fy), (tx, ty) = move
    ch = board[fy * 9 + fx]
    player = FIRST if ch.isupper() else SECOND
    up = ch.upper()
    name = (_NAMES if player == FIRST else _NAMES_BLACK)[up]

    file_pieces = [y for y in range(10) if board[y * 9 + fx] == ch]
    prefix = ""
    if len(file_pieces) >= 2:
        ordered = sorted(file_pieces) if player == FIRST else sorted(file_pieces, reverse=True)
        idx = ordered.index(fy)
        if len(ordered) == 2:
            prefix = "前" if idx == 0 else "后"
        elif len(ordered) == 3:
            prefix = ("前", "中", "后")[idx]
        else:
            prefix = _num(player, idx + 1)

    head = (prefix + name) if prefix else (name + _num(player, _file_num(player, fx)))

    if ty == fy:
        verb = "平" + _num(player, _file_num(player, tx))
    else:
        forward = (ty < fy) if player == FIRST else (ty > fy)
        verb = "进" if forward else "退"
        if _straight(up):
            verb += _num(player, abs(ty - fy))
        else:
            verb += _num(player, _file_num(player, tx))
    return head + verb


def coord_text(game, move, size):
    """围棋（GTP 坐标，跳 I）与五子棋（字母 + 行号）的坐标记谱。"""
    if move is None:
        return "停一手"
    x, y = move
    if game == "go":
        if 0 <= x < len(_GO_COLS):
            return _GO_COLS[x] + str(size - y)
        return f"{x},{y}"
    col = chr(ord("A") + x) if x < 26 else str(x)
    return col + str(y + 1)


def move_text(game, board, move, size):
    """统一入口：象棋走中文记谱，其余走坐标。"""
    if game == "xiangqi":
        return xiangqi_move_text(board, move)
    return coord_text(game, move, size)
