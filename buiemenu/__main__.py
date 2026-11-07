"""Bind `python -m buiemenu [menu.toml]` to a hotkey."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .apps import apps
from .config import load
from .launcher import Launcher
from .menu import actions
from .window import Overlay


def main() -> int:
    qt = QApplication(sys.argv[:1])
    cfg = load(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    entries = [*actions(cfg.menu), *(("App", a) for a in (apps() if cfg.apps else ()))]
    launcher = Launcher(cfg.menu, entries, qt.quit)
    window = Overlay(launcher.app, launcher.size, launcher.opaque)
    window.place()
    window.show()
    window.activateWindow()
    launcher.app.ctx.focus_node(launcher.field)
    launcher.open_pie()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
