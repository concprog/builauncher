"""Load the menu and theme from ~/.config/buiemenu/menu.toml (or the bundled default)."""
import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from .menu import Menu, parse

DEFAULT = Path(__file__).with_name("default.toml")


@dataclass(frozen=True, slots=True)
class Theme:
    background: str = "#cc11111b"
    surface: str = "#1e1e2e"
    foreground: str = "#cdd6f4"
    muted: str = "#7f849c"
    accent: str = "#89b4fa"
    font: str = "sans-serif"
    radius: int = 130
    item_size: int = 56
    dead_zone: int = 40


@dataclass(frozen=True, slots=True)
class Config:
    menu: Menu
    theme: Theme = field(default_factory=Theme)
    apps: bool = True


def user_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "buiemenu" / "menu.toml"


def load(path: Path | None = None) -> Config:
    path = path or next((p for p in (user_path(),) if p.exists()), DEFAULT)
    raw = tomllib.loads(path.read_text())
    known = {f.name for f in fields(Theme)}
    unknown = raw.get("theme", {}).keys() - known
    if unknown:
        raise ValueError(f"{path}: unknown theme keys {sorted(unknown)}")
    return Config(
        menu=Menu("root", tuple(map(parse, raw.get("item", [])))),
        theme=Theme(**raw.get("theme", {})),
        apps=raw.get("apps", True),
    )
