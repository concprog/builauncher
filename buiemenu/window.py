"""Frameless, translucent Qt window that shows a BUI context.

BUI draws into an opaque raster over the region background. This window
makes that background clear again, with no change to BUI:
  - pixels inside widget rects (search row, results, pie items) stay opaque;
  - elsewhere a pixel is the background, maybe under a black shadow, so a grey
    pixel at or below the background gets alpha 1 - v / background.
"""
import ctypes
from collections.abc import Callable, Iterable

import buipy
import numpy as np
from PySide6.QtCore import QObject, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QImage, QKeyEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget
from shiboken6 import getCppPointer, wrapInstance

from bui.components import App

Rect = tuple[int, int, int, int]  # x, y, w, h in raster pixels, as BUI gives them

# Qt key -> X keysym name, as BUI's hosts send them
KEYSYMS = {
    Qt.Key.Key_Return: "Return", Qt.Key.Key_Enter: "KP_Enter", Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Backspace: "BackSpace", Qt.Key.Key_Delete: "Delete", Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Left: "Left", Qt.Key.Key_Right: "Right", Qt.Key.Key_Up: "Up", Qt.Key.Key_Down: "Down",
    Qt.Key.Key_Home: "Home", Qt.Key.Key_End: "End",
}
MODS = ((Qt.KeyboardModifier.ShiftModifier, 1), (Qt.KeyboardModifier.ControlModifier, 2),
        (Qt.KeyboardModifier.AltModifier, 4))
FRAME_MS = 16
# LayerShellQt::Window: no anchors (compositor centres it), overlay layer, exclusive keyboard
LAYER_SHELL = "libLayerShellQtInterface.so.6"
LAYER_GET = "_ZN12LayerShellQt6Window3getEP7QWindow"
LAYER = {"anchors": 0, "layer": 3, "keyboardInteractivity": 1}


def background() -> int:
    """The region background grey (0..255). The matting needs a grey."""
    r, g, b, _ = buipy.kit_theme_color("region_bg")
    assert abs(r - g) < 1e-3 and abs(g - b) < 1e-3, "region background is not grey"
    return round(r * 255)


def layer_surface(widget: QWidget) -> None:
    """Make a Wayland window a centred overlay layer surface. Call before show()."""
    get = getattr(ctypes.CDLL(LAYER_SHELL), LAYER_GET)
    get.restype, get.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
    widget.winId()  # create the QWindow
    surface = wrapInstance(get(getCppPointer(widget.windowHandle())[0]), QObject)
    for name, value in LAYER.items():
        assert surface.setProperty(name, value), name


def matte(bgrx: bytes, w: int, h: int, opaque: Iterable[Rect], bg: int) -> np.ndarray:
    """Premultiplied BGRA from BUI's opaque BGRX raster."""
    px = np.frombuffer(bgrx, np.uint8).reshape(h, w, 4).copy()
    b, g, r = (px[..., i].astype(np.int32) for i in range(3))
    shadow = (b == g) & (g == r) & (r <= bg)
    for x, y, rw, rh in opaque:
        shadow[max(y, 0):y + rh, max(x, 0):x + rw] = False
    px[..., 3] = np.where(shadow, 255 - r * 255 // bg, 255)
    px[..., :3][shadow] = 0  # black shadow, premultiplied
    return px


class Overlay(QWidget):
    def __init__(self, app: App, size: tuple[int, int], opaque: Callable[[], Iterable[Rect]]) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._app, self._size, self._opaque, self._bg = app, size, opaque, background()
        self._image: tuple[np.ndarray, QImage] | None = None
        self._dpr = self.devicePixelRatioF()
        self.resize(round(size[0] / self._dpr), round(size[1] / self._dpr))
        # BUI timers, animations and focus changes: redraw when the context asks
        self._tick = QTimer(self, interval=FRAME_MS, timeout=self._refresh)
        self._tick.start()

    def place(self) -> None:
        """At the pointer on X11. On Wayland, a centred layer surface."""
        if QGuiApplication.platformName() == "wayland":
            return layer_surface(self)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area, pos = screen.availableGeometry(), QCursor.pos()
        centre = pos if area.contains(pos) and not pos.isNull() else area.center()
        rect = QRect(0, 0, self.width(), self.height())
        rect.moveCenter(centre)
        rect.moveTo(min(max(rect.x(), area.left()), area.right() - rect.width()),
                    min(max(rect.y(), area.top()), area.bottom() - rect.height()))
        self.move(rect.topLeft())

    def _refresh(self) -> None:
        if self._app.ctx.needs_render():
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        w, h = self._size
        raster = self._app.render_raster(w, h)
        px = matte(raster.rgb32(), w, h, self._opaque(), self._bg)
        image = QImage(px.data, w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(self._dpr)
        self._image = (px, image)  # QImage borrows px's memory
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawImage(QPointF(0, 0), image)
        painter.end()

    def _at(self, e: QMouseEvent) -> tuple[int, int]:
        p = e.position() * self._dpr
        return round(p.x()), round(p.y())

    def _mods(self, e) -> int:
        held = sum(bit for mod, bit in MODS if e.modifiers() & mod)
        left = isinstance(e, QMouseEvent) and bool(e.buttons() & Qt.MouseButton.LeftButton)
        return held | (8 if left else 0)

    def mousePressEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        press = self._app.ctx.context_menu if e.button() == Qt.MouseButton.RightButton else self._app.ctx.press
        press(*self._at(e), self._mods(e))
        self._refresh()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        self._app.ctx.release(*self._at(e), self._mods(e))
        self._refresh()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        self._app.ctx.motion(*self._at(e), self._mods(e))
        self._refresh()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        keysym = KEYSYMS.get(Qt.Key(e.key()), "")
        text = "" if keysym or e.text() < " " else e.text()
        self._app.ctx.key(text, keysym or text, self._mods(e))
        self._refresh()

    def focusOutEvent(self, e) -> None:  # noqa: N802
        self.close()  # a launcher closes when it loses focus, as Kando does
