"""三棋规则层的公共常量。

阵营统一编号：1 = 先手（五子棋黑 / 象棋红 / 围棋黑），2 = 后手；
0 = 空 / 未决，3 = 和棋。规则层是纯 Python、零 Qt，可独立单测。
"""

EMPTY = 0
FIRST = 1
SECOND = 2
DRAW = 3


def opponent(player):
    return SECOND if player == FIRST else FIRST
