"""Load the menu from ~/.config/builauncher/menu.toml (or the bundled default)."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .items.menu import PIE_SLOTS, Menu, parse
from .items.places import places
from .system import WINDOWS, config_dir

DEFAULT = Path(__file__).with_name("default-windows.toml" if WINDOWS else "default.toml")
SHORTCUT = "CTRL+ALT+space"  # XDG shortcuts format
SCALE = 1.0  # BUI ui scale; 1 is Blender's default
DWELL = 0.4  # s a drag waits still on a submenu or Back before it opens


@dataclass(frozen=True, slots=True)
class Config:
    menu: Menu
    apps: bool = True
    shortcut: str = SHORTCUT  # asked for at the first bind; then the desktop's settings own it
    scale: float = SCALE
    dwell: float = DWELL


def user_path() -> Path:
    return config_dir() / "menu.toml"


def load(path: Path | None = None) -> Config:
    path = path or (user_path() if user_path().exists() else DEFAULT)
    raw = tomllib.loads(path.read_text())
    pies = {"places": places(), **raw.get("pie", {})}  # built-in pies; a [[pie.places]] replaces one
    items = tuple(parse(item, pies) for item in raw.get("item", []))
    if not 0 < len(items) < PIE_SLOTS:
        raise ValueError(f"{path}: the top menu needs 1 to {PIE_SLOTS - 1} items (one slot is Search)")
    scale = float(raw.get("scale", SCALE))
    if not 0.5 <= scale <= 4:
        raise ValueError(f"{path}: scale must be 0.5 to 4")
    dwell = float(raw.get("dwell", DWELL))
    if not 0.05 <= dwell <= 2:
        raise ValueError(f"{path}: dwell must be 0.05 to 2")
    return Config(Menu("builauncher", items), raw.get("apps", True), raw.get("shortcut", SHORTCUT), scale,
                  dwell)
