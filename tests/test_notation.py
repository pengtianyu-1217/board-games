import unittest

from core.games import notation, xiangqi


class XiangqiNotationTest(unittest.TestCase):
    def setUp(self):
        self.board = xiangqi.new_game().board

    def test_opening_cannon_and_horse(self):
        self.assertEqual(notation.xiangqi_move_text(self.board, ((1, 7), (4, 7))), "炮八平五")
        self.assertEqual(notation.xiangqi_move_text(self.board, ((7, 7), (4, 7))), "炮二平五")
        self.assertEqual(notation.xiangqi_move_text(self.board, ((1, 9), (2, 7))), "马八进七")
        self.assertEqual(notation.xiangqi_move_text(self.board, ((7, 9), (6, 7))), "马二进三")

    def test_pawn_forward(self):
        self.assertEqual(notation.xiangqi_move_text(self.board, ((0, 6), (0, 5))), "兵九进一")
        self.assertEqual(notation.xiangqi_move_text(self.board, ((8, 6), (8, 5))), "兵一进一")

    def test_pawn_sideways_after_river(self):
        b = list(self.board)
        b[xiangqi._idx(4, 4)] = "P"
        b[xiangqi._idx(4, 6)] = "."
        two = notation.xiangqi_move_text(tuple(b), ((4, 4), (3, 4)))
        self.assertEqual(two, "兵五平六")

    def test_front_back_disambiguation(self):
        b = ["."] * 90
        b[xiangqi._idx(0, 9)] = "R"
        b[xiangqi._idx(0, 7)] = "R"
        b[xiangqi._idx(4, 0)] = "k"
        b[xiangqi._idx(4, 9)] = "K"
        b = tuple(b)
        self.assertEqual(notation.xiangqi_move_text(b, ((0, 7), (0, 6))), "前车进一")
        self.assertEqual(notation.xiangqi_move_text(b, ((0, 9), (0, 8))), "后车进一")

    def test_black_uses_arabic(self):
        # 黑炮 (1,2) -> (4,2)：黑纵线 2 -> 5
        self.assertEqual(notation.xiangqi_move_text(self.board, ((7, 2), (4, 2))), "炮8平5")


class CoordNotationTest(unittest.TestCase):
    def test_go(self):
        self.assertEqual(notation.coord_text("go", (3, 3), 19), "D16")
        self.assertEqual(notation.coord_text("go", (8, 15), 19), "J4")
        self.assertEqual(notation.coord_text("go", None, 19), "停一手")

    def test_gomoku(self):
        self.assertEqual(notation.coord_text("gomoku", (0, 0), 15), "A1")
        self.assertEqual(notation.coord_text("gomoku", (7, 7), 15), "H8")


if __name__ == "__main__":
    unittest.main()
