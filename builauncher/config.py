"""Load the menu from ~/.config/builauncher/menu.toml (or the bundled default)."""
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .menu import PIE_SLOTS, Menu, parse
from .places import places

DEFAULT = Path(__file__).with_name("default.toml")
SHORTCUT = "CTRL+ALT+space"  # XDG shortcuts format
SCALE = 1.0  # BUI ui scale; 1 is Blender's default


@dataclass(frozen=True, slots=True)
class Config:
    menu: Menu
    apps: bool = True
    shortcut: str = SHORTCUT  # asked for at the first bind; then the desktop's settings own it
    scale: float = SCALE


def user_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "builauncher" / "menu.toml"


def load(path: Path | None = None) -> Config:
    path = path or (user_path() if user_path().exists() else DEFAULT)
    raw = tomllib.loads(path.read_text())
    found = places()
    items = tuple(parse(item, found) for item in raw.get("item", []))
    if not 0 < len(items) < PIE_SLOTS:
        raise ValueError(f"{path}: the top menu needs 1 to {PIE_SLOTS - 1} items (one slot is Search)")
    scale = float(raw.get("scale", SCALE))
    if not 0.5 <= scale <= 4:
        raise ValueError(f"{path}: scale must be 0.5 to 4")
    return Config(Menu("builauncher", items), raw.get("apps", True), raw.get("shortcut", SHORTCUT), scale)
