"""`buiemenu install`: XDG autostart for the daemon, and the .desktop file the shortcut portal needs.

Both are freedesktop.org standards, so KDE, GNOME, Xfce, Cinnamon and others read them.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .trigger import APP_ID

ENTRY = """[Desktop Entry]
Type=Application
Name=buiemenu
Comment=Pie menu launcher
Exec={exec}
Icon=system-run
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""


def paths() -> tuple[Path, Path]:
    """The app entry (portal app id) and the autostart entry."""
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return data / "applications" / f"{APP_ID}.desktop", config / "autostart" / f"{APP_ID}.desktop"


def command() -> str:
    """The installed `buiemenu` script, else this Python with -m."""
    return shutil.which("buiemenu") or f"{sys.executable} -m buiemenu"


def install() -> None:
    app, autostart = paths()
    for path, args in ((app, ""), (autostart, " --daemon")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ENTRY.format(exec=command() + args))
        print(f"wrote {path}")
    if tool := shutil.which("update-desktop-database"):
        subprocess.run([tool, str(app.parent)], check=False)
    print("start it now with: buiemenu --daemon &   (it starts by itself at the next login)")


def uninstall() -> None:
    for path in paths():
        path.unlink(missing_ok=True)
        print(f"removed {path}")
