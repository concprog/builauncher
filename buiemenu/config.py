"""Load the menu from ~/.config/buiemenu/menu.toml (or the bundled default)."""
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .menu import PIE_SLOTS, Menu, parse

DEFAULT = Path(__file__).with_name("default.toml")
SHORTCUT = "CTRL+ALT+space"  # XDG shortcuts format


@dataclass(frozen=True, slots=True)
class Config:
    menu: Menu
    apps: bool = True
    shortcut: str = SHORTCUT  # asked for at the first bind; then the desktop's settings own it


def user_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "buiemenu" / "menu.toml"


def load(path: Path | None = None) -> Config:
    path = path or (user_path() if user_path().exists() else DEFAULT)
    raw = tomllib.loads(path.read_text())
    items = raw.get("item", [])
    if not 0 < len(items) <= PIE_SLOTS:
        raise ValueError(f"{path}: the top menu needs 1 to {PIE_SLOTS} items")
    return Config(Menu("buiemenu", tuple(map(parse, items))), raw.get("apps", True),
                  raw.get("shortcut", SHORTCUT))
