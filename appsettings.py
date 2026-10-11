"""应用设置（QSettings 持久化）。

坐标标注 / 音效 / 背景音乐 / 音量 / 难度 / 执子 都会写进系统设置，
下次启动自动恢复；以 QML 上下文属性 `appSettings` 暴露。

只存「用户偏好」，不含对局数据——对局走 saveGame/loadGame。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QSettings, Signal

ORG = "BoardGames"
APP = "三棋对弈"


class AppSettings(QObject):
    coordsChanged = Signal()
    soundChanged = Signal()
    musicChanged = Signal()
    volumeChanged = Signal()
    difficultyChanged = Signal()
    humanSideChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = QSettings(ORG, APP)
        self._coords = self._read_bool("view/coords", True)
        self._sfx = self._read_bool("audio/sfx", True)
        self._music = self._read_bool("audio/music", True)
        self._volume = self._read_float("audio/volume", 0.35)
        self._difficulty = self._read_int("game/difficulty", 1, 0, 2)
        self._human_side = self._read_int("game/humanSide", 1, 1, 2)

    # ---------------- 读取 ----------------
    def _read_bool(self, key, default):
        value = self._store.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def _read_int(self, key, default, lo, hi):
        try:
            value = int(self._store.value(key, default))
        except (TypeError, ValueError):
            value = default
        return max(lo, min(hi, value))

    def _read_float(self, key, default):
        try:
            value = float(self._store.value(key, default))
        except (TypeError, ValueError):
            value = default
        return max(0.0, min(1.0, value))

    # ---------------- 坐标 ----------------
    def _get_coords(self):
        return self._coords

    def _set_coords(self, value):
        value = bool(value)
        if value != self._coords:
            self._coords = value
            self._store.setValue("view/coords", value)
            self.coordsChanged.emit()

    coords = Property(bool, _get_coords, _set_coords, notify=coordsChanged)

    # ---------------- 音效 ----------------
    def _get_sfx(self):
        return self._sfx

    def _set_sfx(self, value):
        value = bool(value)
        if value != self._sfx:
            self._sfx = value
            self._store.setValue("audio/sfx", value)
            self.soundChanged.emit()

    sfxOn = Property(bool, _get_sfx, _set_sfx, notify=soundChanged)

    # ---------------- 背景音乐 ----------------
    def _get_music(self):
        return self._music

    def _set_music(self, value):
        value = bool(value)
        if value != self._music:
            self._music = value
            self._store.setValue("audio/music", value)
            self.musicChanged.emit()

    musicOn = Property(bool, _get_music, _set_music, notify=musicChanged)

    def _get_volume(self):
        return self._volume

    def _set_volume(self, value):
        value = max(0.0, min(1.0, float(value)))
        if abs(value - self._volume) > 1e-6:
            self._volume = value
            self._store.setValue("audio/volume", value)
            self.volumeChanged.emit()

    musicVolume = Property(float, _get_volume, _set_volume, notify=volumeChanged)

    # ---------------- 难度 ----------------
    def _get_difficulty(self):
        return self._difficulty

    def _set_difficulty(self, value):
        value = max(0, min(2, int(value)))
        if value != self._difficulty:
            self._difficulty = value
            self._store.setValue("game/difficulty", value)
            self.difficultyChanged.emit()

    difficulty = Property(int, _get_difficulty, _set_difficulty, notify=difficultyChanged)

    # ---------------- 执子 ----------------
    def _get_human_side(self):
        return self._human_side

    def _set_human_side(self, value):
        value = 1 if int(value) == 1 else 2
        if value != self._human_side:
            self._human_side = value
            self._store.setValue("game/humanSide", value)
            self.humanSideChanged.emit()

    humanSide = Property(int, _get_human_side, _set_human_side, notify=humanSideChanged)
