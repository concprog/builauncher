"""Menu tree: an item is an Action (runs a command) or a Menu (holds items)."""
from collections.abc import Iterator, Mapping
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
Pies = Mapping[str, "list[dict] | tuple[Action, ...]"]  # name -> config tables, or built-in actions


def parse(raw: dict, pies: Pies, seen: tuple[str, ...] = ()) -> Item:
    """Make an item from a config table: `exec` runs a command, `pie = "name"` opens that sub-pie.
    Raises ValueError on a bad table, an unknown or too full pie, or a pie that opens itself."""
    name, icon = raw.get("name"), raw.get("icon", "")
    if not name:
        raise ValueError(f"item without name: {raw}")
    match raw.get("exec"), raw.get("pie"):
        case str(cmd), None:
            return Action(name, cmd, icon)
        case None, str(pie) if pie in seen:
            raise ValueError(f"pie {pie!r} opens itself: {' > '.join((*seen, pie))}")
        case None, str(pie) if pie not in pies:
            raise ValueError(f"item {name!r}: no pie {pie!r}")
        case None, str(pie) if not 0 < len(pies[pie]) < PIE_SLOTS:
            raise ValueError(f"pie {pie!r} needs 1 to {PIE_SLOTS - 1} items (one slot is Back)")
        case None, str(pie):
            return Menu(name, tuple(i if isinstance(i, Action) else parse(i, pies, (*seen, pie))
                                    for i in pies[pie]), icon)
        case _:
            raise ValueError(f"item {name!r} needs exactly one of 'exec' or 'pie'")


def actions(menu: Menu, path: str = "") -> Iterator[tuple[str, Action]]:
    """Yield every action under menu with its path, e.g. 'System / Lock'."""
    for item in menu.items:
        here = f"{path}{item.name}"
        match item:
            case Action():
                yield path.removesuffix(" / "), item
            case Menu():
                yield from actions(item, f"{here} / ")
