"""三棋对弈（中国象棋 / 围棋 / 五子棋）入口。

    python main.py                 启动图形界面
    python main.py --game go       指定开局棋种（gomoku / xiangqi / go）
    python main.py --demo          开局后自动走一步，便于观察引擎应招
    python main.py --no-engine     强制使用内置占位 AI
    python main.py --selftest      只加载 QML 校验无错，然后退出

截图请看 tools/shot.ps1（按窗口 PID 截屏），不走 Qt 内部抓帧。
"""

import os
import sys
from pathlib import Path

APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) \
    if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
QML_DIR = APP_DIR / "qml"


def _emit(stream_name, text):
    """安全写 stdout/stderr：打包成窗口程序（noconsole）后这两个流可能为 None。"""
    stream = getattr(sys, stream_name, None)
    if stream is not None:
        try:
            stream.write(text)
        except Exception:
            pass


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--no-engine" in argv:
        os.environ["BOARD_NO_ENGINE"] = "1"
    selftest = "--selftest" in argv
    if selftest:
        # 无头冒烟：offscreen 平台，不弹真窗口，也不拉起真引擎
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ["BOARD_NO_ENGINE"] = "1"

    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from appsettings import AppSettings
    from controller import GameController

    app = QGuiApplication(argv)
    app.setApplicationName("三棋对弈")
    app.setOrganizationName("BoardGames")
    app.setApplicationDisplayName("三棋对弈")

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    # 打包后 Qt 的 QML 模块随 PySide6/qml 一起释放在 _MEIPASS 下，显式加入导入路径
    _pyside_qml = APP_DIR / "PySide6" / "qml"
    if _pyside_qml.is_dir():
        engine.addImportPath(str(_pyside_qml))
    settings = AppSettings()
    controller = GameController(settings)
    if "--game" in argv:
        idx = argv.index("--game") + 1
        if idx < len(argv):
            controller.newGame(argv[idx])
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("appSettings", settings)
    app.aboutToQuit.connect(controller.shutdown)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))

    if not engine.rootObjects():
        _emit("stderr", "QML 加载失败：没有生成任何根对象\n")
        return 1

    if selftest:
        _emit("stdout", "selftest ok\n")
        return 0

    if "--demo" in argv:
        def demo():
            kind = controller.game
            if kind == "xiangqi":
                controller.clickCell(0, 6)
                controller.clickCell(0, 5)
            elif kind == "gomoku":
                controller.clickCell(7, 7)
            else:
                controller.clickCell(9, 9)
        QTimer.singleShot(900, demo)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
