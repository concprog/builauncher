"""The launcher window: a pie of commands at the pointer, and type-to-search.

Kando's rules kept where BUI's pie allows: a sub-pie has a Back slot to its
parent, Escape closes, and typing at any time searches every command.
"""
from collections.abc import Callable

import buipy
from bui.components import App, Button, Column, MenuItem, PieMenu, SearchField
from bui.components.core import EV_SUBMIT

from .apps import run
from .fuzzy import search
from .menu import Action, Menu

ROWS = 8
# window in kit units: the search row, then the pie (radius 5 units, items about 6 wide)
WIDTH, SEARCH_HEIGHT, PIE_HEIGHT = 24, 2, 15
Entry = tuple[str, Action]  # (menu path or "App", action)


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
    def __init__(self, menu: Menu, entries: list[Entry], quit: Callable[[], None]) -> None:
        self._menu, self._entries, self._quit = menu, entries, quit
        self._found: list[Entry] = []
        self.field = QueryField(self._query, self._submit)
        # fixed pool: a query changes text and visibility, it does not make nodes
        self._rows = [Button("", lambda i=i: self._launch(self._found[i][1]), visible=False)
                      for i in range(ROWS)]
        u = buipy.kit_unit()
        self._center = (WIDTH * u // 2, SEARCH_HEIGHT * u + PIE_HEIGHT * u // 2)
        self.size = (WIDTH * u, (SEARCH_HEIGHT + PIE_HEIGHT) * u)
        # results take the pie's place while searching
        self.app = App("buiemenu", self.size, self.field, Column(*self._rows, spacing=0))
        self.app.bind("Tab", self.open_pie)
        self.app.bind("Escape", quit)

    def opaque(self) -> list[tuple[int, int, int, int]]:
        """Rects (x, y, w, h) that BUI fills: the search row, the result rows, the pie items."""
        shown = (row.rect for row in self._rows[:len(self._found)])
        pie = (rect for _, rect in self.app.ctx.menu_rows(-1)) if self.app.ctx.popup_count() else ()
        return [self.field.rect, *shown, *pie]

    def open_pie(self, menu: Menu | None = None, parent: Menu | None = None) -> None:
        menu = menu or self._menu
        back = [MenuItem("Back", lambda: self.open_pie(parent), icon="BACK")] if parent else []
        self.app.ctx.set_pointer(*self._center)  # a pie opens at the pointer: keep it inside the window
        PieMenu.show(self.app.ctx, [*back, *(self._pie_item(i, menu) for i in menu.items)],
                     menu.name if parent else "")

    def _pie_item(self, item: Action | Menu, menu: Menu) -> MenuItem:
        match item:
            case Action():
                return MenuItem(item.name, lambda: self._launch(item), icon=item.icon or None)
            case Menu():
                return MenuItem(item.name, lambda: self.open_pie(item, menu), icon=item.icon or None)

    def _query(self, text: str) -> None:
        self._found = search(text, self._entries, key=lambda e: e[1].name, limit=ROWS) if text else []
        for row, entry in zip(self._rows, self._found + [None] * (ROWS - len(self._found))):
            row.set("visible", entry is not None)
            row.set("text", (f"{entry[1].name}   · {entry[0]}" if entry[0] else entry[1].name) if entry else "")
            row.set("icon", entry[1].icon if entry and entry[0] != "App" else "")
        self.app.ctx.close_popups()

    def _submit(self) -> None:
        if self._found:
            self._launch(self._found[0][1])

    def _launch(self, action: Action) -> None:
        run(action.exec)
        self._quit()
