"""Installed apps from freedesktop .desktop files, and command launch."""
import os
import re
import shlex
import subprocess
from collections.abc import Iterator
from configparser import ConfigParser, Error
from pathlib import Path

from .menu import Action

FIELD_CODE = re.compile(r"\s*%[fFuUdDnNickvm]")


def app_dirs() -> Iterator[Path]:
    data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    for d in (str(data_home), *data_dirs.split(":")):
        yield Path(d) / "applications"


def read_entry(path: Path) -> Action | None:
    cp = ConfigParser(interpolation=None, strict=False)
    try:
        cp.read(path, encoding="utf-8")
    except (Error, UnicodeDecodeError):
        return None
    e = cp["Desktop Entry"] if cp.has_section("Desktop Entry") else {}
    if e.get("Type") != "Application" or "true" in (e.get("NoDisplay"), e.get("Hidden")) or not e.get("Exec"):
        return None
    return Action(e.get("Name", path.stem), FIELD_CODE.sub("", e["Exec"]), e.get("Icon", ""))


def apps() -> list[Action]:
    """Apps by desktop id; an earlier dir hides a later one, as the spec says."""
    files: dict[str, Path] = {}
    for d in filter(Path.is_dir, app_dirs()):
        for f in d.rglob("*.desktop"):
            files.setdefault(str(f.relative_to(d)).replace("/", "-"), f)
    return sorted(filter(None, map(read_entry, files.values())), key=lambda a: a.name.lower())


def run(cmd: str) -> None:
    """Start cmd detached from this process."""
    subprocess.Popen(shlex.split(cmd), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
