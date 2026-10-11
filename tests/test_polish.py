"""本轮「沉浸打磨」的回归测试：设置持久化、文本导出、终局详情、连五坐标。"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BOARD_NO_ENGINE"] = "1"

from PySide6.QtCore import QCoreApplication, QSettings  # noqa: E402

from appsettings import AppSettings  # noqa: E402
from ai import choose_move  # noqa: E402
from controller import GameController  # noqa: E402
from core.games import gomoku  # noqa: E402
from core.games import xiangqi  # noqa: E402
from core.games.base import FIRST  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])
TMP = tempfile.gettempdir()


class AppSettingsPersistenceTest(unittest.TestCase):
    def setUp(self):
        # 用临时 INI 目录隔离，别污染用户真实设置
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())

    def test_roundtrip_persists(self):
        a = AppSettings()
        a.coords = False
        a.sfxOn = False
        a.musicOn = False
        a.musicVolume = 0.6
        a.difficulty = 2
        a.humanSide = 2

        b = AppSettings()
        self.assertFalse(b.coords)
        self.assertFalse(b.sfxOn)
        self.assertFalse(b.musicOn)
        self.assertAlmostEqual(b.musicVolume, 0.6, places=5)
        self.assertEqual(b.difficulty, 2)
        self.assertEqual(b.humanSide, 2)

    def test_clamps_out_of_range(self):
        a = AppSettings()
        a.difficulty = 9
        a.humanSide = 7
        a.musicVolume = 5.0
        self.assertEqual(a.difficulty, 2)
        self.assertEqual(a.humanSide, 2)
        self.assertEqual(a.musicVolume, 1.0)


class ControllerWiringTest(unittest.TestCase):
    def test_difficulty_persists_through_controller(self):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
        store = AppSettings()
        c = GameController(store)
        c.aiEnabled = False
        c.difficulty = 2
        self.assertEqual(store.difficulty, 2)
        c.humanSide = 2
        self.assertEqual(store.humanSide, 2)


class ResultDetailTest(unittest.TestCase):
    def test_gomoku_win_line(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for m in [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5), (3, 0), (3, 5), (4, 0)]:
            c.clickCell(*m)
        self.assertEqual(list(c.winLine)[:2], [0, 0])
        self.assertEqual(len(c.winLine), 10)          # 5 子 → 5 组坐标
        self.assertIn("共 9 手", c.resultDetail)

    def test_go_result_detail_has_score(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("go")
        c.passMove()
        c.passMove()
        self.assertTrue(c.gameOver)
        self.assertIn("目", c.resultDetail)
        self.assertIn("贴目 7.5", c.resultDetail)

    def test_non_go_has_no_score(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        self.assertEqual(c.resultDetail, "")          # 未终局


class TextExportTest(unittest.TestCase):
    def test_xiangqi_text_note(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        c.clickCell(1, 7)
        c.clickCell(4, 7)
        path = os.path.join(TMP, "bg_export_test.txt")
        c.saveGame(path)
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("炮八平五", text)
        self.assertIn("中国象棋", text)

    def test_gomoku_text_note(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        path = os.path.join(TMP, "bg_export_gomoku.txt")
        c.saveGame(path)
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("H8", text)


class FallbackGomokuAiTest(unittest.TestCase):
    """兜底 AI 的战术能力（引擎不可用时的下限）。"""

    def _state(self, spec, to_move):
        board = [0] * 225
        for (x, y), v in spec.items():
            board[y * 15 + x] = v
        return gomoku.GomokuState(size=15, board=tuple(board), to_move=to_move)

    def test_blocks_a_four(self):
        s = self._state({(3, 7): 1, (4, 7): 1, (5, 7): 1, (6, 7): 1,
                         (0, 0): 2, (1, 1): 2, (2, 2): 2}, 2)
        self.assertIn(choose_move("gomoku", s, 1), ((2, 7), (7, 7)))

    def test_completes_a_five(self):
        s = self._state({(3, 7): 2, (4, 7): 2, (5, 7): 2, (6, 7): 2,
                         (0, 0): 1, (1, 1): 1, (2, 2): 1}, 2)
        self.assertIn(choose_move("gomoku", s, 1), ((2, 7), (7, 7)))

    def test_blocks_an_open_three(self):
        s = self._state({(5, 7): 1, (6, 7): 1, (7, 7): 1,
                         (0, 0): 2, (1, 1): 2, (2, 2): 2}, 2)
        self.assertIn(choose_move("gomoku", s, 1), ((4, 7), (8, 7)))

    def test_opens_at_center(self):
        self.assertEqual(choose_move("gomoku", gomoku.new_game(15), 1), (7, 7))


class XiangqiMateTermTest(unittest.TestCase):
    """象棋杀法术语识别。"""

    def _board(self, pieces):
        board = ["."] * 90
        for (px, py), ch in pieces.items():
            board[py * 9 + px] = ch
        return tuple(board)

    def test_smothered(self):
        b = self._board({(4, 0): "k", (3, 0): "a", (5, 0): "a", (4, 1): "a",
                         (4, 5): "C", (4, 9): "K"})
        self.assertEqual(xiangqi.mate_term(b, FIRST), "闷宫")

    def test_double_cannon(self):
        b = self._board({(4, 0): "k", (4, 3): "C", (4, 5): "C", (4, 9): "K"})
        self.assertEqual(xiangqi.mate_term(b, FIRST), "重炮")

    def test_cannon_behind_horse(self):
        b = self._board({(4, 0): "k", (4, 2): "p", (4, 5): "C", (3, 3): "N", (4, 9): "K"})
        self.assertEqual(xiangqi.mate_term(b, FIRST), "马后炮")

    def test_horse_mate(self):
        b = self._board({(4, 0): "k", (3, 2): "N", (4, 9): "K"})
        self.assertEqual(xiangqi.mate_term(b, FIRST), "卧槽马")

    def test_stalemate_when_not_check(self):
        b = self._board({(4, 0): "k", (4, 9): "K"})
        self.assertEqual(xiangqi.mate_term(b, FIRST), "困毙")


if __name__ == "__main__":
    unittest.main()
