"""Bind `buiemenu` to a hotkey. It triggers the daemon, or opens the menu once if none runs."""
import os
import sys

from .trigger import send_trigger


def main() -> int:
    if "--daemon" not in sys.argv[1:] and send_trigger():
        return 0
    os.execv(sys.executable, [sys.executable, "-m", "buiemenu.app", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
