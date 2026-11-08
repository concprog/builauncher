"""The launcher process: `--daemon` waits for triggers, else it opens the menu once."""
import os
import sys
from pathlib import Path

from gi.repository import GLib
from PySide6.QtWidgets import QApplication

from .apps import apps
from .config import load
from .daemon import serve
from .launcher import Launcher
from .menu import actions
from .shortcut import bind
from .window import Overlay

SHELL_VAR = "QT_WAYLAND_SHELL_INTEGRATION"


def main() -> int:
    daemon = "--daemon" in sys.argv[1:]
    paths = [Path(a) for a in sys.argv[1:] if a != "--daemon"]
    # wayland: a layer surface has no frame, no tiling, and stays above windows
    shell = os.environ.get(SHELL_VAR)
    os.environ[SHELL_VAR] = "layer-shell"
    qt = QApplication(sys.argv[:1])
    qt.setQuitOnLastWindowClosed(not daemon)
    cfg = load(paths[0] if paths else None)
    entries = [*actions(cfg.menu), *(("App", a) for a in (apps() if cfg.apps else ()))]
    launcher = Launcher(cfg.menu, entries, lambda: window.dismiss())
    window = Overlay(launcher, daemon)
    # the window has its shell now; launched apps must not inherit layer-shell (they open full screen)
    os.environ.pop(SHELL_VAR) if shell is None else os.environ.update({SHELL_VAR: shell})
    if not daemon:
        window.summon()
        return qt.exec()
    server = serve(window.trigger)  # noqa: F841 (kept alive)
    try:
        portal = bind(cfg.shortcut, window.trigger, window.release)  # noqa: F841 (kept alive)
    except GLib.Error as error:
        print(f"builauncher: no global shortcut ({error.message}); bind `builauncher` in the desktop", file=sys.stderr)
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
