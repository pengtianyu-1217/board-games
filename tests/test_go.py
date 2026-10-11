import unittest

from core.games import go
from core.games.base import DRAW, FIRST, SECOND


def mkboard(size, spec):
    b = [0] * (size * size)
    for (x, y), v in spec.items():
        b[y * size + x] = v
    return tuple(b)


class GoRulesTest(unittest.TestCase):
    def test_new_game(self):
        s = go.new_game(19)
        self.assertEqual(s.size, 19)
        self.assertEqual(s.to_move, FIRST)
        self.assertEqual(len(s.board), 361)
        self.assertEqual(sum(s.board), 0)

    def test_place_and_switch(self):
        s = go.new_game(9)
        s = s.play((4, 4))
        self.assertEqual(s.cell(4, 4), FIRST)
        self.assertEqual(s.to_move, SECOND)
        self.assertEqual(s.last_move, (4, 4))

    def test_illegal_occupied(self):
        s = go.new_game(9).play((4, 4))
        with self.assertRaises(ValueError):
            s.play((4, 4))

    def test_capture_single_stone(self):
        size = 9
        spec = {
            (1, 1): SECOND,
            (0, 1): FIRST, (1, 0): FIRST, (2, 1): FIRST,
        }
        s = go.GoState(size=size, board=mkboard(size, spec), to_move=FIRST)
        s = s.play((1, 2))  # 黑补最后一口气，提掉白 (1,1)
        self.assertEqual(s.cell(1, 1), 0)
        self.assertEqual(s.captures[0], 1)  # 黑提子数

    def test_suicide_forbidden(self):
        size = 9
        spec = {(1, 0): SECOND, (0, 1): SECOND}
        s = go.GoState(size=size, board=mkboard(size, spec), to_move=FIRST)
        self.assertFalse(s.is_legal((0, 0)))
        with self.assertRaises(ValueError):
            s.play((0, 0))

    def test_ko_recapture_forbidden(self):
        size = 9
        spec = {
            (1, 0): FIRST, (2, 0): SECOND,
            (0, 1): FIRST, (1, 1): SECOND, (3, 1): SECOND,
            (1, 2): FIRST, (2, 2): SECOND,
        }
        s = go.GoState(size=size, board=mkboard(size, spec), to_move=FIRST)
        s = s.play((2, 1))                 # 黑提一子，形成劫
        self.assertEqual(s.cell(1, 1), 0)
        self.assertEqual(s.ko, (1, 1))
        self.assertFalse(s.is_legal((1, 1)))  # 白不能立刻回提
        with self.assertRaises(ValueError):
            s.play((1, 1))

    def test_two_passes_end_game(self):
        s = go.new_game(9)
        s = s.play(None)
        self.assertFalse(s.is_over)
        self.assertEqual(s.passes, 1)
        s = s.play(None)
        self.assertTrue(s.is_over)
        self.assertEqual(s.winner, SECOND)  # 空盘 + 贴目，白胜

    def test_area_score_empty_board_is_neutral_plus_komi(self):
        size = 9
        first, second = go.compute_score(mkboard(size, {}), size, 7.5)
        self.assertEqual(first, 0)
        self.assertEqual(second, 7.5)

    def test_area_score_black_wall_owns_all(self):
        size = 9
        spec = {(4, y): FIRST for y in range(size)}
        first, second = go.compute_score(mkboard(size, spec), size, 0.0)
        self.assertEqual(first, 81)   # 9 子 + 72 空（两片都归黑）
        self.assertEqual(second, 0)

    def test_sgf_export(self):
        s = go.new_game(9)
        s = s.play((3, 3))
        s = s.play((4, 4))
        text = s.to_sgf()
        self.assertIn("SZ[9]", text)
        self.assertIn(";B[dd]", text)
        self.assertIn(";W[ee]", text)

    def test_history_immutable(self):
        s0 = go.new_game(9)
        s1 = s0.play((0, 0))
        self.assertEqual(s1.move_count, 1)
        self.assertEqual(s0.move_count, 0)


if __name__ == "__main__":
    unittest.main()
