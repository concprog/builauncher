# What BUI could do for buiemenu

buiemenu does not change BUI. Each item below is code in buiemenu that works
around something BUI does not have. If BUI had it, the code could go, and with
items 1 to 4 the PyQt host could go too.

## Gaps and their workarounds

| # | BUI today | buiemenu's workaround | Cost |
| --- | --- | --- | --- |
| 1 | The Linux hosts do not implement `alpha`. The Wayland buffer is XRGB8888, and X11 uses an opaque visual. | A Qt window. `window.matte` turns grey background pixels back into alpha. | Square corners show grey slivers, and grey widgets outside the widget rects become translucent. A numpy pass runs on every frame. |
| 2 | The Linux hosts do not implement `override` (no frame) or `topmost`. | Qt `FramelessWindowHint`, `WindowStaysOnTopHint`, `Tool`. | Needs Qt. |
| 3 | The Wayland host has only xdg-shell toplevels. KWin and tiling compositors tile them and place them. | layer-shell-qt, reached through ctypes (`window.layer_surface`). | Needs Qt, a C++ mangled symbol, and layer-shell-qt. |
| 4 | Hosts do not hide and show a window without destroying it, and do not report focus loss to Python. | Qt `hide`, `show` and `focusOutEvent`. | Needs Qt. |
| 5 | The pie picks on click only. Blender's pie also picks on release after a drag, and on hotkey release after `U.pie_tap_timeout`. | `Launcher.flick` presses and releases at the centre of the item in the stroke's direction. `Overlay` times the hold and tracks the stroke. | A second direction rule beside BUI's `pie_dir_hot`. |
| 6 | No pie sub-menus. Blender calls `wm.call_menu_pie` from a pie item. | `Launcher.open_pie(path)` closes the pie and opens a new one, with a Back slot. | No animation between levels; buiemenu keeps the menu path itself. |
| 7 | `PieMenu.show` opens at the context's pointer. | `ctx.set_pointer(centre)` before each `show`. | A fake pointer move. |
| 8 | No hit test from Python. | `Launcher.opaque()` collects `field.rect`, the rows' `rect` and `ctx.menu_rows(-1)`, and `Overlay._on_widget` tests them. | buiemenu must know every widget it shows. |
| 9 | `SearchField` has no `on_submit`. While it edits, it takes Up and Down. | `QueryField` sets `events` and catches `EV_SUBMIT`. | No keyboard navigation through results. |
| 10 | Only `kit_set_theme("dark" or "light")`. No single theme colour can be set. | The matting needs the region background to be grey and asserts it. | A theme with a coloured background breaks the matting. |

Out of scope for BUI: global shortcuts (the desktop binds `buiemenu`), the
daemon socket and the fuzzy search.

## Proposed BUI changelog

This is a proposal, not applied. It follows BUI's `CHANGELOG.md` format, and each
item follows the Blender source that it names.

```markdown
## [Unreleased]

### Added
- **Transparent windows on Linux.** The `alpha` window property now works on Wayland
  (`wl_shm` ARGB8888 buffers) and X11 (a 32-bit ARGB visual). With `alpha`, the region
  background is clear and only widgets, popups and their shadows are drawn. The raster
  gains `argb32()` (premultiplied), so Python hosts get the alpha too.
- **`override` and `topmost` on Linux.** `override` gives a window with no frame and no
  decoration (`xdg-decoration` client side on Wayland, `_MOTIF_WM_HINTS` and
  override-redirect on X11). `topmost` keeps it above other windows.
- **Wayland layer-shell windows.** A new `layer` window property (`"overlay"`, `"top"`,
  `"bottom"`, `"background"`), with `anchors` and `keyboard` (`"none"`, `"exclusive"`,
  `"on_demand"`), uses `zwlr_layer_shell_v1` when the compositor offers it. Without
  anchors, the compositor centres the window. Launchers, docks and panels need no
  toolkit.
- **`App.hide()` and `App.show()`** keep the window and its context. `on_focus_out` is
  called when the window loses keyboard focus.
- **Pie: drag and hotkey-release picks,** as Blender's `ui_pie_handler` does. A press
  that is dragged past `U.pie_menu_threshold` picks the direction's item on release. A
  pie opened by a key held longer than `U.pie_tap_timeout` picks on that key's release.
  `PieMenu.show(..., key=...)` names the key.
- **Pie sub-menus.** A `MenuItem` can hold a `PieMenu`. Picking it opens the sub-pie at
  the same centre, as `wm.call_menu_pie` does. Clicking the centre returns to the
  parent.
- **`PieMenu.show(ctx, items, title, at=(x, y))`** opens a pie at a point without
  moving the pointer.
- **`ctx.hit(x, y)`** returns the node under a point, or `None`.
- **`SearchField(on_submit=...)`** is called on Return. While the field edits, Up and
  Down go to `on_navigate(step)`.
- **`kit_set_theme_color(name, rgba)`** sets one theme colour, as Blender's theme
  editor does.

### Changed
- Python: `bui.components.App` accepts `alpha`, `override`, `topmost`, `layer`,
  `anchors` and `keyboard`, and passes them to the host.
```

With these, `window.py`, numpy and PySide6 could go. `app.py` would build one
`App(..., alpha=True, override=True, layer="overlay", keyboard="exclusive")` and run
the daemon socket with the standard library's `socket` and BUI's own event loop
(a `ctx` file-descriptor watch would also be needed, or a BUI timer that polls the
socket).
