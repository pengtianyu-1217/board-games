import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BOARD_NO_ENGINE"] = "1"

from PySide6.QtCore import QCoreApplication  # noqa: E402

from controller import GameController  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])
TMP = tempfile.gettempdir()


def _path(name):
    return os.path.join(TMP, name)


class SerializationTest(unittest.TestCase):
    def test_gomoku_roundtrip(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for m in [(7, 7), (8, 8), (7, 8), (8, 7)]:
            c.clickCell(*m)
        p = _path("bg_rt_gomoku.json")
        c.saveGame(p)
        c2 = GameController()
        c2.aiEnabled = False
        c2.loadGame(p)
        self.assertEqual(c2.game, "gomoku")
        self.assertEqual(c2.moveCount, 4)
        self.assertEqual(c2.moves.rowCount(), 4)

    def test_xiangqi_notation_survives_roundtrip(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        for a, b in [((1, 7), (4, 7)), ((7, 2), (4, 2)), ((1, 9), (2, 7))]:
            c.clickCell(*a)
            c.clickCell(*b)
        p = _path("bg_rt_xiangqi.json")
        c.saveGame(p)
        c2 = GameController()
        c2.aiEnabled = False
        c2.loadGame(p)
        texts = [c2.moves.data(c2.moves.index(r, 0), c2.moves.TextRole)
                 for r in range(c2.moves.rowCount())]
        self.assertEqual(texts, ["炮八平五", "炮8平5", "马八进七"])

    def test_go_pass_preserved(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("go")
        c.clickCell(3, 3)
        c.passMove()
        c.clickCell(4, 4)
        p = _path("bg_rt_go.json")
        c.saveGame(p)
        c2 = GameController()
        c2.aiEnabled = False
        c2.loadGame(p)
        self.assertEqual(list(c2._state.moves), [(3, 3), None, (4, 4)])
        self.assertEqual(c2.moveCount, 3)


class ReviewTest(unittest.TestCase):
    def test_jump_and_exit(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        c.clickCell(8, 8)
        c.clickCell(6, 6)
        self.assertFalse(c.reviewing)
        c.gotoMove(1)
        self.assertTrue(c.reviewing)
        self.assertEqual(c.moveCount, 1)
        c.exitReview()
        self.assertFalse(c.reviewing)
        self.assertEqual(c.moveCount, 3)

    def test_cannot_play_while_reviewing(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        c.gotoMove(0)
        c.clickCell(0, 0)
        self.assertEqual(c.moveCount, 0)   # 复盘态不落子


class SettingsTest(unittest.TestCase):
    def test_human_side_and_difficulty(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        c.clickCell(0, 6)
        c.clickCell(0, 5)
        self.assertEqual(c.moveCount, 1)
        c.humanSide = 2                 # 改边会重开
        self.assertEqual(c.humanSide, 2)
        self.assertEqual(c.moveCount, 0)
        c.difficulty = 2
        self.assertEqual(c.difficultyText, "困难")

    def test_captured_lists(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        self.assertEqual(list(c.capturedFirst), [])
        self.assertEqual(list(c.capturedSecond), [])
        c.newGame("go")
        self.assertEqual(c.goCaptureFirst, 0)

    def test_xiangqi_capture_detected(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        # 红炮八平五；黑炮 8 平 5；红炮吃中卒（(4,7)->(4,3)，越过红兵的炮架）
        for a, b in [((1, 7), (4, 7)), ((7, 2), (4, 2)), ((4, 7), (4, 3))]:
            c.clickCell(*a)
            c.clickCell(*b)
        self.assertEqual(c.moveCount, 3)
        self.assertEqual(list(c.capturedFirst), ["卒"])
        self.assertEqual(list(c.capturedSecond), [])

    def test_load_missing_file_reports_notice(self):
        c = GameController()
        c.aiEnabled = False
        notices = []
        c.notice.connect(lambda m: notices.append(m))
        c.loadGame(_path("bg_missing_xyz.json"))
        self.assertTrue(notices)


class EventTermTest(unittest.TestCase):
    def test_xiangqi_capture_term_and_ghost(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        for a, b in [((1, 7), (4, 7)), ((7, 0), (6, 2)), ((4, 7), (4, 3))]:
            c.clickCell(*a)
            c.clickCell(*b)
        self.assertEqual(c.eventTerm, "吃子")
        self.assertEqual(len(c.lastCaptured), 1)
        self.assertEqual(c.lastCaptured[0]["glyph"], "卒")

    def test_go_capture_term(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("go")
        for m in [(0, 1), (1, 1), (1, 0), (5, 5), (2, 1), (6, 6), (1, 2)]:
            c.clickCell(*m)
        self.assertEqual(c.eventTerm, "提子")
        self.assertEqual(len(c.lastCaptured), 1)
        self.assertEqual(c.lastCaptured[0]["owner"], 2)   # 被提的是白子

    def test_gomoku_win_term(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for a, b in [((0, 0), (0, 5)), ((1, 0), (1, 5)), ((2, 0), (2, 5)), ((3, 0), (3, 5))]:
            c.clickCell(*a)
            c.clickCell(*b)
        c.clickCell(4, 0)
        self.assertEqual(c.eventTerm, "连五")

    def test_xiangqi_check_term_and_point(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        # 黑炮在 (4,2) 成为炮架，红炮吃中卒的同时将军
        for a, b in [((1, 7), (4, 7)), ((7, 2), (4, 2)), ((4, 7), (4, 3))]:
            c.clickCell(*a)
            c.clickCell(*b)
        self.assertEqual(c.eventTerm, "将军")
        self.assertEqual(list(c.checkPoint), [4, 0])

    def test_check_point_empty_initially(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        self.assertEqual(list(c.checkPoint), [])
        self.assertEqual(list(c.koPoint), [])


if __name__ == "__main__":
    unittest.main()
