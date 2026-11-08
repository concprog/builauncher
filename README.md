# builauncher

A pie-menu launcher on [BUI](https://github.com/ppmpreetham/BUI)'s Python binding
(Blender's pie menu and widgets), shown in a frameless, translucent Qt window.
Press a hotkey, pick from a pie, or type to
fuzzy-search every command and installed app.

## Use

    pip install .                    # or: pipx install --system-site-packages .
    builauncher install              # autostart and app entry; `builauncher uninstall` removes them
    builauncher daemon &             # this session only; later sessions start it by themselves
    builauncher                      # open the menu (same as `builauncher open`)

`builauncher --help` lists the commands. `open` and `daemon` take `--config TOML`.

For development: `uv venv --system-site-packages`, `uv sync`, `uv run pytest`, `uv build`.

Distro packages: `python3-pyside6`, `python3-gobject` and `layer-shell-qt` (Fedora names).
Without the first two, `pip install .[wheels]` gets them from PyPI; PyGObject then
builds from source and needs the gobject-introspection and cairo headers.

`install` writes two freedesktop.org entries, so any XDG desktop reads them:

- `~/.config/autostart/io.github.builauncher.desktop` starts `builauncher daemon` at login.
- `~/.local/share/applications/io.github.builauncher.desktop` (hidden) gives the app id.

The daemon binds its own global shortcut through the
[XDG GlobalShortcuts portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)
(KDE Plasma, GNOME 48 and later, Hyprland). It asks for `shortcut` from the config,
`Ctrl+Alt+Space` by default, at the first start. The desktop may ask you to confirm it.
After that, change it in the desktop's shortcut settings. The portal sends press and
release, so the hold gesture is exact.

Without the portal (for example on sway), the daemon prints a note. Bind the
command `builauncher` to a key in your compositor. It sends a trigger over
`$XDG_RUNTIME_DIR/builauncher.sock` in about 80 ms, or opens the menu once if no daemon
runs. Compositors that do not run XDG autostart (sway, Hyprland) need `builauncher daemon`
in their own startup config, or `dex -a`.

Gestures (from Kando and Blender's pie):

| Input | Result |
| --- | --- |
| Hotkey tap | Open the pie. Pick with a click. |
| Hotkey held, pointer moved, hotkey released | Pick the item in that direction. A hold is 0.2 s, Blender's `pie_tap_timeout`. |
| Hotkey twice within 0.4 s | Search only, with no pie. |
| Hotkey while open | Close. |
| Mouse drag from empty space | Pick the item in the drag direction (Kando's marking mode). |
| Click the pie centre | Back to the parent pie, or close at the top. |
| Escape or Alt+F4 (in the pie or the search), click outside the widgets, focus lost | Close. |
| Search slot (west), or typing at any time | Search bar and results in place of the pie: fuzzy search over menu actions and `.desktop` apps. Up and Down move the lit row; Return or a click runs it. |
| Tab | Back to the pie. |

On Wayland the window is a centred, borderless layer-shell overlay that takes the
keyboard (needs `layer-shell-qt`). On X11 it opens at the pointer.

## Config

Copy `builauncher/default.toml` to `~/.config/builauncher/menu.toml`. An item has
one of `exec`, 1 to 8 child `item` tables (BUI's pie has 8 slots), or `places = true`. The top pie
takes 7, since Search has the eighth. `icon`
is a Blender icon name. Bad items are rejected at load.

- `scale` (default 1) sizes the pie and the search. It is BUI's UI scale.
- An item with `places = true` is a sub-pie of Home, Documents, Downloads, Music,
  Pictures, Videos and the Trash (Desktop too, in search). The default Files item is one. Qt's `QStandardPaths` finds
  the folders: XDG user-dirs on Linux, Known Folders on Windows, and the standard
  folders on macOS. The trash has no standard path; on Linux it is `trash:///`.

## BUI

The Qt host and the gesture code exist only because BUI cannot do these yet.
[docs/bui-gaps.md](docs/bui-gaps.md) lists the gaps and a proposed BUI changelog
that would let builauncher use buipy alone.

## Checklist

- [x] Menu tree from TOML config, validated at load (8 slots per pie)
- [x] Fuzzy search over menu actions and `.desktop` apps
- [x] BUI pie with nested sub-pies and a Back slot
- [x] Type-to-search while the pie is open, Return runs the top hit
- [x] Frameless translucent window (Qt host, alpha matted from BUI's raster)
- [x] Window at the pointer on X11; on Wayland a centred, borderless layer-shell overlay
- [x] Daemon with a fast trigger client
- [x] Files sub-pie of the platform's standard folders, and a `scale` setting
- [x] `builauncher install`: XDG autostart, and a global shortcut from the portal
- [x] Gestures: hold and release, double tap, drag pick, centre back, dismissal
- [x] Results in Blender's UI list: icons, Up and Down move the lit row, Return or a click runs it
- [ ] Drop Qt when BUI has the features in docs/bui-gaps.md
