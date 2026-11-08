"""The parts of the desktop that differ between Linux and Windows. No Qt, so the client stays fast."""
import os
import shlex
import subprocess
import sys
from pathlib import Path

WINDOWS = sys.platform == "win32"
APP_ID = "io.github.builauncher"  # the .desktop file name (Linux) and the Run value name (Windows)
PIPE = r"\\.\pipe\builauncher"  # Qt's QLocalServer name "builauncher" on Windows
TRASH = "shell:RecycleBinFolder" if WINDOWS else "trash:///"


def config_dir() -> Path:
    if WINDOWS:
        return Path(os.environ["APPDATA"]) / "builauncher"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "builauncher"


def socket_path() -> Path:
    """The daemon's Unix socket (Linux)."""
    return Path(os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/builauncher-{os.getuid()}") / "builauncher.sock"


def server_name() -> str:
    """The daemon's QLocalServer name: a Unix socket path, or a named pipe on Windows."""
    return "builauncher" if WINDOWS else str(socket_path())


def open_command(target: str) -> str:
    """A command that opens a folder, file, link, URL or shell location in its default app."""
    return f'explorer "{target}"' if WINDOWS else f"xdg-open {shlex.quote(target)}"


def run(cmd: str) -> None:
    """Start cmd detached from this process."""
    out = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if WINDOWS:  # Popen takes the command line as it is: shlex would eat backslashes
        subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP, **out)
    else:
        subprocess.Popen(shlex.split(cmd), start_new_session=True, **out)
