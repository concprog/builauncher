"""The global shortcut: the XDG portal on Linux, RegisterHotKey on Windows."""
import sys

if sys.platform == "win32":
    from .shortcut_windows import bind
else:
    from .shortcut_portal import bind

__all__ = ["bind"]
