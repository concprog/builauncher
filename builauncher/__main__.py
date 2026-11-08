"""The `builauncher` command. Qt loads only in the process that shows the menu."""
import argparse
import os
import sys

from .install import install, uninstall
from .trigger import send_trigger


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="builauncher", description="Pie-menu launcher on BUI.")
    sub = cli.add_subparsers(dest="command", metavar="command")
    sub.add_parser("open", help="open the menu: trigger the daemon, or open it once (the default)")
    sub.add_parser("daemon", help="stay running, bind the global shortcut, wait for triggers")
    sub.add_parser("install", help="add the autostart entry and the app entry")
    sub.add_parser("uninstall", help="remove them")
    for name in ("open", "daemon"):
        sub.choices[name].add_argument("--config", metavar="TOML", help="menu file (default: ~/.config/builauncher/menu.toml)")
    return cli


def main() -> int:
    args = parser().parse_args()
    match args.command:
        case "install":
            install()
        case "uninstall":
            uninstall()
        case "daemon" | "open" | None:
            daemon = args.command == "daemon"
            if not daemon and send_trigger():
                return 0
            config = [args.config] if getattr(args, "config", None) else []
            os.execv(sys.executable, [sys.executable, "-m", "builauncher.app", *(["--daemon"] if daemon else []), *config])
    return 0


if __name__ == "__main__":
    sys.exit(main())
