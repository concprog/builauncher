"""The launcher process: `--daemon` waits for triggers, else it opens the menu once."""
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .apps import apps
from .config import load
from .daemon import serve
from .launcher import Launcher
from .menu import actions
from .window import Overlay


def main() -> int:
    daemon = "--daemon" in sys.argv[1:]
    paths = [Path(a) for a in sys.argv[1:] if a != "--daemon"]
    # wayland: a layer surface has no frame, no tiling, and stays above windows
    os.environ.setdefault("QT_WAYLAND_SHELL_INTEGRATION", "layer-shell")
    qt = QApplication(sys.argv[:1])
    qt.setQuitOnLastWindowClosed(not daemon)
    cfg = load(paths[0] if paths else None)
    entries = [*actions(cfg.menu), *(("App", a) for a in (apps() if cfg.apps else ()))]
    launcher = Launcher(cfg.menu, entries, lambda: window.dismiss())
    window = Overlay(launcher, daemon)
    server = serve(window.trigger) if daemon else None  # noqa: F841 (keeps the server alive)
    if not daemon:
        window.summon()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
