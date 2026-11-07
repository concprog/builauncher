"""The launcher window: a pie of commands at the pointer, and type-to-search.

Kando's rules kept where BUI's pie allows: a sub-pie has a Back slot to its
parent, Escape closes, and typing at any time searches every command.
"""
from collections.abc import Callable

from bui.components import App, Button, Column, MenuItem, PieMenu, SearchField
from bui.components.core import EV_SUBMIT

from .apps import run
from .fuzzy import search
from .menu import Action, Menu

ROWS = 8
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
        self._rows = [Button("", lambda i=i: self._launch(self._found[i][1]), emboss=False, visible=False)
                      for i in range(ROWS)]
        self.app = App("buiemenu", (520, 360), self.field, Column(*self._rows, spacing=0))
        self.app.bind("Tab", self.open_pie)
        self.app.bind("Escape", quit)

    def open_pie(self, menu: Menu | None = None, parent: Menu | None = None) -> None:
        menu = menu or self._menu
        back = [MenuItem("Back", lambda: self.open_pie(parent), icon="BACK")] if parent else []
        PieMenu.show(self.app.ctx, [*back, *map(lambda i: self._pie_item(i, menu), menu.items)], menu.name)

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
            row.set("text", f"{entry[1].name}   · {entry[0]}" if entry else "")
            row.set("icon", entry[1].icon if entry and entry[0] != "App" else "")
        self.app.ctx.close_popups()

    def _submit(self) -> None:
        if self._found:
            self._launch(self._found[0][1])

    def _launch(self, action: Action) -> None:
        run(action.exec)
        self._quit()
