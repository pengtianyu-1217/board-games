import unittest

from core.games import gomoku, xiangqi
from core.games.base import DRAW, FIRST, SECOND
from core.games.xiangqi import _repetition_result


class RepetitionVerdictTest(unittest.TestCase):
    def test_plain_repetition_is_draw(self):
        # positions: A B A B A  ->  A 出现三次；双方都没将军
        givers = (0, 0, 0, 0)
        self.assertEqual(_repetition_result(("A", "B", "A", "B", "A"), givers, "A"), DRAW)

    def test_one_side_perpetual_check_loses(self):
        # 红（先手，奇数手）每步都将军，黑没有 -> 红判负
        givers = (FIRST, 0, FIRST, 0)
        self.assertEqual(_repetition_result(("A", "B", "A", "B", "A"), givers, "A"), SECOND)

    def test_both_checking_is_draw(self):
        givers = (FIRST, SECOND, FIRST, SECOND)
        self.assertEqual(_repetition_result(("A", "B", "A", "B", "A"), givers, "A"), DRAW)


class RepetitionIntegrationTest(unittest.TestCase):
    def test_real_threefold_is_draw(self):
        s = xiangqi.new_game()
        seq = [((1, 7), (4, 7)), ((0, 0), (0, 1)), ((4, 7), (1, 7)), ((0, 1), (0, 0)),
               ((1, 7), (4, 7)), ((0, 0), (0, 1)), ((4, 7), (1, 7)), ((0, 1), (0, 0))]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, DRAW)


class GomokuForbiddenTest(unittest.TestCase):
    SEQUENCE = [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5),
                (4, 0), (4, 5), (5, 0), (5, 5), (3, 0)]

    def test_overline_loses_under_forbidden(self):
        s = gomoku.new_game(15, forbidden=True)
        for m in self.SEQUENCE:
            s = s.play(m)
        self.assertEqual(s.winner, SECOND)   # 黑长连禁手，黑负

    def test_overline_wins_when_freestyle(self):
        s = gomoku.new_game(15)
        for m in self.SEQUENCE:
            s = s.play(m)
        self.assertEqual(s.winner, FIRST)


if __name__ == "__main__":
    unittest.main()
