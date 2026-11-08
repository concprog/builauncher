"""A global shortcut on Windows: RegisterHotKey gives the press as WM_HOTKEY.

Windows sends no release, so a timer polls GetAsyncKeyState until the key is up.
The process that gets WM_HOTKEY may bring its window to the front.
"""
import ctypes
import sys
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer

WM_HOTKEY, HOTKEY_ID, MOD_NOREPEAT, KEY_DOWN = 0x0312, 1, 0x4000, 0x8000
POLL_MS = 16
# XDG shortcut names (the config's format) -> Windows modifier bits and virtual keys
MODS = {"CTRL": 0x2, "ALT": 0x1, "SHIFT": 0x4, "LOGO": 0x8}
KEYS = {"space": 0x20, "tab": 0x09, "return": 0x0D, "escape": 0x1B, "grave": 0xC0,
        **{f"F{i}": 0x6F + i for i in range(1, 25)}}
user32 = ctypes.WinDLL("user32") if sys.platform == "win32" else None


def parse(trigger: str) -> tuple[int, int]:
    """'CTRL+ALT+space' -> (modifier bits, virtual key). Raises ValueError on an unknown name."""
    *mods, key = trigger.split("+")
    if unknown := [m for m in mods if m not in MODS]:
        raise ValueError(f"shortcut {trigger!r}: unknown modifier {unknown[0]}")
    vk = KEYS.get(key) or (ord(key.upper()) if len(key) == 1 and key.isalnum() else 0)
    if not vk:
        raise ValueError(f"shortcut {trigger!r}: unknown key {key!r}")
    return sum(MODS[m] for m in mods), vk


class Hotkey(QAbstractNativeEventFilter):
    def __init__(self, trigger: str, on_press: Callable[[], None], on_release: Callable[[], None]) -> None:
        super().__init__()
        mods, self._vk = parse(trigger)
        self._press, self._release = on_press, on_release
        self._poll = QTimer(interval=POLL_MS, timeout=self._check)
        if not user32.RegisterHotKey(None, HOTKEY_ID, mods | MOD_NOREPEAT, self._vk):
            raise OSError(f"shortcut {trigger}: {ctypes.FormatError()}")  # another app holds it
        QCoreApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, kind, message) -> tuple[bool, int]:  # noqa: N802
        msg = wintypes.MSG.from_address(int(message))
        if msg.message != WM_HOTKEY or msg.wParam != HOTKEY_ID:
            return False, 0
        self._press()
        self._poll.start()
        return True, 0

    def _check(self) -> None:
        if not user32.GetAsyncKeyState(self._vk) & KEY_DOWN:
            self._poll.stop()
            self._release()


def bind(trigger: str, on_press: Callable[[], None], on_release: Callable[[], None]) -> Hotkey:
    """Bind the shortcut. Keep the result alive. Raises OSError if another app holds it."""
    return Hotkey(trigger, on_press, on_release)
