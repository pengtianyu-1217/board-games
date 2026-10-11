"""针对本轮修复的回归测试。

覆盖：五子棋禁手接线、复盘态悔棋、非法点击/选中信号、
象棋最后一手标记、围棋终局守卫、引擎超时看门狗。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BOARD_NO_ENGINE"] = "1"

from PySide6.QtCore import QCoreApplication  # noqa: E402

from controller import GameController  # noqa: E402
from core.games import go as go_mod  # noqa: E402
from core.games import gomoku as gomoku_mod  # noqa: E402
from core.games.base import DRAW, FIRST, SECOND  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])
TMP = tempfile.gettempdir()


def _path(name):
    return os.path.join(TMP, name)

# 黑在第 0 行连成 6 子（长连）
_OVERLINE = [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5),
             (4, 0), (4, 5), (5, 0), (5, 5), (3, 0)]


class GomokuForbiddenWiringTest(unittest.TestCase):
    def test_new_game_enables_forbidden(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        self.assertTrue(c._state.forbidden)

    def test_overline_loses_in_app(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for m in _OVERLINE:
            c.clickCell(*m)
        self.assertTrue(c.gameOver)
        self.assertEqual(c._state.winner, SECOND)   # 黑长连禁手判负
        self.assertEqual(c.status, "白方胜")

    def test_longest_line_preferred(self):
        # 一手同时成五与成六时，win_line 应为 6 连（长连优先）
        s = gomoku_mod.new_game(15, forbidden=True)
        for m in _OVERLINE:
            s = s.play(m)
        self.assertEqual(s.winner, SECOND)
        self.assertGreaterEqual(len(s.win_line), 6)


class UndoDuringReviewTest(unittest.TestCase):
    def test_undo_removes_viewed_move(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        for m in [(7, 7), (8, 8), (6, 6)]:
            c.clickCell(*m)
        c.gotoMove(1)                 # 正在看第 1 手
        c.undo()                      # 应撤掉第 1 手，而不是末尾的第 3 手
        self.assertEqual(c.moveCount, 0)
        self.assertFalse(c.reviewing)


class InputFeedbackTest(unittest.TestCase):
    def test_select_and_illegal_signals(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        sel, ill = [], []
        c.pieceSelected.connect(lambda: sel.append(1))
        c.illegalMove.connect(lambda: ill.append(1))
        c.clickCell(0, 6)             # 选中红兵
        c.clickCell(3, 3)             # 非法落点
        self.assertEqual(len(sel), 1)
        self.assertEqual(len(ill), 1)
        self.assertEqual(c.moveCount, 0)

    def test_gomoku_illegal_click_emits(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        ill = []
        c.illegalMove.connect(lambda: ill.append(1))
        c.clickCell(7, 7)
        c.clickCell(7, 7)             # 已占位
        self.assertEqual(len(ill), 1)


class MarkLastTest(unittest.TestCase):
    def test_xiangqi_marks_only_destination(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        c.clickCell(0, 6)
        c.clickCell(0, 5)
        marked = [i for i, m in enumerate(c.board._marks) if m == 1]
        self.assertEqual(marked, [5 * 9 + 0])   # 仅落点 (0,5)


class GoGameOverGuardTest(unittest.TestCase):
    def test_is_legal_false_after_two_passes(self):
        s = go_mod.new_game(9)
        s = s.play(None).play(None)
        self.assertTrue(s.is_over)
        self.assertFalse(s.is_legal((4, 4)))
        self.assertEqual(s.legal_moves(), [])


class WatchdogTest(unittest.TestCase):
    def test_timeout_falls_back_to_placeholder(self):
        c = GameController()
        c.aiEnabled = True
        c.newGame("xiangqi")
        c.clickCell(0, 6)
        c.clickCell(0, 5)             # 人走一步 -> 轮到 AI(黑)
        self.assertEqual(c._state.to_move, SECOND)
        c._ai_thinking = True
        c._engine_asked = ("xiangqi", c._state.move_count, c._state.to_move)
        c._on_engine_timeout()        # 模拟引擎超时
        self.assertFalse(c.aiThinking)
        self.assertEqual(c.moveCount, 2)   # 占位 AI 顶上


def _finish_gomoku(c):
    for m in [(0, 0), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5), (3, 0), (3, 5), (4, 0)]:
        c.clickCell(*m)


class EndOfGameTest(unittest.TestCase):
    def test_undo_at_review_start_is_noop(self):
        # 终局 -> 复盘(gotoMove 0) -> 悔棋：曾在此崩溃（IndexError）
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        _finish_gomoku(c)
        c.gotoMove(0)
        c.undo()                       # 不应抛异常
        self.assertEqual(c.moveCount, 0)
        self.assertFalse(c.gameOver)

    def test_two_player_resign_uses_side_to_move(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")            # 黑先
        c.resign()                     # 黑认输
        self.assertEqual(c.status, "白方胜")

        c2 = GameController()
        c2.aiEnabled = False
        c2.newGame("gomoku")
        c2.clickCell(7, 7)             # 换白走
        c2.resign()                    # 白认输
        self.assertEqual(c2.status, "黑方胜")

    def test_stale_engine_reply_does_not_stick(self):
        c = GameController()
        c.aiEnabled = True
        c.newGame("xiangqi")
        c.clickCell(0, 6)
        c.clickCell(0, 5)              # 轮到 AI
        c.gotoMove(0)                  # 用户切到历史手（复盘）
        c._ai_thinking = True
        c._engine_asked = ("xiangqi", 999, 1)   # 故意过期的请求
        c._on_engine_move("xiangqi", ((1, 7), (4, 7)))
        self.assertFalse(c.aiThinking)          # 不再永久卡在「思考中」
        c.exitReview()                          # 回到最新局面
        self.assertTrue(c.aiThinking)           # AI 重新应招


class SaveLoadRobustnessTest(unittest.TestCase):
    """存读的边界：错误扩展名不崩、畸形 JSON 只提示不抛异常。"""

    def test_wrong_format_save_is_rejected(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("gomoku")
        c.clickCell(7, 7)
        notices = []
        c.notice.connect(lambda m: notices.append(m))
        for ext in (".fen", ".sgf"):
            p = _path("bg_wrong" + ext)
            if os.path.exists(p):
                os.remove(p)
            c.saveGame(p)                 # 曾抛 AttributeError 崩主线程
            self.assertFalse(os.path.exists(p))
        self.assertEqual(len(notices), 2)

    def test_matching_format_save_still_works(self):
        c = GameController()
        c.aiEnabled = False
        c.newGame("xiangqi")
        c.clickCell(0, 6)
        c.clickCell(0, 5)
        p = _path("bg_ok_shape.fen")
        c.saveGame(p)
        self.assertIn("rnbakabnr", Path(p).read_text(encoding="utf-8"))

    def test_malformed_json_reports_notice_without_crash(self):
        c = GameController()
        c.aiEnabled = False
        notices = []
        c.notice.connect(lambda m: notices.append(m))
        bad = _path("bg_bad_load.json")
        Path(bad).write_text(json.dumps({"game": "go", "size": "abc"}),
                             encoding="utf-8")
        c.loadGame(bad)
        self.assertTrue(notices)

    def test_load_clamps_absurd_size(self):
        c = GameController()
        c.aiEnabled = False
        p = _path("bg_huge_size.json")
        Path(p).write_text(json.dumps({"game": "gomoku", "size": 10 ** 9}),
                           encoding="utf-8")
        c.loadGame(p)                     # 不应分配超大棋盘
        self.assertLessEqual(c._state.size, 25)
        self.assertEqual(c.moves.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
