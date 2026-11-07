# buiemenu

A pie-menu launcher. Press a hotkey, flick to a command, or type to fuzzy-search
every command and installed app. Python + QML (PySide6); the UI is plain QML,
so it is themed like a Quickshell config.

## Use

    python -m buiemenu [menu.toml]

Bind that command to a hotkey in your desktop (KDE: System Settings > Shortcuts).

- **Click** a slot: run it, or open the submenu.
- **Flick** (press, drag, release): a sharp turn or a short pause opens the
  submenu under the stroke; release runs the action. Chain submenus in one stroke.
- **Back**: the dot toward the parent, right click, or Backspace.
- **Type** at any time: fuzzy search over all menu actions and `.desktop` apps.
  Up/Down/Tab move, Enter runs, Esc clears, then closes.

On X11 the pie opens at the pointer; on Wayland, at the screen centre.

## Config

Copy `buiemenu/default.toml` to `~/.config/buiemenu/menu.toml`. An item has
either `exec` or child `item` tables; `icon` is an icon theme name or an
absolute path. `[theme]` keys: `background surface foreground muted accent font
radius item_size dead_zone`.

## Design

Gesture rules follow Kando's marking mode (min stroke, 20 degree corner, 100 ms
pause, 15 px drag threshold, back slot toward the parent). Logic is pure Python
(`menu`, `fuzzy`, `gesture`, `pie`, `apps`) and tested; QML only draws.

    python -m pytest

## Checklist

- [x] Menu tree from TOML config, validated at load
- [x] Fuzzy search over menu actions and `.desktop` apps
- [x] Gesture detector (marking mode: corner or pause selects a submenu)
- [x] Pie geometry: slots, dead zone, back slot toward parent
- [x] QML overlay: pie, hover highlight, nested submenus, results list
- [x] Type-to-search mid-menu, keyboard navigation, launch
- [x] Theme from config
- [ ] Daemon mode for instant open (keep the process warm, toggle by socket)
- [ ] Wayland: open at pointer (layer-shell)
