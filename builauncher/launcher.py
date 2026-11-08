"""The launcher window: a pie of commands at the pointer, and type-to-search.

Kando's rules kept where BUI's pie allows: a sub-pie has a Back slot to its
parent, Escape closes, and typing at any time searches every command.
"""
import math
from collections.abc import Callable

import buipy
from bui.components import App, ListView, MenuItem, PieMenu, SearchField
from bui.components.core import EV_SUBMIT

from .apps import run
from .fuzzy import search
from .menu import Action, Menu

ROWS = 8
# window in kit units: the search row, then the pie (radius 5 units, items about 6 wide)
WIDTH, SEARCH_HEIGHT, PIE_HEIGHT = 24, 2, 15
Entry = tuple[str, Action]  # (menu path or "App", action)
FLICK, DEAD_ZONE = 2, 1.5  # kit units: shortest stroke that picks; centre click radius


class QueryField(SearchField):
    """Live search box; Return calls on_submit (BUI's EV_SUBMIT)."""

    def __init__(self, on_change: Callable[[str], None], on_submit: Callable[[], None]) -> None:
        super().__init__(live=True, placeholder="Type to search", on_change=on_change)
        self.on_submit = on_submit
        self.set("events", True)

    def _on_event(self, kind, ref, a, b):
        if kind == EV_SUBMIT:
            self.on_submit()
        else:
            super()._on_event(kind, ref, a, b)


class Launcher:
    def __init__(self, menu: Menu, entries: list[Entry], close: Callable[[], None]) -> None:
        self._menu, self._entries, self._close = menu, entries, close
        self._back: Callable[[], None] = close  # the centre and Back open the parent, or close at the root
        self._found: list[Entry] = []
        self.field = QueryField(self._query, self._submit)
        # Blender's UI list: icons, left-aligned names, the selected row lit; a click runs it
        self._list = ListView(rows=ROWS, visible=False, on_change=lambda i: self._launch(self._found[i][1]))
        u = buipy.kit_unit()
        self.size = (WIDTH * u, (SEARCH_HEIGHT + PIE_HEIGHT) * u)
        self._center = (self.size[0] // 2, self.size[1] // 2)
        # the search row and its results show in place of the pie
        self.app = App("builauncher", self.size, self.field, self._list)
        self.app.bind("Tab", self.reset)

    @property
    def searching(self) -> bool:
        return bool(self.field.get("visible"))

    def opaque(self) -> list[tuple[int, int, int, int]]:
        """Rects (x, y, w, h) that BUI fills: the search row, the result rows, the pie items."""
        shown = [self._list.rect] if self._found else []
        pie = (rect for _, rect in self.app.ctx.menu_rows(-1)) if self.app.ctx.popup_count() else ()
        return [*([self.field.rect] if self.searching else []), *shown, *pie]

    def reset(self) -> None:
        """No search, root pie: the state each time the menu opens."""
        self.field.set_value("")
        self.field.set("visible", False)
        self.open_pie()

    def search_only(self) -> None:
        self.app.ctx.close_popups()
        self.field.set("visible", True)
        self.app.ctx.focus_node(self.field)

    def flick(self, dx: float, dy: float) -> bool:
        """Pick the pie item in the stroke's direction, as Kando's marking mode. False if none."""
        u = buipy.kit_unit()
        if math.hypot(dx, dy) < FLICK * u or not self.app.ctx.popup_count():
            return False
        cx, cy = self._center
        aim = math.atan2(dy, dx)
        x, y, w, h = min((rect for _, rect in self.app.ctx.menu_rows(-1)), key=lambda r: abs(
            math.remainder(math.atan2(r[1] + r[3] / 2 - cy, r[0] + r[2] / 2 - cx) - aim, math.tau)))
        self.app.ctx.press(x + w // 2, y + h // 2, 8)
        self.app.ctx.release(x + w // 2, y + h // 2, 0)
        return True

    def click_empty(self, x: int, y: int) -> None:
        """A click on no widget: the pie centre goes back, elsewhere closes."""
        near = math.dist((x, y), self._center) < DEAD_ZONE * buipy.kit_unit()
        (self._back if near and self.app.ctx.popup_count() else self._close)()

    def open_pie(self, path: tuple[Menu, ...] = ()) -> None:
        """Open the last sub-menu in path, or the root when path is empty."""
        menu = path[-1] if path else self._menu
        self._back = (lambda: self.open_pie(path[:-1])) if path else self._close
        # slot 1 (W): Back in a sub-pie, Search at the root
        first = (MenuItem("Back", self._back, icon="BACK") if path
                 else MenuItem("Search", self.search_only, icon="VIEWZOOM"))
        self.app.ctx.set_pointer(*self._center)  # a pie opens at the pointer: keep it inside the window
        PieMenu.show(self.app.ctx, [first, *(self._pie_item(i, path) for i in menu.items)], menu.name if path else "")

    def _pie_item(self, item: Action | Menu, path: tuple[Menu, ...]) -> MenuItem:
        match item:
            case Action():
                return MenuItem(item.name, lambda: self._launch(item), icon=item.icon or None)
            case Menu():
                return MenuItem(item.name, lambda: self.open_pie((*path, item)), icon=item.icon or None)

    def step(self, delta: int) -> None:
        """Move the lit result row (Up, Down)."""
        if self._found:
            self._list.set_value(max(0, min(len(self._found) - 1, self._list.value + delta)), notify=False)

    def _query(self, text: str) -> None:
        self._found = search(text, self._entries, key=lambda e: e[1].name, limit=ROWS) if text else []
        self._list.set("icons", ["WINDOW" if path == "App" else a.icon or "PLAY" for path, a in self._found])
        self._list.items = [f"{a.name}    {path}" if path and path != "App" else a.name for path, a in self._found]
        self._list.set("rows", max(len(self._found), 1))
        self._list.set_value(0, notify=False)
        self._list.set("visible", bool(self._found))
        self.app.ctx.close_popups()

    def _submit(self) -> None:
        if self._found:
            self._launch(self._found[self._list.value][1])

    def _launch(self, action: Action) -> None:
        run(action.exec)
        self._close()
