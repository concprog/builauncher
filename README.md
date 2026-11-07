# buiemenu

A pie-menu launcher. Press a hotkey, flick to a command, or type to fuzzy-search
every command and installed app. Python + QML (PySide6); the UI is plain QML,
so it is themed like a Quickshell config.

## Checklist

- [ ] Menu tree from TOML config (`~/.config/buiemenu/menu.toml`), validated at load
- [ ] Fuzzy search over menu actions and `.desktop` apps
- [ ] Gesture detector (marking mode: corner or pause selects a submenu)
- [ ] Pie geometry: slots, dead zone, back slot toward parent
- [ ] QML overlay: pie, hover highlight, nested submenus, results list
- [ ] Type-to-search mid-menu, keyboard navigation, launch
- [ ] Theme from config
