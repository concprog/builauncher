"""The launcher window: a pie of commands at the pointer, and type-to-search.

A sub-pie has a Back slot to its parent, Escape closes, and typing at any time
searches every command.
"""
import math
from collections.abc import Callable

import buipy
from bui.components import App, Box, ListView, MenuItem, PieMenu, SearchField, Separator
from bui.components.core import EV_SUBMIT

from .fuzzy import search
from .items.menu import Action, Menu
from .system import run

SEARCH_PAD = 8  # px around the search bar, on Blender's box background
ROWS = 6  # results below the pie centre fit in the window's lower half
# window in kit units: the search row, then the pie (radius 5 units, items about 6 wide)
WIDTH, SEARCH_HEIGHT, PIE_HEIGHT = 24, 2, 15
Entry = tuple[str, Action]  # (menu path or "App", action)
FLICK, DEAD_ZONE = 2, 1.5  # kit units: shortest stroke that picks; centre click radius
# BUI's pie slots per item index (kit_menus.c g_pie_rdir/g_pie_angle), y-down degrees: W E S N NW NE SW SE
SLOTS = (180, 0, 90, -90, -135, -45, 135, 45)


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
        self._drags: list[Callable[[], None] | None] = []  # per pie slot: the pick a drag dwell may make
        self._found: list[Entry] = []
        self.field = QueryField(self._query, self._submit)
        # Blender's UI list: icons, left-aligned names, the selected row lit; a click runs it
        self._list = ListView(rows=ROWS, visible=False, on_change=lambda i: self._launch(self._found[i][1]))
        u = buipy.kit_unit()
        self.size = (WIDTH * u, (SEARCH_HEIGHT + PIE_HEIGHT) * u)
        self._center = (self.size[0] // 2, self.size[1] // 2)
        # the search row and its results show in place of the pie
        self._gap = Separator(0)  # puts the search bar on the pie centre
        self._bar = Box(self.field, padding=SEARCH_PAD)
        self.app = App("builauncher", self.size, self._gap, self._bar, self._list)
        self.app.render_raster(*self.size)  # lay out once to measure the bar
        _, y, _, h = self._bar.rect
        self._gap.set("factor", (self._center[1] - h // 2 - y) / u)
        self.app.bind("Tab", self.reset)

    @property
    def searching(self) -> bool:
        return bool(self._bar.get("visible"))

    def opaque(self) -> list[tuple[int, int, int, int]]:
        """Rects (x, y, w, h) that BUI fills: the search row, the result rows, the pie items."""
        shown = [self._list.rect] if self._found else []
        pie = (rect for _, rect in self.app.ctx.menu_rows(-1)) if self.app.ctx.popup_count() else ()
        return [*([self._bar.rect] if self.searching else []), *shown, *pie]

    def reset(self) -> None:
        """No search, root pie: the state each time the menu opens."""
        self.field.set_value("")
        self._bar.set("visible", False)
        self.open_pie()

    def search_only(self) -> None:
        self.app.ctx.close_popups()
        self._bar.set("visible", True)
        self.app.ctx.focus_node(self.field)

    def flick(self, start: tuple[int, int], at: tuple[int, int]) -> bool:
        """Pick the item highlighted at the pointer, if a real stroke moved for a direction
        pick: marking mode. False if none."""
        hot = self.hot(*at)
        if hot is None or (not hot[1] and math.dist(at, start) < FLICK * buipy.kit_unit()):
            return False  # nothing is lit, or a direction guess on a mere twitch of a stroke
        x, y, w, h = self.app.ctx.menu_rows(-1)[hot[0]][1]
        self.app.ctx.press(x + w // 2, y + h // 2, 8)
        self.app.ctx.release(x + w // 2, y + h // 2, 0)
        return True

    def click_empty(self, x: int, y: int) -> None:
        """A click on no widget: the pie centre goes back, elsewhere closes."""
        near = math.dist((x, y), self._center) < DEAD_ZONE * buipy.kit_unit()
        (self._back if near and self.app.ctx.popup_count() else self._close)()

    def hot(self, x: int, y: int) -> tuple[int, bool] | None:
        """The pie item highlighted at (x, y): the item under the pointer, else the one the
        pointer's direction from the centre lights — BUI keeps it lit far beyond the radius.
        (index, pointer on the item's rect); None when nothing is lit: no pie, or the dead zone."""
        if not self.app.ctx.popup_count():
            return None
        rows = [r for _, r in self.app.ctx.menu_rows(-1)]
        on_rect = next(((i, r) for i, r in enumerate(rows)
                        if r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]), None)
        if on_rect:
            return on_rect[0], True
        cx, cy = self._center
        if math.dist((x, y), (cx, cy)) < DEAD_ZONE * buipy.kit_unit():
            return None  # the centre's dead zone lights nothing
        # BUI lights the item whose slot direction the pointer is on (g_pie_rdir/g_pie_angle):
        # one atan2 against a constant table, no per-item trig
        aim = math.degrees(math.atan2(y - cy, x - cx))
        i = min(range(len(rows)), key=lambda i: abs(math.remainder(aim - SLOTS[i], 360)))
        return i, False

    def drag_pick(self, x: int, y: int) -> Callable[[], None] | None:
        """The pick a drag dwell may make on the highlighted item: a submenu or Back; None on an Action."""
        hot = self.hot(x, y)
        return None if hot is None else self._drags[hot[0]]

    def open_pie(self, path: tuple[Menu, ...] = ()) -> None:
        """Open the last sub-menu in path, or the root when path is empty."""
        menu = path[-1] if path else self._menu
        self._back = (lambda: self.open_pie(path[:-1])) if path else self._close
        # slot 1 (W): Back in a sub-pie, Search at the root
        first = (MenuItem("Back", self._back, icon="BACK") if path
                 else MenuItem("Search", self.search_only, icon="VIEWZOOM"))
        shown = [first, *(self._pie_item(i, path) for i in menu.items)]
        # drag-through: a dwell may pick only a submenu or Back, never an Action nor Search
        self._drags = [first.on_click if path else None]
        self._drags += [item.on_click if isinstance(src, Menu) else None
                        for src, item in zip(menu.items, shown[1:])]
        self.app.ctx.set_pointer(*self._center)  # a pie opens at the pointer: keep it inside the window
        PieMenu.show(self.app.ctx, shown, menu.name if path else "")

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
