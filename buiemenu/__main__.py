"""Bind `python -m buiemenu [menu.toml]` to a hotkey."""
import sys
from pathlib import Path

from bui import host

from .apps import apps
from .config import load
from .launcher import Launcher
from .menu import actions


def main() -> None:
    cfg = load(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    entries = [*actions(cfg.menu), *(("App", a) for a in (apps() if cfg.apps else ()))]
    launcher = Launcher(cfg.menu, entries, host.quit)
    launcher.app.open()
    launcher.app.ctx.focus_node(launcher.field)
    launcher.open_pie()
    host.run()


if __name__ == "__main__":
    main()
