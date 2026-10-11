import unittest

from core.games import gomoku
from core.games.base import DRAW, EMPTY, FIRST, SECOND


class GomokuRulesTest(unittest.TestCase):
    def test_new_game_empty(self):
        s = gomoku.new_game(15)
        self.assertEqual(s.size, 15)
        self.assertEqual(s.to_move, FIRST)
        self.assertEqual(s.winner, 0)
        self.assertEqual(len(list(s.stones())), 0)
        self.assertEqual(len(s.legal_moves()), 225)

    def test_alternating_turns(self):
        s = gomoku.new_game(15)
        s = s.play((7, 7))
        self.assertEqual(s.cell(7, 7), FIRST)
        self.assertEqual(s.to_move, SECOND)
        self.assertEqual(s.last_move, (7, 7))
        s = s.play((0, 0))
        self.assertEqual(s.cell(0, 0), SECOND)
        self.assertEqual(s.to_move, FIRST)

    def test_illegal_rejects_occupied(self):
        s = gomoku.new_game(15).play((7, 7))
        with self.assertRaises(ValueError):
            s.play((7, 7))

    def test_illegal_rejects_out_of_bounds(self):
        s = gomoku.new_game(15)
        with self.assertRaises(ValueError):
            s.play((15, 0))

    def test_illegal_after_game_over(self):
        s = gomoku.new_game(15)
        for x in range(4):
            s = s.play((x, 0))          # black
            s = s.play((x, 1))          # white
        s = s.play((4, 0))              # black fifth in a row -> win
        self.assertEqual(s.winner, FIRST)
        with self.assertRaises(ValueError):
            s.play((5, 5))

    def test_horizontal_win(self):
        s = gomoku.new_game(15)
        seq = [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5), (3, 0), (3, 5), (4, 0)]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, FIRST)
        self.assertEqual(len(s.win_line), 5)

    def test_vertical_win(self):
        s = gomoku.new_game(15)
        # white wins vertically
        seq = [(0, 0), (5, 0), (1, 1), (5, 1), (2, 2), (5, 2), (3, 3), (5, 3), (0, 9), (5, 4)]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, SECOND)

    def test_diagonal_win(self):
        s = gomoku.new_game(15)
        seq = [(0, 0), (0, 5), (1, 1), (1, 5), (2, 2), (2, 5), (3, 3), (3, 5), (4, 4)]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, FIRST)

    def test_anti_diagonal_win(self):
        s = gomoku.new_game(15)
        seq = [(4, 0), (0, 5), (3, 1), (1, 5), (2, 2), (2, 5), (1, 3), (3, 5), (0, 4)]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, FIRST)

    def test_draw_on_small_full_board(self):
        s = gomoku.new_game(3)  # 3x3 cannot make five
        for x in range(3):
            for y in range(3):
                s = s.play((x, y))
        self.assertEqual(s.winner, DRAW)
        self.assertEqual(s.legal_moves(), [])

    def test_six_in_a_row_still_wins_freestyle(self):
        s = gomoku.new_game(15)
        seq = [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5), (3, 0), (3, 5), (4, 0)]
        for m in seq:
            s = s.play(m)
        self.assertEqual(s.winner, FIRST)


if __name__ == "__main__":
    unittest.main()
