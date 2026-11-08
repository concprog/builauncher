"""Check an installed distribution: run with the wheel or sdist only, no project, no display."""
from pathlib import Path

import builauncher.config as config
from builauncher.__main__ import parser
from builauncher.fuzzy import search
from builauncher.shortcut_windows import parse

for name in ("default.toml", "default-windows.toml"):  # the package data is in the distribution
    menu = config.load(Path(config.__file__).with_name(name)).menu
    assert menu.items, name
assert parser().parse_args(["stop"]).command == "stop"
assert search("firfox", ["Firefox", "Files"], str) == ["Firefox"]
assert parse("CTRL+ALT+space") == (0x3, 0x20)
print("smoke test passed")
