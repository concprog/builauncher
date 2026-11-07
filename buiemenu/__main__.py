"""buiemenu: bind `python -m buiemenu` to a hotkey."""
import sys
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .bridge import Bridge, IconProvider
from .config import load


def start_point(app: QGuiApplication) -> tuple[float, float]:
    """The pointer when the platform tells it (X11), else the screen centre (Wayland)."""
    screen = app.primaryScreen().geometry()
    pos = QCursor.pos()
    p = pos if screen.contains(pos) and not pos.isNull() else screen.center()
    local = QPointF(p - screen.topLeft())
    return local.x(), local.y()


def main() -> int:
    app = QGuiApplication(sys.argv)
    bridge = Bridge(load(Path(sys.argv[1]) if len(sys.argv) > 1 else None), start_point(app))
    bridge.finished.connect(app.quit)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconProvider())
    engine.setInitialProperties({"bridge": bridge})
    engine.load(Path(__file__).with_name("qml") / "Main.qml")
    return app.exec() if engine.rootObjects() else 1


if __name__ == "__main__":
    sys.exit(main())
