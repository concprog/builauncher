"""`buiemenu install` once. `buiemenu` triggers the daemon, or opens the menu once if none runs."""
import os
import sys

from .install import install, uninstall
from .trigger import send_trigger


COMMANDS = {"install": install, "uninstall": uninstall}


def main() -> int:
    if command := COMMANDS.get(sys.argv[1] if len(sys.argv) > 1 else ""):
        return command() or 0
    if "--daemon" not in sys.argv[1:] and send_trigger():
        return 0
    os.execv(sys.executable, [sys.executable, "-m", "buiemenu.app", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
