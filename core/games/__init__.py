"""三棋规则层（纯 Python，零 Qt）。"""

from . import go, gomoku, xiangqi
from .base import DRAW, EMPTY, FIRST, SECOND, opponent

__all__ = ["gomoku", "xiangqi", "go", "EMPTY", "FIRST", "SECOND", "DRAW", "opponent"]
