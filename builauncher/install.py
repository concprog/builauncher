"""`builauncher install`: start the daemon at login.

Linux: an XDG autostart entry, and the .desktop file the shortcut portal knows the app by.
Both are freedesktop.org standards, so KDE, GNOME, Xfce, Cinnamon and others read them.
Windows: a value under the user's Run registry key, with pythonw so no console opens.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .system import APP_ID, WINDOWS

if WINDOWS:
    import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
ENTRY = """[Desktop Entry]
Type=Application
Name=builauncher
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
    """The installed `builauncher` script, else this Python with -m."""
    return shutil.which("builauncher") or f"{sys.executable} -m builauncher"


def install() -> None:
    install_windows() if WINDOWS else install_xdg()


def uninstall() -> None:
    uninstall_windows() if WINDOWS else uninstall_xdg()


def install_windows() -> None:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, f'"{pythonw}" -m builauncher daemon')
    print(f"added {APP_ID} to HKCU\\{RUN_KEY}")
    print("start it now with: builauncher daemon   (it starts by itself at the next sign-in)")


def uninstall_windows() -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, APP_ID)
        except FileNotFoundError:
            pass  # not installed
    print(f"removed {APP_ID} from HKCU\\{RUN_KEY}")


def install_xdg() -> None:
    app, autostart = paths()
    for path, args in ((app, ""), (autostart, " daemon")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ENTRY.format(exec=command() + args))
        print(f"wrote {path}")
    if tool := shutil.which("update-desktop-database"):
        subprocess.run([tool, str(app.parent)], check=False)
    print("start it now with: builauncher daemon &   (it starts by itself at the next login)")


def uninstall_xdg() -> None:
    for path in paths():
        path.unlink(missing_ok=True)
        print(f"removed {path}")
