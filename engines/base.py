"""引擎适配基类：QProcess 管子进程，按行收发文本协议。

要点：坐标映射只要「发送」与「解析」互为逆运算即可——即使引擎自身的
坐标原点约定与我们对不上，反射后棋局是等价的，着法仍能正确映射回来。
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

# 引擎「不是正常落子」的两种明确语义（区别于 None=引擎失败）
MOVE_PASS = "pass"
MOVE_RESIGN = "resign"


# ---------------------------------------------------------------- 子进程兜底
# Windows：把引擎子进程加入一个 KILL_ON_JOB_CLOSE 的 Job Object。这样即便本进程被
# 强杀（崩溃 / 任务管理器结束 / 未走 aboutToQuit），OS 也会随 Job 句柄关闭一并终止
# katago / pikafish / rapfi，避免残留进程占满 CPU。正常退出仍走 stop() 的优雅结束，
# 不依赖这里。非 Windows 或调用失败都静默降级（best-effort，绝不因此让启动失败）。
_JOB = None
_JOB_TRIED = False


def _ensure_job():
    global _JOB, _JOB_TRIED
    if _JOB_TRIED:
        return _JOB
    _JOB_TRIED = True
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _BASIC_LIMIT(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _EXT_LIMIT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC_LIMIT),
                ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        k32 = ctypes.windll.kernel32
        k32.CreateJobObjectW.restype = ctypes.c_void_p
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXT_LIMIT()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        # 9 == JobObjectExtendedLimitInformation
        k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        _JOB = job
    except Exception:
        _JOB = None
    return _JOB


def _assign_to_job(pid):
    job = _ensure_job()
    if not job or not pid:
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        handle = k32.OpenProcess(0x0100 | 0x0001, False, int(pid))  # SET_QUOTA | TERMINATE
        if handle:
            k32.AssignProcessToJobObject(job, handle)
            k32.CloseHandle(handle)
    except Exception:
        pass


class EngineBase(QObject):
    bestMove = Signal(object)   # 引擎给出的着法（各棋种自己的坐标表示）
    failed = Signal(str)

    def __init__(self, name, program, args=None, cwd=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.program = str(program)
        self.args = [str(a) for a in (args or [])]
        self.cwd = str(cwd) if cwd else None
        self._proc = None
        self._buf = ""
        self._callbacks = []

    # ---------------- 生命周期 ----------------
    def available(self):
        return Path(self.program).exists()

    def start(self):
        if self._proc is not None:
            return True
        if not self.available():
            self.failed.emit("未找到引擎：%s" % self.program)
            return False
        proc = QProcess(self)
        proc.setProgram(self.program)
        proc.setArguments(self.args)
        if self.cwd:
            proc.setWorkingDirectory(self.cwd)
        proc.readyReadStandardOutput.connect(self._read_out)
        proc.readyReadStandardError.connect(self._read_err)
        proc.errorOccurred.connect(self._on_proc_error)
        proc.start()
        if not proc.waitForStarted(6000):
            self.failed.emit("%s 启动失败" % self.name)
            proc.deleteLater()
            return False
        self._proc = proc
        _assign_to_job(proc.processId())
        for cmd in self.handshake():
            self.send(cmd)
        return True

    def stop(self):
        proc = self._proc
        if proc is None:
            return
        self._proc = None
        for sig in (proc.readyReadStandardOutput, proc.readyReadStandardError,
                    proc.errorOccurred):
            try:
                sig.disconnect()
            except Exception:
                pass
        try:
            proc.write((self.quit_command() + "\n").encode("utf-8"))
            proc.waitForFinished(1500)
        except Exception:
            pass
        if proc.state() != QProcess.NotRunning:
            proc.kill()
            proc.waitForFinished(1000)
        proc.deleteLater()

    def _on_proc_error(self, err):
        if self._proc is None:
            return
        try:
            self.failed.emit("%s 进程错误：%s" % (self.name, err))
        except RuntimeError:
            pass   # 退出期对象已在析构，忽略

    def _read_err(self):
        if self._proc is None:
            return
        text = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace")
        if text.strip() and os.environ.get("BOARD_ENGINE_LOG"):
            import sys
            sys.stderr.write("[%s] %s" % (self.name, text))

    def _read_out(self):
        if self._proc is None:
            return
        self._buf += bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self.on_line(line.rstrip("\r"))

    def send(self, cmd, callback=None, record=True):
        if self._proc is None:
            return
        if record:
            self._callbacks.append(callback)
        self._proc.write((cmd + "\n").encode("utf-8"))

    def _resolve(self, line):
        """GTP 用：把响应行交给最早挂起的回调。"""
        if line[:1] in ("=", "?") and self._callbacks:
            cb = self._callbacks.pop(0)
            if cb is not None:
                cb(line)

    @property
    def running(self):
        return self._proc is not None

    # ---------------- 子类实现 ----------------
    def handshake(self):
        return []

    def quit_command(self):
        return "quit"

    def on_line(self, line):
        self._resolve(line)

    def request(self, state, time_ms=800):
        raise NotImplementedError

    def set_difficulty(self, level):
        """0 简单 / 1 普通 / 2 困难；子类按需覆盖。"""
        pass
