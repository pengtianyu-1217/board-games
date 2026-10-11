"""QML 与规则层之间的桥（QObject + 列表模型）。

QML 只跟这里交互：读棋盘模型、点格子、悔棋、换棋种、棋谱、计时、存读。
规则、历史、轮次、AI 都在这层收口；引擎接入后在此替换 choose_move。
"""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, Property,
                            QTimer, Qt, QUrl, Signal, Slot)

from ai import choose_move
from core.games import go as go_mod
from core.games import gomoku as gomoku_mod
from core.games import notation
from core.games import xiangqi as xiangqi_mod
from core.games.base import DRAW, FIRST, SECOND, opponent
from engines.base import MOVE_PASS, MOVE_RESIGN
from engines.manager import EngineManager

GLYPHS = {
    "R": "车", "N": "马", "B": "相", "A": "仕", "K": "帅", "C": "炮", "P": "兵",
    "r": "车", "n": "马", "b": "象", "a": "士", "k": "将", "c": "炮", "p": "卒",
}

PLAYER_NAMES = {
    "xiangqi": {FIRST: "红方", SECOND: "黑方"},
    "go": {FIRST: "黑方", SECOND: "白方"},
    "gomoku": {FIRST: "黑方", SECOND: "白方"},
}

GAME_NAMES = {"gomoku": "五子棋", "xiangqi": "中国象棋", "go": "围棋"}

DIFFICULTY_NAMES = ("简单", "普通", "困难")

# 引擎单步最长等待（毫秒）：围棋模型重、冷启动慢，给更宽；超时回退内置 AI
ENGINE_TIMEOUT_MS = {"go": 20000, "xiangqi": 10000, "gomoku": 10000}

# 标记位
MARK_NONE = 0
MARK_LAST = 1
MARK_SELECTED = 2
MARK_TARGET = 3
MARK_WIN = 4


def _with_winner(state, winner):
    from dataclasses import replace
    return replace(state, winner=winner)


def _to_local(text):
    url = QUrl(str(text))
    return url.toLocalFile() if url.isLocalFile() else str(text)


class BoardModel(QAbstractListModel):
    OwnerRole = Qt.UserRole + 1
    GlyphRole = Qt.UserRole + 2
    MarkRole = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cols = 0
        self._owners: list = []
        self._glyphs: list = []
        self._marks: list = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._owners)

    def roleNames(self):
        return {
            self.OwnerRole: b"owner",
            self.GlyphRole: b"glyph",
            self.MarkRole: b"mark",
        }

    def data(self, index, role):
        if not index.isValid():
            return None
        i = index.row()
        if role == self.OwnerRole:
            return self._owners[i]
        if role == self.GlyphRole:
            return self._glyphs[i]
        if role == self.MarkRole:
            return self._marks[i]
        return None

    def set_board(self, cols, owners, glyphs, marks):
        owners, glyphs, marks = list(owners), list(glyphs), list(marks)
        if cols != self._cols or len(owners) != len(self._owners):
            self.beginResetModel()
            self._cols = cols
            self._owners, self._glyphs, self._marks = owners, glyphs, marks
            self.endResetModel()
            return
        changed = [
            i for i in range(len(owners))
            if (self._owners[i], self._glyphs[i], self._marks[i])
            != (owners[i], glyphs[i], marks[i])
        ]
        self._owners, self._glyphs, self._marks = owners, glyphs, marks
        for i in changed:
            idx = self.index(i, 0)
            self.dataChanged.emit(idx, idx)


class MoveListModel(QAbstractListModel):
    NoRole = Qt.UserRole + 1
    SideRole = Qt.UserRole + 2
    TextRole = Qt.UserRole + 3
    CurrentRole = Qt.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def roleNames(self):
        return {
            self.NoRole: b"moveNo",
            self.SideRole: b"side",
            self.TextRole: b"text",
            self.CurrentRole: b"current",
        }

    def data(self, index, role):
        if not index.isValid():
            return None
        it = self._items[index.row()]
        if role == self.NoRole:
            return it["index"]
        if role == self.SideRole:
            return it["side"]
        if role == self.TextRole:
            return it["text"]
        if role == self.CurrentRole:
            return it["current"]
        return None

    def set_items(self, items):
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()


class GameController(QObject):
    gameChanged = Signal()
    stateChanged = Signal()
    statusChanged = Signal()
    aiThinkingChanged = Signal()
    timeChanged = Signal()
    movesChanged = Signal()
    reviewChanged = Signal()
    humanSideChanged = Signal()
    difficultyChanged = Signal()
    capturedChanged = Signal()
    moveMade = Signal(str)      # place / capture / check / win / pass / lose / atari
    notice = Signal(str)
    eventChanged = Signal()         # 术语浮字
    captureAnimChanged = Signal()   # 被提/被吃棋子的飞离动画
    pieceSelected = Signal()        # 选中己方棋子（QML 播选中音）
    illegalMove = Signal()          # 落点非法（QML 播错误音）

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._game = "gomoku"
        self._timeline: list = []      # (state, t_first, t_second, move)
        self._viewIndex = 0
        self._state = None
        self._selected = None
        self._human_side = settings.humanSide if settings is not None else FIRST
        self._difficulty = settings.difficulty if settings is not None else 1
        self._ai_enabled = True
        self._ai_thinking = False
        self._think_start = 0.0
        self._ai_delay = 300
        self._times = [0.0, 0.0]
        self._engine_asked = None      # (棋种, 手数, 行棋方)：用于丢弃迟到的引擎应答
        self._event_term = ""
        self._event_seq = 0
        self._last_captured: list = []
        self._fallback_notified = False
        self._model = BoardModel(self)
        self._moves = MoveListModel(self)
        self._engine = EngineManager(self)
        self._engine.bestMove.connect(self._on_engine_move)
        self._engine.statusChanged.connect(lambda *_: self.statusChanged.emit())
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick)
        self._clock.start()
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_engine_timeout)
        self.newGame()

    # ---------------- 属性 ----------------
    def _get_game(self):
        return self._game

    def _set_game(self, value):
        if value and value != self._game:
            self.newGame(value)

    game = Property(str, _get_game, _set_game, notify=gameChanged)

    def _get_rows(self):
        return 10 if self._game == "xiangqi" else self._state.size

    def _get_cols(self):
        return 9 if self._game == "xiangqi" else self._state.size

    rows = Property(int, _get_rows, notify=gameChanged)
    cols = Property(int, _get_cols, notify=gameChanged)

    def _get_board(self):
        return self._model

    board = Property(QObject, _get_board, constant=True)

    def _get_moves(self):
        return self._moves

    moves = Property(QObject, _get_moves, constant=True)

    def _get_turn(self):
        return self._state.to_move

    turn = Property(int, _get_turn, notify=stateChanged)

    def _get_game_over(self):
        return self._state.is_over

    gameOver = Property(bool, _get_game_over, notify=stateChanged)

    def _get_ai_thinking(self):
        return self._ai_thinking

    aiThinking = Property(bool, _get_ai_thinking, notify=aiThinkingChanged)

    def _get_think_seconds(self):
        if not self._ai_thinking:
            return 0
        return max(0, int(time.monotonic() - self._think_start))

    thinkSeconds = Property(int, _get_think_seconds, notify=aiThinkingChanged)

    def _get_ai_engine(self):
        return self._engine.engine_name(self._game) or "内置 AI"

    aiEngine = Property(str, _get_ai_engine, notify=statusChanged)

    def _get_can_undo(self):
        return len(self._timeline) > 1

    canUndo = Property(bool, _get_can_undo, notify=stateChanged)

    def _get_move_count(self):
        return self._state.move_count

    moveCount = Property(int, _get_move_count, notify=stateChanged)

    def _get_engine_status(self):
        return self._engine.status

    engineStatus = Property(str, _get_engine_status, notify=statusChanged)

    def _get_status(self):
        if self._state.is_over:
            return self._result_text()
        if self._ai_thinking:
            return "对手思考中"
        return self._turn_text()

    status = Property(str, _get_status, notify=statusChanged)

    def _get_ai_enabled(self):
        return self._ai_enabled

    def _set_ai_enabled(self, value):
        if bool(value) != self._ai_enabled:
            self._ai_enabled = bool(value)
            self.statusChanged.emit()
            self._maybe_ai()

    aiEnabled = Property(bool, _get_ai_enabled, _set_ai_enabled, notify=statusChanged)

    def _get_human_side(self):
        return self._human_side

    def _set_human_side(self, value):
        value = FIRST if int(value) == 1 else SECOND
        if value != self._human_side:
            self._human_side = value
            if self._settings is not None:
                self._settings.humanSide = value
            self.humanSideChanged.emit()
            self.newGame()

    humanSide = Property(int, _get_human_side, _set_human_side, notify=humanSideChanged)

    def _get_difficulty(self):
        return self._difficulty

    def _set_difficulty(self, value):
        value = max(0, min(2, int(value)))
        if value != self._difficulty:
            self._difficulty = value
            if self._settings is not None:
                self._settings.difficulty = value
            self.difficultyChanged.emit()
            self.statusChanged.emit()

    difficulty = Property(int, _get_difficulty, _set_difficulty, notify=difficultyChanged)

    def _get_difficulty_text(self):
        return DIFFICULTY_NAMES[self._difficulty]

    difficultyText = Property(str, _get_difficulty_text, notify=difficultyChanged)

    def _get_result_detail(self):
        st = self._state
        if st is None or not st.is_over:
            return ""
        parts = ["共 %d 手" % st.move_count]
        if self._game == "go" and st.score is not None:
            first, second = st.score          # second 已含贴目
            parts.append("黑 %.0f 目 · 白 %.0f 目（含贴目 %.1f）· 差 %.1f 目"
                         % (first, second, st.komi, abs(first - second)))
        return " · ".join(parts)

    resultDetail = Property(str, _get_result_detail, notify=stateChanged)

    def _get_win_line(self):
        if self._game == "gomoku" and self._state.win_line:
            out = []
            for x, y in self._state.win_line:
                out.append(x)
                out.append(y)
            return out
        return []

    winLine = Property("QVariantList", _get_win_line, notify=stateChanged)

    def _get_reviewing(self):
        return self._viewIndex != len(self._timeline) - 1

    reviewing = Property(bool, _get_reviewing, notify=reviewChanged)

    def _get_time_first(self):
        if self.reviewing:
            return int(self._timeline[self._viewIndex][1])
        return int(self._times[0])

    def _get_time_second(self):
        if self.reviewing:
            return int(self._timeline[self._viewIndex][2])
        return int(self._times[1])

    timeFirst = Property(int, _get_time_first, notify=timeChanged)
    timeSecond = Property(int, _get_time_second, notify=timeChanged)

    def _get_can_pass(self):
        return self._game == "go" and not self._state.is_over and not self.reviewing

    canPass = Property(bool, _get_can_pass, notify=stateChanged)

    def _get_captured_first(self):
        return self._captured()[0]

    def _get_captured_second(self):
        return self._captured()[1]

    capturedFirst = Property("QVariantList", _get_captured_first, notify=capturedChanged)
    capturedSecond = Property("QVariantList", _get_captured_second, notify=capturedChanged)

    def _get_event_term(self):
        return self._event_term

    def _get_event_seq(self):
        return self._event_seq

    eventTerm = Property(str, _get_event_term, notify=eventChanged)
    eventSeq = Property(int, _get_event_seq, notify=eventChanged)

    def _get_last_captured(self):
        return self._last_captured

    lastCaptured = Property("QVariantList", _get_last_captured, notify=captureAnimChanged)

    def _get_check_point(self):
        if self._game != "xiangqi" or self._state.is_over:
            return []
        if xiangqi_mod.is_check(self._state.board, self._state.to_move):
            kp = xiangqi_mod.king_pos(self._state.board, self._state.to_move)
            if kp:
                return [kp[0], kp[1]]
        return []

    checkPoint = Property("QVariantList", _get_check_point, notify=stateChanged)

    def _get_ko_point(self):
        if self._game == "go" and self._state.ko:
            return [self._state.ko[0], self._state.ko[1]]
        return []

    koPoint = Property("QVariantList", _get_ko_point, notify=stateChanged)

    def _get_go_capture_first(self):
        return self._state.captures[0] if self._game == "go" else 0

    def _get_go_capture_second(self):
        return self._state.captures[1] if self._game == "go" else 0

    goCaptureFirst = Property(int, _get_go_capture_first, notify=capturedChanged)
    goCaptureSecond = Property(int, _get_go_capture_second, notify=capturedChanged)

    # ---------------- 供 QML 查询 ----------------
    @Slot(int, int, result=bool)
    def canClick(self, x, y):
        if self._state.is_over or self._ai_thinking or self.reviewing:
            return False
        return self._human_turn()

    def _human_turn(self):
        return (not self._ai_enabled) or (self._state.to_move == self._human_side)

    @Slot(int, result=str)
    def playerName(self, side):
        return PLAYER_NAMES[self._game].get(int(side), "")

    @Slot()
    def checkEngine(self):
        self.notice.emit(self._engine.probe(self._game))

    # ---------------- 槽 ----------------
    @Slot()
    @Slot(str)
    def newGame(self, game=None):
        if game:
            self._game = game
        self._selected = None
        self._ai_thinking = False
        self._engine_asked = None
        self._fallback_notified = False
        self._watchdog.stop()
        self._times = [0.0, 0.0]
        if self._game == "xiangqi":
            state = xiangqi_mod.new_game()
        elif self._game == "go":
            state = go_mod.new_game(19, 7.5)
        else:
            self._game = "gomoku"
            state = gomoku_mod.new_game(15, forbidden=True)
        self._timeline = [(state, 0.0, 0.0, None)]
        self._viewIndex = 0
        self._state = state
        self._set_captured([])
        self._emit_event("")
        self.gameChanged.emit()
        self.reviewChanged.emit()
        self._rebuild()
        self._sync_moves()
        self._emit_state()
        if self._ai_enabled:
            self._engine.prewarm(self._game)
        self._maybe_ai()

    @Slot(int, int)
    def clickCell(self, x, y):
        if self._state.is_over or self._ai_thinking or self.reviewing:
            return
        if not self._human_turn():
            return
        if self._game == "xiangqi":
            self._click_xiangqi(x, y)
        elif self._state.is_legal((x, y)):
            self._play((x, y))
        else:
            self.illegalMove.emit()

    @Slot()
    def passMove(self):
        if self._game != "go" or self._state.is_over or self._ai_thinking or self.reviewing:
            return
        if not self._human_turn():
            return
        try:
            new = self._state.play(None)
        except ValueError:
            return
        self._push(new, None)
        self._selected = None
        self._set_captured([])
        self._rebuild()
        self._sync_moves()
        self._emit_event("停一手")
        self.moveMade.emit("pass")
        self._emit_state()
        self._maybe_ai()

    @Slot()
    def undo(self):
        if len(self._timeline) <= 1:
            return
        # 复盘态：先丢弃「当前查看位置之后」的手，再撤掉当前这一手
        del self._timeline[self._viewIndex + 1:]
        if len(self._timeline) > 1:
            self._timeline.pop()
        if self._ai_enabled:
            while len(self._timeline) > 1 and self._timeline[-1][0].to_move != self._human_side:
                self._timeline.pop()
        self._viewIndex = len(self._timeline) - 1
        self._state = self._timeline[-1][0]
        self._times = [self._timeline[-1][1], self._timeline[-1][2]]
        self._selected = None
        self._ai_thinking = False
        self._engine_asked = None
        self._watchdog.stop()
        self._set_captured([])
        self.aiThinkingChanged.emit()
        self.reviewChanged.emit()
        self._rebuild()
        self._sync_moves()
        self._emit_state()

    @Slot()
    def resign(self):
        if self._state.is_over:
            return
        # AI 模式：人认输；双人模式：当前行棋的一方认输
        loser = self._human_side if self._ai_enabled else self._state.to_move
        self._end_game(opponent(loser))

    @Slot()
    def shutdown(self):
        self._clock.stop()
        self._watchdog.stop()
        self._engine.shutdown()

    # ---------------- 复盘 ----------------
    @Slot(int)
    def gotoMove(self, index):
        index = max(0, min(int(index), len(self._timeline) - 1))
        if index == self._viewIndex:
            return
        self._viewIndex = index
        self._state = self._timeline[index][0]
        self._selected = None
        self._set_captured([])
        self._rebuild()
        self._sync_moves()
        self.reviewChanged.emit()
        self.stateChanged.emit()
        self.timeChanged.emit()
        # 回到最新局面后，若仍轮到 AI 则恢复应招（复盘期间 AI 被挂起）
        if not self.reviewing:
            self._maybe_ai()

    @Slot()
    def exitReview(self):
        self.gotoMove(len(self._timeline) - 1)

    # ---------------- 存读 ----------------
    @Slot(str)
    def saveGame(self, target):
        path = _to_local(target)
        suffix = Path(path).suffix.lower()
        # .fen / .sgf 是棋种专属记谱：格式与当前棋种不符时明确拒绝，别抛异常
        if suffix == ".fen" and self._game != "xiangqi":
            self.notice.emit("FEN 记谱仅适用于象棋（当前为%s）" % GAME_NAMES.get(self._game, self._game))
            return
        if suffix == ".sgf" and self._game != "go":
            self.notice.emit("SGF 记谱仅适用于围棋（当前为%s）" % GAME_NAMES.get(self._game, self._game))
            return
        try:
            if suffix == ".fen":
                self._write(path, self._state.to_fen())
            elif suffix == ".sgf":
                self._write(path, self._state.to_sgf())
            elif suffix == ".txt":
                self._write(path, self._export_text())
            else:
                live = self._timeline[-1][0]
                data = {
                    "game": self._game,
                    "size": getattr(live, "size", 0),
                    "komi": getattr(live, "komi", 0),
                    "forbidden": bool(getattr(live, "forbidden", False)),
                    "humanSide": self._human_side,
                    "difficulty": self._difficulty,
                    "moves": [self._encode(m) for m in live.moves],
                }
                self._write(path, json.dumps(data, ensure_ascii=False, indent=2))
            self.notice.emit("已保存棋谱")
        except (OSError, ValueError) as exc:
            self.notice.emit("保存失败：%s" % exc)

    @Slot(str)
    def loadGame(self, target):
        path = _to_local(target)
        # 文件是外部输入：解析与字段校验全部托管，畸形文件只提示不抛异常
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("不是棋谱文件")
            game = data.get("game", "gomoku")
            size = int(data.get("size") or (19 if game == "go" else 15))
            if not 5 <= size <= 25:                     # 防止畸形尺寸撑爆棋盘
                size = 19 if game == "go" else 15
            komi = float(data.get("komi") or 7.5)
            human_side = FIRST if int(data.get("humanSide", 1)) == 1 else SECOND
            difficulty = max(0, min(2, int(data.get("difficulty", 1))))
            forbidden = bool(data.get("forbidden", True))
            moves = list(data.get("moves", []) or [])
        except (OSError, ValueError, TypeError) as exc:
            self.notice.emit("读取失败：%s" % exc)
            return

        if game == "xiangqi":
            state = xiangqi_mod.new_game()
        elif game == "go":
            state = go_mod.new_game(size, komi)
        else:
            game = "gomoku"
            state = gomoku_mod.new_game(size, forbidden=forbidden)
        self._game = game
        self._human_side = human_side
        self._difficulty = difficulty
        self._timeline = [(state, 0.0, 0.0, None)]
        self._times = [0.0, 0.0]
        self._state = state
        self._selected = None
        self._ai_thinking = False
        self._engine_asked = None
        self._watchdog.stop()
        ok = True
        for enc in moves:
            try:
                move = self._decode(game, enc)
                new = self._state.play(move)
            except (ValueError, TypeError, IndexError, KeyError):
                ok = False
                break
            self._push_raw(new, move)
            if new.is_over:
                break
        self._viewIndex = len(self._timeline) - 1
        self._state = self._timeline[-1][0]
        self.gameChanged.emit()
        self.humanSideChanged.emit()
        self.difficultyChanged.emit()
        self.reviewChanged.emit()
        self._rebuild()
        self._sync_moves()
        self._emit_state()
        self.notice.emit("已读入棋谱" if ok else "棋谱有非法着法，已截断")
        self._maybe_ai()

    # ---------------- 内部 ----------------
    def _write(self, path, text):
        Path(path).write_text(text, encoding="utf-8")

    def _export_text(self):
        """纯文本棋谱：可读的中文记谱 / 坐标，便于分享与打印。"""
        lines = [
            "三棋对弈 · %s 棋谱" % GAME_NAMES.get(self._game, self._game),
            "难度：%s" % DIFFICULTY_NAMES[self._difficulty],
            "结果：%s" % (self._result_text() if self._state.is_over else "未终局"),
            "",
        ]
        for i in range(1, len(self._timeline)):
            state, _t1, _t2, move = self._timeline[i]
            prev = self._timeline[i - 1][0]
            side = FIRST if i % 2 == 1 else SECOND
            if move == "resign":
                text = "认输"
            elif self._game == "xiangqi":
                text = notation.xiangqi_move_text(prev.board, move)
            else:
                text = notation.coord_text(self._game, move, state.size)
            lines.append("%3d. %s  %s" % (i, PLAYER_NAMES[self._game][side], text))
        return "\n".join(lines) + "\n"

    def _encode(self, move):
        if move is None:
            return None
        if self._game == "xiangqi":
            (fx, fy), (tx, ty) = move
            return [fx, fy, tx, ty]
        return [move[0], move[1]]

    def _decode(self, game, enc):
        if enc is None:
            return None
        if game == "xiangqi":
            fx, fy, tx, ty = enc
            return ((fx, fy), (tx, ty))
        return (enc[0], enc[1])

    def _click_xiangqi(self, x, y):
        st = self._state
        i = y * 9 + x
        ch = st.board[i]
        color = 0 if ch == "." else (FIRST if ch.isupper() else SECOND)
        own = (color == st.to_move and ch != ".")
        if self._selected is not None:
            move = (self._selected, (x, y))
            if move in st.legal_moves():
                self._play(move)
                self._selected = None
                return
            if not own:
                # 已选中棋子，但落点是空点 / 对方子且非法
                self.illegalMove.emit()
                return
            # 点到另一枚己方子 → 改选
        if own:
            self._selected = (x, y)
            self.pieceSelected.emit()
        else:
            self._selected = None
        self._rebuild()
        self.stateChanged.emit()

    def _push_raw(self, state, move):
        self._timeline.append((state, self._times[0], self._times[1], move))
        self._viewIndex = len(self._timeline) - 1
        self._state = state

    def _push(self, state, move):
        del self._timeline[self._viewIndex + 1:]
        self._push_raw(state, move)

    def _play(self, move):
        if not self._apply(move):
            return
        self._maybe_ai()

    def _apply(self, move):
        prev = self._state
        try:
            new = prev.play(move)
        except ValueError:
            return False
        self._push(new, move)
        self._selected = None
        self._set_captured(self._captured_diff(prev, move, new))
        self._rebuild()
        self._sync_moves()
        self._announce(prev, move)
        self._emit_state()
        return True

    def _captured_diff(self, prev, move, new):
        out = []
        if self._game == "xiangqi":
            (fx, fy), (tx, ty) = move
            ch = prev.board[ty * 9 + tx]
            if ch != ".":
                out.append({"x": tx, "y": ty,
                            "owner": FIRST if ch.isupper() else SECOND,
                            "glyph": GLYPHS.get(ch, ch)})
        else:
            size = new.size
            for i, (a, b) in enumerate(zip(prev.board, new.board)):
                if a != 0 and b == 0:
                    out.append({"x": i % size, "y": i // size, "owner": a, "glyph": ""})
        return out

    def _set_captured(self, items):
        self._last_captured = items
        self.captureAnimChanged.emit()

    def _emit_event(self, term):
        self._event_term = term
        if term:
            self._event_seq += 1
        self.eventChanged.emit()

    def _in_atari(self, st, move):
        """围棋：这手是否让对手某串变成只剩一气（打吃）。"""
        if move is None:
            return False
        size = st.size
        x, y = move
        seen = set()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= nx < size and 0 <= ny < size) or (nx, ny) in seen:
                continue
            if st.board[ny * size + nx] != st.to_move:
                continue
            group, libs = go_mod.group_and_liberties(st.board, size, nx, ny)
            seen |= group
            if len(libs) == 1:
                return True
        return False

    def _result_term(self):
        st = self._state
        if st.winner == DRAW:
            return "和棋"
        if self._game == "xiangqi":
            return xiangqi_mod.mate_term(st.board, st.winner)
        if self._game == "gomoku":
            if st.forbidden and st.winner == SECOND and len(st.win_line) >= 6:
                return "禁手"
            return "连五"
        return "终局"

    def _end_game(self, winner):
        self._ai_thinking = False
        self._watchdog.stop()
        self._push(_with_winner(self._state, winner), "resign")
        self._selected = None
        self.aiThinkingChanged.emit()
        self._rebuild()
        self._sync_moves()
        self._emit_event("认输")
        self.moveMade.emit("win" if winner == self._human_side else "lose")
        self._emit_state()

    def _announce(self, prev, move):
        st = self._state
        kind = "place"
        term = ""
        if st.is_over:
            kind = "win" if st.winner == self._human_side or not self._ai_enabled else "lose"
            term = self._result_term()
        elif self._game == "go":
            if sum(st.captures) > sum(prev.captures):
                kind = "capture"
                term = "提子"
            elif st.ko is not None:
                term = "打劫"
            elif self._in_atari(st, move):
                kind = "atari"
                term = "打吃"
        elif self._game == "xiangqi":
            if st.piece_count() < prev.piece_count():
                kind = "capture"
                term = "吃子"
            if xiangqi_mod.is_check(st.board, st.to_move):
                if kind == "place":
                    kind = "check"
                term = "将军"
        self._emit_event(term)
        self.moveMade.emit(kind)

    def _maybe_ai(self):
        if not self._ai_enabled or self._state.is_over or self.reviewing:
            return
        if self._ai_thinking:
            return
        if self._state.to_move == self._human_side:
            return
        self._ai_thinking = True
        self._think_start = time.monotonic()
        self.aiThinkingChanged.emit()
        self.statusChanged.emit()
        self._engine_asked = (self._game, self._state.move_count, self._state.to_move)
        if self._engine.request(self._game, self._state, None, self._difficulty):
            self._watchdog.start(ENGINE_TIMEOUT_MS.get(self._game, 10000))
            return
        self._engine_asked = None
        if not self._fallback_notified:
            self._fallback_notified = True
            self.notice.emit("引擎不可用，已回退内置 AI")
        QTimer.singleShot(self._ai_delay, self._do_ai)

    def _on_engine_timeout(self):
        # 引擎超时未应答：记为软失败并回退占位 AI，避免界面永久卡在「思考中」
        if not self._ai_thinking:
            return
        self._engine_asked = None
        self._engine.note_timeout(self._game)
        self._do_ai()

    def _on_engine_move(self, game, move):
        self._watchdog.stop()
        st = self._state
        asked = self._engine_asked
        self._engine_asked = None
        # 丢弃「迟到 / 过期」的应答：期间换过棋种、悔过棋、或局面已变。
        # 注意仍要清掉思考态，否则用户跳回历史手时 AI 应答被判过期后会永久卡在「思考中」。
        if game != self._game or asked != (self._game, st.move_count, st.to_move):
            if self._ai_thinking:
                self._ai_thinking = False
                self.aiThinkingChanged.emit()
                self.statusChanged.emit()
                self._maybe_ai()
            return
        if st.is_over or st.to_move == self._human_side:
            self._ai_thinking = False
            self.aiThinkingChanged.emit()
            self.statusChanged.emit()
            return
        if move == MOVE_RESIGN:
            self._end_game(self._human_side)
            return
        if move == MOVE_PASS and self._game == "go":
            try:
                new = st.play(None)
            except ValueError:
                self._do_ai()
                return
            self._ai_thinking = False
            self._push(new, None)
            self._set_captured([])
            self._rebuild()
            self._sync_moves()
            self._emit_event("停一手")
            self.moveMade.emit("pass")
            self._emit_state()
            self.aiThinkingChanged.emit()
            self._maybe_ai()
            return
        legal = False
        if move is None:
            legal = False
        elif self._game == "xiangqi":
            legal = move in st.legal_moves()
        else:
            legal = bool(st.is_legal(move))
        if not legal:
            self._do_ai()   # 引擎异常，退回占位 AI
            return
        self._ai_thinking = False
        if not self._apply(move):
            self._do_ai()
            return
        self.aiThinkingChanged.emit()
        self._maybe_ai()

    def _do_ai(self):
        st = self._state
        if st.is_over or st.to_move == self._human_side or self.reviewing:
            self._ai_thinking = False
            self.aiThinkingChanged.emit()
            self.statusChanged.emit()
            return
        move = choose_move(self._game, st, self._difficulty)
        self._ai_thinking = False
        if move is None and self._game == "go":
            try:
                new = st.play(None)
            except ValueError:
                self._emit_state()
                return
            self._push(new, None)
            self._set_captured([])
            self._rebuild()
            self._sync_moves()
            self._emit_event("停一手")
            self.moveMade.emit("pass")
            self._emit_state()
        elif move is None:
            self._emit_state()
            return
        else:
            if not self._apply(move):
                self.aiThinkingChanged.emit()
                self.statusChanged.emit()
                return
        self.aiThinkingChanged.emit()
        self._maybe_ai()

    def _rebuild(self):
        st = self._state
        if self._game == "xiangqi":
            cols = 9
            owners, glyphs = [], []
            for c in st.board:
                if c == ".":
                    owners.append(0)
                    glyphs.append("")
                else:
                    owners.append(FIRST if c.isupper() else SECOND)
                    glyphs.append(GLYPHS.get(c, c))
        else:
            cols = st.size
            owners = list(st.board)
            glyphs = [""] * len(owners)
        marks = self._compute_marks(cols, len(owners))
        self._model.set_board(cols, owners, glyphs, marks)
        self.capturedChanged.emit()

    def _compute_marks(self, cols, count):
        marks = [MARK_NONE] * count
        st = self._state
        if self._game == "xiangqi":
            if st.last_move:
                (_fx, _fy), (tx, ty) = st.last_move
                marks[ty * cols + tx] = MARK_LAST
            if self._selected is not None:
                sx, sy = self._selected
                marks[sy * cols + sx] = MARK_SELECTED
                for (frm, to) in st.legal_moves():
                    if frm == self._selected:
                        marks[to[1] * cols + to[0]] = MARK_TARGET
        else:
            if st.last_move:
                x, y = st.last_move
                marks[y * cols + x] = MARK_LAST
            for (x, y) in getattr(st, "win_line", ()) or ():
                marks[y * cols + x] = MARK_WIN
        return marks

    def _captured(self):
        if self._game != "xiangqi":
            return [], []
        init = collections.Counter(c for c in xiangqi_mod.INITIAL if c != ".")
        cur = collections.Counter(c for c in self._state.board if c != ".")
        first, second = [], []
        for ch, n in init.items():
            missing = n - cur.get(ch, 0)
            if missing > 0:
                bucket = first if ch.islower() else second
                bucket.extend([GLYPHS.get(ch, ch)] * missing)
        return first, second

    def _sync_moves(self):
        game = self._game
        items = []
        for i in range(1, len(self._timeline)):
            state, _t1, _t2, move = self._timeline[i]
            prev = self._timeline[i - 1][0]
            if move == "resign":
                text = "认输"
            elif game == "xiangqi":
                text = notation.xiangqi_move_text(prev.board, move)
            else:
                text = notation.coord_text(game, move, state.size)
            items.append({
                "index": i,
                "side": FIRST if i % 2 == 1 else SECOND,
                "text": text,
                "current": i == self._viewIndex,
            })
        self._moves.set_items(items)
        self.movesChanged.emit()

    def _tick(self):
        if self._state is None or self._state.is_over or self.reviewing:
            return
        self._times[self._state.to_move - 1] += 1.0
        self.timeChanged.emit()
        if self._ai_thinking:
            self.aiThinkingChanged.emit()

    def _turn_text(self):
        return PLAYER_NAMES[self._game][self._state.to_move] + "行棋"

    def _result_text(self):
        w = self._state.winner
        if w == DRAW:
            return "和棋"
        return PLAYER_NAMES[self._game][w] + "胜"

    def _emit_state(self):
        self.stateChanged.emit()
        self.statusChanged.emit()
