# buiemenu

A pie-menu launcher on [BUI](https://github.com/ppmpreetham/BUI)'s Python binding
(Blender's pie menu and widgets). Press a hotkey, pick from a pie, or type to
fuzzy-search every command and installed app.

## Use

    pip install blenderui      # or: BUIPY_BUILD_DIR=<BUI>/build/bindings/python PYTHONPATH=<BUI>/bindings/python
    python -m buiemenu [menu.toml]

Bind that command to a hotkey in your desktop.

- **Pie**: move toward an item and click (Blender's pie). A sub-pie has a
  **Back** slot to its parent (from Kando). Tab reopens the top pie.
- **Type** at any time: fuzzy search over menu actions and `.desktop` apps.
  Return runs the top hit, a click runs any row, Escape quits.

## Config

Copy `buiemenu/default.toml` to `~/.config/buiemenu/menu.toml`. An item has
either `exec` or 1 to 8 child `item` tables (BUI's pie has 8 slots). `icon`
is a Blender icon name. Bad items are rejected at load.

    python -m pytest

## Checklist

- [x] Menu tree from TOML config, validated at load (8 slots per pie)
- [x] Fuzzy search over menu actions and `.desktop` apps
- [x] BUI pie with nested sub-pies and a Back slot
- [x] Type-to-search while the pie is open, Return runs the top hit
- [ ] BUI pie: drag-release pick and hotkey-release pick (Blender has both; BUI picks on click only)
- [ ] Window at the pointer, borderless (BUI host)
- [ ] Daemon mode for instant open
