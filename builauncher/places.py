"""The user's common folders. QStandardPaths finds them on Linux (XDG user-dirs),
Windows (Known Folders) and macOS. The trash is no standard path: on Linux it is trash:///.
"""
import shlex

from PySide6.QtCore import QStandardPaths

from .menu import PIE_SLOTS, Action

L = QStandardPaths.StandardLocation
FOLDERS = (("Home", L.HomeLocation, "HOME"), ("Documents", L.DocumentsLocation, "DOCUMENTS"),
           ("Downloads", L.DownloadLocation, "IMPORT"), ("Music", L.MusicLocation, "FILE_SOUND"),
           ("Pictures", L.PicturesLocation, "FILE_IMAGE"), ("Videos", L.MoviesLocation, "FILE_MOVIE"),
           ("Desktop", L.DesktopLocation, "DESKTOP"))
TRASH = Action("Trash", "xdg-open trash:///", "TRASH")


def places() -> tuple[Action, ...]:
    """Folders that exist, then the trash. A sub-pie keeps one slot for Back."""
    found = (Action(name, f"xdg-open {shlex.quote(path)}", icon) for name, where, icon in FOLDERS
             if (path := QStandardPaths.writableLocation(where)))
    return *list(found)[:PIE_SLOTS - 2], TRASH
