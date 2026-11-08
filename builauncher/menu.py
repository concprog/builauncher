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


def parse(raw: dict, places: tuple[Action, ...] = ()) -> Item:
    """Make an item from a config table; `places = true` makes a sub-pie of places.
    Raises ValueError on a bad table."""
    name, icon = raw.get("name"), raw.get("icon", "")
    if not name:
        raise ValueError(f"item without name: {raw}")
    match raw.get("exec"), raw.get("item"), raw.get("places", False):
        case str(cmd), None, False:
            return Action(name, cmd, icon)
        case None, list(children), False if 0 < len(children) <= PIE_SLOTS:
            return Menu(name, tuple(parse(c, places) for c in children), icon)
        case None, None, True:
            return Menu(name, places, icon)
        case _:
            raise ValueError(f"item {name!r} needs exactly one of 'exec', 'places = true' "
                             f"or 1 to {PIE_SLOTS} 'item' tables")


def actions(menu: Menu, path: str = "") -> Iterator[tuple[str, Action]]:
    """Yield every action under menu with its path, e.g. 'System / Lock'."""
    for item in menu.items:
        here = f"{path}{item.name}"
        match item:
            case Action():
                yield path.removesuffix(" / "), item
            case Menu():
                yield from actions(item, f"{here} / ")
