"""The launcher process: `--daemon` waits for triggers, else it opens the menu once."""
import os
import sys
from pathlib import Path

import buipy
from PySide6.QtWidgets import QApplication

from .items.apps import apps
from .config import load
from .daemon import serve
from .launcher import Launcher
from .items.menu import actions
from .shortcut import bind
from .window import Overlay, layer_shell

SHELL_VAR = "QT_WAYLAND_SHELL_INTEGRATION"


def main() -> int:
    daemon = "--daemon" in sys.argv[1:]
    paths = [Path(a) for a in sys.argv[1:] if a != "--daemon"]
    # wayland: a layer surface has no frame, no tiling, and stays above windows
    shell = os.environ.get(SHELL_VAR)
    if layer_shell():
        os.environ[SHELL_VAR] = "layer-shell"
    qt = QApplication(sys.argv[:1])
    qt.setQuitOnLastWindowClosed(not daemon)
    cfg = load(paths[0] if paths else None)
    buipy.kit_set_scale(cfg.scale)  # before any size is taken from the kit unit
    entries = [*actions(cfg.menu), *(("App", a) for a in (apps() if cfg.apps else ()))]
    launcher = Launcher(cfg.menu, entries, lambda: window.dismiss())
    window = Overlay(launcher, daemon, cfg.dwell)
    # the window has its shell now; launched apps must not inherit layer-shell (they open full screen)
    os.environ.pop(SHELL_VAR, None) if shell is None else os.environ.update({SHELL_VAR: shell})
    if not daemon:
        window.summon()
        return qt.exec()
    server = serve(window.trigger)  # noqa: F841 (kept alive)
    try:
        portal = bind(cfg.shortcut, window.trigger, window.release)  # noqa: F841 (kept alive)
    except (OSError, ValueError) as error:
        print(f"builauncher: no global shortcut ({error}); bind `builauncher` in the desktop", file=sys.stderr)
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
