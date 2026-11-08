"""The user's common folders. QStandardPaths finds them on Linux (XDG user-dirs),
Windows (Known Folders) and macOS. The trash is no standard path: see system.TRASH.
"""
from PySide6.QtCore import QStandardPaths

from .menu import PIE_SLOTS, Action
from .system import TRASH, open_command

L = QStandardPaths.StandardLocation
FOLDERS = (("Home", L.HomeLocation, "HOME"), ("Documents", L.DocumentsLocation, "DOCUMENTS"),
           ("Downloads", L.DownloadLocation, "IMPORT"), ("Music", L.MusicLocation, "FILE_SOUND"),
           ("Pictures", L.PicturesLocation, "FILE_IMAGE"), ("Videos", L.MoviesLocation, "FILE_MOVIE"),
           ("Desktop", L.DesktopLocation, "DESKTOP"))


def places() -> tuple[Action, ...]:
    """Folders that exist, then the trash. A sub-pie keeps one slot for Back."""
    found = (Action(name, open_command(path), icon) for name, where, icon in FOLDERS
             if (path := QStandardPaths.writableLocation(where)))
    return *list(found)[:PIE_SLOTS - 2], Action("Trash", open_command(TRASH), "TRASH")
