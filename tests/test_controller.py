import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BOARD_NO_ENGINE"] = "1"   # 单测用占位 AI，保证确定性

from PySide6.QtCore import QCoreApplication  # noqa: E402

from controller import GameController  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])


class ControllerTest(unittest.TestCase):
    def test_gomoku_two_player_flow(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        self.assertEqual(c.game, "gomoku")
        self.assertEqual(c.board.rowCount(), 225)
        self.assertEqual(c.rows, 15)
        self.assertEqual(c.cols, 15)
        self.assertEqual(c.moveCount, 0)

        c.clickCell(7, 7)
        self.assertEqual(c.turn, 2)
        self.assertEqual(c.moveCount, 1)
        self.assertTrue(c.canUndo)

        c.undo()
        self.assertEqual(c.moveCount, 0)
        self.assertEqual(c.turn, 1)
        self.assertFalse(c.canUndo)

    def test_ai_replies(self):
        c = GameController()
        c.aiEnabled = True
        c.newGame("gomoku")
        c.clickCell(7, 7)
        self.assertEqual(c.turn, 2)     # 轮到 AI
        c._do_ai()                      # 手动触发，绕过定时器
        self.assertEqual(c.turn, 1)     # 回到人类
        self.assertEqual(c.moveCount, 2)

    def test_switch_game_resets_board(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        self.assertEqual(c.rows, 10)
        self.assertEqual(c.cols, 9)
        self.assertEqual(c.board.rowCount(), 90)
        self.assertEqual(c.moveCount, 0)

        c.newGame("go")
        self.assertEqual(c.rows, 19)
        self.assertEqual(c.board.rowCount(), 361)

    def test_gomoku_win_detected(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for x in range(4):
            c.clickCell(x, 0)   # 黑
            c.clickCell(x, 5)   # 白
        c.clickCell(4, 0)       # 黑第五子
        self.assertTrue(c.gameOver)
        self.assertEqual(c.status, "黑方胜")

    def test_xiangqi_select_then_move(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        c.clickCell(0, 6)   # 选中红兵
        self.assertEqual(c.moveCount, 0)
        c.clickCell(0, 5)   # 走一步
        self.assertEqual(c.moveCount, 1)
        self.assertEqual(c.turn, 2)

    def test_resign(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.resign()
        self.assertTrue(c.gameOver)
        self.assertEqual(c.status, "白方胜")

    def test_go_pass_twice_ends(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("go")
        c.passMove()
        self.assertFalse(c.gameOver)
        c.passMove()
        self.assertTrue(c.gameOver)

    def test_stale_engine_reply_is_ignored(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        before = c.moveCount
        c._engine_asked = ("gomoku", 999, 1)   # 与当前局面不符
        c._on_engine_move("gomoku", (0, 0))
        self.assertEqual(c.moveCount, before)

    def test_engine_reply_applied_when_current(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        c._ai_enabled = True
        c._ai_thinking = True
        c._engine_asked = ("gomoku", c._state.move_count, c._state.to_move)
        c._on_engine_move("gomoku", (0, 0))
        self.assertEqual(c.moveCount, 2)
        self.assertFalse(c.aiThinking)

    def test_resign_clears_thinking(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c._ai_thinking = True
        c.resign()
        self.assertFalse(c.aiThinking)


if __name__ == "__main__":
    unittest.main()
