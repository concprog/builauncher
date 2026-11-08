"""A global shortcut from the XDG GlobalShortcuts portal, so no desktop's settings need it.

The portal gives press and release, so a hold is exact. A non-sandboxed app first
registers its app id, which must match an installed .desktop file (`builauncher install`).
jeepney talks D-Bus in pure Python. After the bind, a thread reads the signals and a
Qt signal brings them to the main thread.
"""
import os
import threading
from collections.abc import Callable

from jeepney import DBusAddress, HeaderFields, MatchRule, Message, MessageType, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import DBusConnection, open_dbus_connection
from PySide6.QtCore import QObject, Signal

from .system import APP_ID

SHORTCUT_ID = "open"
PORTAL, PATH = "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
SHORTCUTS = "org.freedesktop.portal.GlobalShortcuts"
REQUEST = "org.freedesktop.portal.Request"
REGISTRY = DBusAddress(PATH, PORTAL, "org.freedesktop.host.portal.Registry")
PORTAL_SHORTCUTS = DBusAddress(PATH, PORTAL, SHORTCUTS)


class Shortcut(QObject):
    """Keeps the connection and its reader thread alive. Signals arrive in the Qt thread."""
    signal = Signal(str)

    def __init__(self, conn: DBusConnection, on_press: Callable[[], None], on_release: Callable[[], None]) -> None:
        super().__init__()
        self._conn = conn
        self.signal.connect(lambda name: (on_press if name == "Activated" else on_release)())
        rule = MatchRule(type="signal", interface=SHORTCUTS, path=PATH)
        _call(conn, message_bus.AddMatch(rule))
        self._queue = conn.filter(rule).queue

    def start(self) -> None:
        """Read signals in a thread. Call after the last portal request: the connection has one reader."""
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        while msg := self._conn.recv_until_filtered(self._queue):
            if msg.body[1] == SHORTCUT_ID:
                self.signal.emit(msg.header.fields[HeaderFields.member])


def _call(conn: DBusConnection, msg: Message) -> Message:
    reply = conn.send_and_get_reply(msg)
    if reply.header.message_type == MessageType.error:
        raise OSError(f"{msg.header.fields[HeaderFields.member]}: {reply.body}")
    return reply


def _request(conn: DBusConnection, method: str, signature: str, args: tuple, options: dict) -> dict:
    """Call a portal method that answers with a Request::Response signal. Options go last."""
    token = f"builauncher{os.getpid()}_{method}"
    sender = conn.unique_name[1:].replace(".", "_")
    rule = MatchRule(type="signal", interface=REQUEST, member="Response",
                     path=f"{PATH}/request/{sender}/{token}")
    _call(conn, message_bus.AddMatch(rule))
    with conn.filter(rule) as queue:
        _call(conn, new_method_call(PORTAL_SHORTCUTS, method, signature,
                                    (*args, {**options, "handle_token": ("s", token)})))
        code, results = conn.recv_until_filtered(queue).body
    if code != 0:
        raise OSError(f"portal {method}: response {code}")
    return results


def bind(trigger: str, on_press: Callable[[], None], on_release: Callable[[], None]) -> Shortcut:
    """Bind the shortcut. Keep the result alive. Raises OSError if the portal has no GlobalShortcuts."""
    try:
        conn = open_dbus_connection("SESSION")
    except (KeyError, ValueError) as error:  # no session bus address
        raise OSError(f"no session bus: {error}") from error
    try:  # an older portal has no Registry: the app id comes from the systemd scope (the autostart unit)
        _call(conn, new_method_call(REGISTRY, "Register", "sa{sv}", (APP_ID, {})))
    except OSError:
        pass
    shortcut = Shortcut(conn, on_press, on_release)
    session = _request(conn, "CreateSession", "a{sv}", (), {"session_handle_token": ("s", "builauncher")})
    bound = (SHORTCUT_ID, {"description": ("s", "Open builauncher"), "preferred_trigger": ("s", trigger)})
    _request(conn, "BindShortcuts", "oa(sa{sv})sa{sv}", (session["session_handle"][1], [bound], ""), {})
    shortcut.start()
    return shortcut
