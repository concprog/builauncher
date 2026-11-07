"""QML bridge: pointer and key input in, pie and search state out."""
from dataclasses import asdict
from math import dist
from time import monotonic

from PySide6.QtCore import Property, QObject, QPointF, QSize, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtQuick import QQuickImageProvider

from .apps import apps, run
from .config import Config
from .fuzzy import search
from .gesture import Gesture, Point
from .menu import Action, actions
from .pie import Pie

DRAG = 15.0
NONE = -2  # hovered value: nothing


class IconProvider(QQuickImageProvider):
    """image://icon/<theme name or absolute path>"""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Pixmap)

    def requestPixmap(self, name: str, size: QSize, requested: QSize) -> QPixmap:  # noqa: N802
        side = max(requested.width(), 64)
        icon = QIcon(name) if name.startswith("/") else QIcon.fromTheme(name)
        return icon.pixmap(side, side)


class Bridge(QObject):
    changed = Signal()
    searched = Signal()
    finished = Signal()

    def __init__(self, cfg: Config, center: Point) -> None:
        super().__init__()
        self._theme = asdict(cfg.theme)
        self._pie = Pie(cfg.menu, cfg.theme.radius, cfg.theme.dead_zone)
        self._pie.open(center)
        self._gesture = Gesture()
        self._entries = [(path, a) for path, a in actions(cfg.menu)] + [("App", a) for a in (apps() if cfg.apps else ())]
        self._pointer: Point = center
        self._pressed: Point | None = None
        self._dragging = False
        self._hovered = NONE
        self._query = ""
        self._results: list[tuple[str, Action]] = []
        self._index = 0

    # pie state

    @Property("QVariantMap", constant=True)
    def theme(self) -> dict:
        return self._theme

    @Property(QPointF, notify=changed)
    def center(self) -> QPointF:
        return QPointF(*self._pie.level.center)

    @Property("QVariantList", notify=changed)
    def trail(self) -> list:
        return [QPointF(*lv.center) for lv in self._pie.stack]

    @Property("QVariantList", notify=changed)
    def slots(self) -> list:
        items, angles = self._pie.level.menu.items, self._pie.angles()
        return [{"name": i.name, "icon": i.icon, "angle": a, "menu": not isinstance(i, Action)}
                for i, a in zip(items, angles)]

    @Property(float, notify=changed)
    def back(self) -> float:
        return -1.0 if self._pie.level.back is None else self._pie.level.back

    @Property(int, notify=changed)
    def hovered(self) -> int:
        return self._hovered

    @Property(str, notify=changed)
    def title(self) -> str:
        lv = self._pie.level
        match self._hovered:
            case -2:
                return "" if len(self._pie.stack) == 1 else lv.menu.name
            case -1:
                return "Back"
            case i:
                return lv.menu.items[i].name

    # pointer

    def _hover(self, p: Point) -> None:
        self._pointer = p
        hit = self._pie.hit(p)
        self._hovered = NONE if hit is None else hit
        self.changed.emit()

    def _select(self, p: Point, gesture: bool) -> None:
        action = self._pie.select(p, at_pointer=gesture, submenu_only=gesture)
        if action:
            self._launch(action)
        self._hover(self._pointer)

    @Slot(float, float)
    def press(self, x: float, y: float) -> None:
        self._pressed, self._dragging = (x, y), False
        self._gesture.reset((x, y))

    @Slot(float, float)
    def move(self, x: float, y: float) -> None:
        if self._pressed and not self._dragging:
            self._dragging = dist(self._pressed, (x, y)) > DRAG
        if self._dragging and (corner := self._gesture.motion((x, y), monotonic())):
            self._select(corner, gesture=True)
        self._hover((x, y))

    @Slot()
    def tick(self) -> None:
        if self._dragging and (p := self._gesture.poll(self._pointer, monotonic())):
            self._select(p, gesture=True)

    @Slot(float, float)
    def release(self, x: float, y: float) -> None:
        self._pressed = None
        self._select((x, y), gesture=False)
        self._dragging = False

    @Slot()
    def back_out(self) -> None:
        if len(self._pie.stack) > 1:
            self._pie.stack.pop()
            self._hover(self._pointer)

    # search

    @Property(str, notify=searched)
    def query(self) -> str:
        return self._query

    @Property("QVariantList", notify=searched)
    def results(self) -> list:
        return [{"name": a.name, "path": path, "icon": a.icon} for path, a in self._results]

    @Property(int, notify=searched)
    def index(self) -> int:
        return self._index

    @Slot(str)
    def type(self, text: str) -> None:
        self._set_query(self._query + text)

    @Slot()
    def erase(self) -> None:
        if self._query:
            self._set_query(self._query[:-1])
        else:
            self.back_out()

    @Slot(int)
    def step(self, delta: int) -> None:
        if self._results:
            self._index = (self._index + delta) % len(self._results)
            self.searched.emit()

    @Slot()
    def accept(self) -> None:
        if self._results:
            self._launch(self._results[self._index][1])

    @Slot()
    def cancel(self) -> None:
        if self._query:
            self._set_query("")
        else:
            self.finished.emit()

    def _set_query(self, q: str) -> None:
        self._query, self._index = q, 0
        self._results = search(q, self._entries, key=lambda e: e[1].name) if q else []
        self.searched.emit()

    def _launch(self, action: Action) -> None:
        run(action.exec)
        self.finished.emit()
