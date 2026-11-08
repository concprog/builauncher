"""Menu tree: an item is an Action (runs a command) or a Menu (holds items)."""
from collections.abc import Iterator
from dataclasses import dataclass

PIE_SLOTS = 8  # BUI's pie, as Blender's: W, E, S, N, NW, NE, SW, SE


@dataclass(frozen=True, slots=True)
class Action:
    name: str
    exec: str
    icon: str = ""


@dataclass(frozen=True, slots=True)
class Menu:
    name: str
    items: tuple["Action | Menu", ...]
    icon: str = ""


Item = Action | Menu


def parse(raw: dict) -> Item:
    """Make an item from a config table. Raises ValueError on a bad table."""
    name, icon = raw.get("name"), raw.get("icon", "")
    if not name:
        raise ValueError(f"item without name: {raw}")
    match raw.get("exec"), raw.get("item"):
        case str(cmd), None:
            return Action(name, cmd, icon)
        case None, list(children) if 0 < len(children) <= PIE_SLOTS:
            return Menu(name, tuple(map(parse, children)), icon)
        case _:
            raise ValueError(f"item {name!r} needs exactly one of 'exec' or 1 to {PIE_SLOTS} 'item' tables")


def actions(menu: Menu, path: str = "") -> Iterator[tuple[str, Action]]:
    """Yield every action under menu with its path, e.g. 'System / Lock'."""
    for item in menu.items:
        here = f"{path}{item.name}"
        match item:
            case Action():
                yield path.removesuffix(" / "), item
            case Menu():
                yield from actions(item, f"{here} / ")
