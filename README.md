# buiemenu

A pie-menu launcher on [BUI](https://github.com/ppmpreetham/BUI)'s Python binding
(Blender's pie menu and widgets), shown in a frameless, translucent Qt window.
Press a hotkey, pick from a pie, or type to
fuzzy-search every command and installed app.

## Use

    pip install blenderui      # or: BUIPY_BUILD_DIR=<BUI>/build/bindings/python PYTHONPATH=<BUI>/bindings/python
    buiemenu --daemon [menu.toml] &   # once per session (autostart)
    buiemenu                          # bind this to a hotkey

`buiemenu` sends a trigger to the daemon over `$XDG_RUNTIME_DIR/buiemenu.sock`.
It does not load Qt, so it takes about 60 ms. With no daemon, it opens the menu
once and exits when the menu closes.

Gestures (from Kando and Blender's pie):

| Input | Result |
| --- | --- |
| Hotkey tap | Open the pie. Pick with a click. |
| Hotkey held, pointer moved, hotkey released | Pick the item in that direction. A hold is 0.2 s, Blender's `pie_tap_timeout`. |
| Hotkey twice within 0.4 s | Search only, with no pie. |
| Hotkey while open | Close. |
| Mouse drag from empty space | Pick the item in the drag direction (Kando's marking mode). |
| Click the pie centre | Back to the parent pie, or close at the top. |
| Click outside the widgets, Escape, focus lost | Close. |
| Typing | Fuzzy search over menu actions and `.desktop` apps. Return runs the top hit. |
| Tab | Reopen the top pie. |

On Wayland the window is a centred, borderless layer-shell overlay that takes the
keyboard (needs `layer-shell-qt`). On X11 it opens at the pointer.

## Config

Copy `buiemenu/default.toml` to `~/.config/buiemenu/menu.toml`. An item has
either `exec` or 1 to 8 child `item` tables (BUI's pie has 8 slots). `icon`
is a Blender icon name. Bad items are rejected at load.

    python -m pytest

## BUI

The Qt host and the gesture code exist only because BUI cannot do these yet.
[docs/bui-gaps.md](docs/bui-gaps.md) lists the gaps and a proposed BUI changelog
that would let buiemenu use buipy alone.

## Checklist

- [x] Menu tree from TOML config, validated at load (8 slots per pie)
- [x] Fuzzy search over menu actions and `.desktop` apps
- [x] BUI pie with nested sub-pies and a Back slot
- [x] Type-to-search while the pie is open, Return runs the top hit
- [x] Frameless translucent window (Qt host, alpha matted from BUI's raster)
- [x] Window at the pointer on X11; on Wayland a centred, borderless layer-shell overlay
- [x] Daemon with a fast trigger client
- [x] Gestures: hold and release, double tap, drag pick, centre back, dismissal
- [ ] Up and Down through results while typing (BUI's field takes those keys)
- [ ] Drop Qt when BUI has the features in docs/bui-gaps.md
