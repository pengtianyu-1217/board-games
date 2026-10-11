"""中国象棋规则（纯 Python，零 Qt）。

棋盘 9 列 × 10 行；坐标 (x, y)：x 向右 0..8，y 向下 0..9。
红方（先手）在下（y=5..9），黑方在上（y=0..4）。

棋子字符：红方大写、黑方小写，'.' 为空。
    K 将/帅   A 士/仕   B 象/相   N 马   R 车   C 炮   P 兵/卒
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .base import DRAW, EMPTY, FIRST, SECOND, opponent

W, H = 9, 10

INITIAL = (
    "rnbakabnr"
    "........."
    ".c.....c."
    "p.p.p.p.p"
    "........."
    "........."
    "P.P.P.P.P"
    ".C.....C."
    "........."
    "RNBAKABNR"
)

_ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_KNIGHT = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
_ELEPHANT = ((2, 2), (2, -2), (-2, 2), (-2, -2))


def _idx(x, y):
    return y * W + x


def _color(ch):
    if ch == ".":
        return 0
    return FIRST if ch.isupper() else SECOND


def _in_palace(x, y, player):
    if not (3 <= x <= 5):
        return False
    return (7 <= y <= 9) if player == FIRST else (0 <= y <= 2)


# ---------------------------------------------------------------- 走子生成
def _push(out, board, x, y, tx, ty, player):
    if not (0 <= tx < W and 0 <= ty < H):
        return
    if _color(board[_idx(tx, ty)]) != player:
        out.append(((x, y), (tx, ty)))


def _moves_rook(board, x, y, player, out):
    for dx, dy in _ORTHO:
        cx, cy = x + dx, y + dy
        while 0 <= cx < W and 0 <= cy < H:
            t = board[_idx(cx, cy)]
            if t == ".":
                out.append(((x, y), (cx, cy)))
            else:
                if _color(t) != player:
                    out.append(((x, y), (cx, cy)))
                break
            cx += dx
            cy += dy


def _moves_cannon(board, x, y, player, out):
    for dx, dy in _ORTHO:
        cx, cy = x + dx, y + dy
        screen = False
        while 0 <= cx < W and 0 <= cy < H:
            t = board[_idx(cx, cy)]
            if not screen:
                if t == ".":
                    out.append(((x, y), (cx, cy)))
                else:
                    screen = True  # 找到炮架，之后只能吃第一个子
            else:
                if t != ".":
                    if _color(t) != player:
                        out.append(((x, y), (cx, cy)))
                    break
            cx += dx
            cy += dy


def _moves_horse(board, x, y, player, out):
    for dx, dy in _KNIGHT:
        tx, ty = x + dx, y + dy
        if not (0 <= tx < W and 0 <= ty < H):
            continue
        if abs(dx) == 2:  # 蹩马腿：横向两格，绊点是中间格
            bx, by = x + (1 if dx > 0 else -1), y
        else:
            bx, by = x, y + (1 if dy > 0 else -1)
        if board[_idx(bx, by)] != ".":
            continue
        if _color(board[_idx(tx, ty)]) != player:
            out.append(((x, y), (tx, ty)))


def _moves_elephant(board, x, y, player, out):
    for dx, dy in _ELEPHANT:
        tx, ty = x + dx, y + dy
        if not (0 <= tx < W and 0 <= ty < H):
            continue
        if player == FIRST and ty < 5:  # 红象不过河
            continue
        if player == SECOND and ty > 4:  # 黑象不过河
            continue
        if board[_idx(x + dx // 2, y + dy // 2)] != ".":  # 塞象眼
            continue
        if _color(board[_idx(tx, ty)]) != player:
            out.append(((x, y), (tx, ty)))


def _moves_advisor(board, x, y, player, out):
    for dx, dy in _DIAG:
        tx, ty = x + dx, y + dy
        if _in_palace(tx, ty, player) and _color(board[_idx(tx, ty)]) != player:
            out.append(((x, y), (tx, ty)))


def _moves_king(board, x, y, player, out):
    for dx, dy in _ORTHO:
        tx, ty = x + dx, y + dy
        if _in_palace(tx, ty, player) and _color(board[_idx(tx, ty)]) != player:
            out.append(((x, y), (tx, ty)))


def _moves_pawn(board, x, y, player, out):
    fwd = -1 if player == FIRST else 1  # 红兵向上（y 减小）
    _push(out, board, x, y, x, y + fwd, player)
    crossed = (player == FIRST and y <= 4) or (player == SECOND and y >= 5)
    if crossed:
        _push(out, board, x, y, x - 1, y, player)
        _push(out, board, x, y, x + 1, y, player)


_DISPATCH = {
    "R": _moves_rook, "C": _moves_cannon, "N": _moves_horse,
    "B": _moves_elephant, "A": _moves_advisor, "K": _moves_king, "P": _moves_pawn,
}


def pseudo_moves(board, player):
    return list(_pseudo_moves(board, player))


@lru_cache(maxsize=8192)
def _pseudo_moves(board, player):
    out = []
    for y in range(H):
        for x in range(W):
            ch = board[_idx(x, y)]
            if ch != "." and _color(ch) == player:
                _DISPATCH[ch.upper()](board, x, y, player, out)
    return tuple(out)


# ---------------------------------------------------------------- 将军判定
@lru_cache(maxsize=8192)
def king_pos(board, player):
    target = "K" if player == FIRST else "k"
    try:
        i = board.index(target)
    except ValueError:
        return None
    return i % W, i // W


@lru_cache(maxsize=8192)
def kings_face(board):
    rp = king_pos(board, FIRST)
    bp = king_pos(board, SECOND)
    if rp is None or bp is None:
        return False
    rx, ry = rp
    bx, by = bp
    if rx != bx:
        return False
    for y in range(min(ry, by) + 1, max(ry, by)):
        if board[_idx(rx, y)] != ".":
            return False
    return True


@lru_cache(maxsize=8192)
def is_attacked(board, tx, ty, by_player):
    return any(t == (tx, ty) for _, t in _pseudo_moves(board, by_player))


def is_check(board, player):
    """player 一方是否正被将军。"""
    kp = king_pos(board, player)
    if kp is None:
        return False
    return is_attacked(board, kp[0], kp[1], opponent(player))


# ---------------------------------------------------------------- 杀法术语
def attackers_of(board, tx, ty, by_player):
    """攻击 (tx,ty) 的一方棋子：返回 [((x,y), 棋子字符)]。"""
    out = []
    for (fx, fy), (mx, my) in _pseudo_moves(board, by_player):
        if (mx, my) == (tx, ty):
            out.append(((fx, fy), board[_idx(fx, fy)]))
    return out


def _two_cannons_on_king_line(board, winner, kx, ky):
    """老将所在纵/横线上是否有胜方两门炮（重炮）。"""
    target = "C" if winner == FIRST else "c"
    for dx, dy in _ORTHO:
        cx, cy = kx + dx, ky + dy
        count = 0
        while 0 <= cx < W and 0 <= cy < H:
            if board[_idx(cx, cy)] == target:
                count += 1
                if count >= 2:
                    return True
            cx += dx
            cy += dy
    return False


def _king_smothered(board, loser, kx, ky):
    """老将相邻的宫内点是否全被自己的子堵死（闷宫的必要条件）。"""
    for dx, dy in _ORTHO:
        tx, ty = kx + dx, ky + dy
        if not _in_palace(tx, ty, loser):
            continue
        ch = board[_idx(tx, ty)]
        if ch == "." or _color(ch) != loser:
            return False
    return True


def _horse_controls_king(board, winner, kx, ky):
    """胜方是否有马控制老将旁边的点（马后炮里的「马」）。"""
    target = "N" if winner == FIRST else "n"
    for (fx, fy), (tx, ty) in _pseudo_moves(board, winner):
        if board[_idx(fx, fy)] != target:
            continue
        if abs(tx - kx) + abs(ty - ky) == 1:
            return True
    return False


def mate_term(board, winner):
    """胜方将死对方时的杀法术语；拿不准就回退「将死 / 困毙」。"""
    loser = opponent(winner)
    if not is_check(board, loser):
        return "困毙"
    kp = king_pos(board, loser)
    if kp is None:
        return "将死"
    kx, ky = kp
    kinds = {ch.upper() for _pos, ch in attackers_of(board, kx, ky, winner)}
    if "C" in kinds:
        if _two_cannons_on_king_line(board, winner, kx, ky):
            return "重炮"
        if _king_smothered(board, loser, kx, ky):
            return "闷宫"
        if _horse_controls_king(board, winner, kx, ky):
            return "马后炮"
        return "将死"
    if "N" in kinds:
        return "卧槽马"
    return "将死"


def _fingerprint(board, to_move):
    return "".join(board) + ("w" if to_move == FIRST else "b")


def _repetition_result(positions, givers, fp):
    """三次重复局面的裁决：一方长将判负，否则判和。"""
    j = len(positions) - 1
    f = positions.index(fp)
    first_moves, second_moves = [], []
    for m in range(f + 1, j + 1):
        mover = FIRST if m % 2 == 1 else SECOND
        checked = givers[m - 1] != 0
        (first_moves if mover == FIRST else second_moves).append(checked)
    a = bool(first_moves) and all(first_moves)
    b = bool(second_moves) and all(second_moves)
    if a and not b:
        return SECOND
    if b and not a:
        return FIRST
    return DRAW


def _apply(board, move):
    nb = list(board)
    (fx, fy), (tx, ty) = move
    nb[_idx(tx, ty)] = nb[_idx(fx, fy)]
    nb[_idx(fx, fy)] = "."
    return tuple(nb)


def legal_moves(board, player):
    return list(_legal_moves(board, player))


@lru_cache(maxsize=8192)
def _legal_moves(board, player):
    res = []
    for mv in _pseudo_moves(board, player):
        nb = _apply(board, mv)
        kpos = king_pos(nb, player)
        if kpos is None:
            continue
        kx, ky = kpos
        if is_attacked(nb, kx, ky, opponent(player)):
            continue
        if kings_face(nb):
            continue
        res.append(mv)
    return tuple(res)


# ---------------------------------------------------------------- 局面对象
@dataclass(frozen=True)
class XiangqiState:
    board: tuple = ()
    to_move: int = FIRST
    last_move: tuple | None = None
    winner: int = 0
    moves: tuple = ()
    positions: tuple = ()   # 局面指纹序列（含初始），用于重复/长将判定
    givers: tuple = ()      # 每一着的将军方（未将是 0）

    def __post_init__(self):
        if not self.board:
            object.__setattr__(self, "board", tuple(INITIAL))
        if not self.positions:
            object.__setattr__(
                self, "positions", (_fingerprint(self.board, self.to_move),))

    @property
    def is_over(self):
        return self.winner != 0

    @property
    def move_count(self):
        return len(self.moves)

    def piece_count(self):
        return sum(1 for c in self.board if c != ".")

    def legal_moves(self):
        return legal_moves(self.board, self.to_move)

    def play(self, move):
        if self.winner:
            raise ValueError("对局已结束")
        if move not in legal_moves(self.board, self.to_move):
            raise ValueError(f"非法着法：{move}")
        nb = _apply(self.board, move)
        mover = self.to_move
        nxt = opponent(mover)
        fp = _fingerprint(nb, nxt)
        positions = self.positions + (fp,)
        givers = self.givers + (mover if is_check(nb, nxt) else 0,)
        winner = 0
        if not legal_moves(nb, nxt):
            winner = mover          # 困毙/将死
        elif positions.count(fp) >= 3:
            winner = _repetition_result(positions, givers, fp)
        return XiangqiState(
            board=nb,
            to_move=nxt,
            last_move=move,
            winner=winner,
            moves=self.moves + (move,),
            positions=positions,
            givers=givers,
        )

    def to_fen(self):
        rows = []
        for y in range(H):
            row, empty = "", 0
            for x in range(W):
                c = self.board[_idx(x, y)]
                if c == ".":
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += c
            if empty:
                row += str(empty)
            rows.append(row)
        return "/".join(rows) + (" w" if self.to_move == FIRST else " b")


def new_game():
    return XiangqiState()
