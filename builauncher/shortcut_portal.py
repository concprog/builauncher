"""A global shortcut from the XDG GlobalShortcuts portal, so no desktop's settings need it.

The portal gives press and release, so a hold is exact. A non-sandboxed app first
registers its app id, which must match an installed .desktop file (`builauncher install`).
Gio runs on Qt's GLib event loop.
"""
import os
from collections.abc import Callable
from itertools import count

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .system import APP_ID

SHORTCUT_ID = "open"
PORTAL, PATH = "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
SHORTCUTS = "org.freedesktop.portal.GlobalShortcuts"
REQUEST = "org.freedesktop.portal.Request"
_tokens = count()


def _request(bus: Gio.DBusConnection, method: str, signature: str, args: tuple, options: dict,
             done: Callable[[dict], None]) -> None:
    """Call a portal method that answers with a Request::Response signal. Options go last."""
    token = f"builauncher{os.getpid()}_{next(_tokens)}"
    sender = bus.get_unique_name()[1:].replace(".", "_")
    path = f"{PATH}/request/{sender}/{token}"

    def response(bus, _sender, _path, _iface, _signal, params) -> None:
        bus.signal_unsubscribe(sub)
        code, results = params.unpack()
        if code != 0:
            raise RuntimeError(f"portal {method}: response {code}")
        done(results)

    sub = bus.signal_subscribe(PORTAL, REQUEST, "Response", path, None, Gio.DBusSignalFlags.NO_MATCH_RULE, response)
    options = {**options, "handle_token": GLib.Variant("s", token)}
    bus.call_sync(PORTAL, PATH, SHORTCUTS, method, GLib.Variant(signature, (*args, options)), None,
                  Gio.DBusCallFlags.NONE, -1, None)


def bind(trigger: str, on_press: Callable[[], None], on_release: Callable[[], None]) -> Gio.DBusConnection:
    """Bind the shortcut. Keep the result alive. Raises OSError if the portal has no GlobalShortcuts."""
    try:
        return _bind(trigger, on_press, on_release)
    except GLib.Error as error:
        raise OSError(error.message) from error


def _bind(trigger: str, on_press: Callable[[], None], on_release: Callable[[], None]) -> Gio.DBusConnection:
    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    try:
        bus.call_sync(PORTAL, PATH, "org.freedesktop.host.portal.Registry", "Register",
                      GLib.Variant("(sa{sv})", (APP_ID, {})), None, Gio.DBusCallFlags.NONE, -1, None)
    except GLib.Error:
        pass  # an older portal: the app id comes from the systemd scope (the autostart unit)

    def on_signal(_bus, _sender, _path, _iface, signal, params) -> None:
        if params[1] == SHORTCUT_ID:
            (on_press if signal == "Activated" else on_release)()

    for signal in ("Activated", "Deactivated"):
        bus.signal_subscribe(PORTAL, SHORTCUTS, signal, PATH, None, Gio.DBusSignalFlags.NONE, on_signal)

    def created(results: dict) -> None:
        shortcut = (SHORTCUT_ID, {"description": GLib.Variant("s", "Open builauncher"),
                                  "preferred_trigger": GLib.Variant("s", trigger)})
        _request(bus, "BindShortcuts", "(oa(sa{sv})sa{sv})", (results["session_handle"], [shortcut], ""), {},
                 lambda _: None)

    _request(bus, "CreateSession", "(a{sv})", (), {"session_handle_token": GLib.Variant("s", "builauncher")}, created)
    return bus
