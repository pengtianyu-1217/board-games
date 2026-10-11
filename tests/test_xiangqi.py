import unittest

from core.games import xiangqi as x
from core.games.base import FIRST, SECOND


def board_from_fen(fen):
    rows = fen.split()[0].split("/")
    cells = []
    for row in rows:
        for ch in row:
            if ch.isdigit():
                cells.extend("." * int(ch))
            else:
                cells.append(ch)
    return tuple(cells)


class XiangqiRulesTest(unittest.TestCase):
    def test_initial_setup(self):
        s = x.new_game()
        self.assertEqual(len(s.board), 90)
        self.assertEqual(s.piece_count(), 32)
        red = sum(1 for c in s.board if c != "." and c.isupper())
        black = sum(1 for c in s.board if c != "." and c.islower())
        self.assertEqual(red, 16)
        self.assertEqual(black, 16)
        self.assertEqual(s.to_move, FIRST)

    def test_initial_fen(self):
        expected = (
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"
        )
        self.assertEqual(x.new_game().to_fen(), expected)

    def test_initial_legal_moves_count(self):
        # 象棋开局标准合法着法数为 44
        self.assertEqual(len(x.new_game().legal_moves()), 44)

    def test_red_pawn_forward_only_before_river(self):
        board = board_from_fen("3k5/9/9/9/9/9/9/9/9/4K4")
        b = list(board)
        b[x._idx(0, 6)] = "P"
        b = tuple(b)
        moves = x.pseudo_moves(b, FIRST)
        self.assertIn(((0, 6), (0, 5)), moves)
        self.assertNotIn(((0, 6), (1, 6)), moves)

    def test_red_pawn_sideways_after_river(self):
        board = board_from_fen("3k5/9/9/9/9/9/9/9/9/4K4")
        b = list(board)
        b[x._idx(4, 4)] = "P"
        b = tuple(b)
        moves = x.legal_moves(b, FIRST)
        self.assertIn(((4, 4), (4, 3)), moves)
        self.assertIn(((4, 4), (3, 4)), moves)
        self.assertIn(((4, 4), (5, 4)), moves)

    def test_horse_leg_blocked(self):
        b = ["."] * 90
        b[x._idx(4, 5)] = "N"
        b = tuple(b)
        self.assertEqual(len([m for m in x.pseudo_moves(b, FIRST) if m[0] == (4, 5)]), 8)
        b2 = list(b)
        b2[x._idx(5, 5)] = "P"  # 绊马腿
        b2 = tuple(b2)
        from_here = [m for m in x.pseudo_moves(b2, FIRST) if m[0] == (4, 5)]
        self.assertNotIn(((4, 5), (6, 6)), from_here)
        self.assertNotIn(((4, 5), (6, 4)), from_here)

    def test_elephant_cannot_cross_river(self):
        b = ["."] * 90
        b[x._idx(2, 5)] = "B"
        b = tuple(b)
        targets = {m[1] for m in x.pseudo_moves(b, FIRST) if m[0] == (2, 5)}
        self.assertIn((0, 7), targets)
        self.assertIn((4, 7), targets)
        self.assertNotIn((0, 3), targets)
        self.assertNotIn((4, 3), targets)

    def test_cannon_requires_screen_to_capture(self):
        b = ["."] * 90
        b[x._idx(4, 5)] = "C"
        b[x._idx(4, 3)] = "P"  # 炮架
        b[x._idx(4, 0)] = "k"
        moves = x.pseudo_moves(tuple(b), FIRST)
        self.assertIn(((4, 5), (4, 0)), moves)

        b2 = list(b)
        b2[x._idx(4, 3)] = "."
        moves2 = x.pseudo_moves(tuple(b2), FIRST)
        self.assertNotIn(((4, 5), (4, 0)), moves2)
        self.assertIn(((4, 5), (4, 3)), moves2)

    def test_flying_general_forbidden(self):
        # 红兵挡在两将之间的 4 路，移开就会让两将照面 → 非法
        board = board_from_fen("4k4/9/9/....P..../9/9/9/9/9/4K4")
        legal = x.legal_moves(board, FIRST)
        self.assertIn(((4, 3), (4, 2)), legal)      # 沿线走，仍挡着
        self.assertNotIn(((4, 3), (3, 3)), legal)   # 横移 → 照面，非法
        self.assertNotIn(((4, 3), (5, 3)), legal)

    def test_pinned_piece_cannot_expose_king(self):
        # 黑车牵制 3 路上的红车：红车不能离开该线
        board = board_from_fen("3rk4/9/9/9/9/3R5/9/9/9/3K5")
        for mv in x.legal_moves(board, FIRST):
            if mv[0] == (3, 5):
                self.assertEqual(mv[1][0], 3)

    def test_checkmate_means_no_legal_moves(self):
        b = ["."] * 90
        b[x._idx(4, 0)] = "k"   # 黑将
        b[x._idx(3, 9)] = "K"   # 红帅
        b[x._idx(4, 1)] = "R"
        b[x._idx(3, 1)] = "R"
        b[x._idx(5, 1)] = "R"
        self.assertEqual(x.legal_moves(tuple(b), SECOND), [])

    def test_play_and_history_immutability(self):
        s0 = x.new_game()
        s1 = s0.play(((0, 6), (0, 5)))
        self.assertEqual(s1.to_move, SECOND)
        self.assertEqual(s1.move_count, 1)
        self.assertEqual(s0.move_count, 0)

    def test_play_illegal_raises(self):
        s = x.new_game()
        with self.assertRaises(ValueError):
            s.play(((0, 6), (1, 6)))  # 未过河，不能横走


if __name__ == "__main__":
    unittest.main()
