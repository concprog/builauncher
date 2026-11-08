"""Frameless, translucent Qt window that shows a BUI context.

BUI draws into an opaque raster over the region background. This window
makes that background clear again, with no change to BUI:
  - pixels inside widget rects (search row, results, pie items) stay opaque;
  - elsewhere a pixel is the background, maybe under a black shadow, so a grey
    pixel at or below the background gets alpha 1 - v / background.
"""
import ctypes
import math
import time
from collections.abc import Iterable

import buipy
import numpy as np
from PySide6.QtCore import QObject, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QImage, QKeyEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget
from shiboken6 import getCppPointer, wrapInstance

from .launcher import Launcher

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
HOLD_S, DOUBLE_S = 0.2, 0.4  # hold: Blender U.pie_tap_timeout; a second trigger sooner is a double tap
DRAG_PX = 15  # Kando's drag threshold
FADE_IN_S, FADE_OUT_S = 0.15, 0.1  # Kando's fade durations; also between pie and search
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
    """The launcher's window. Gestures, as Kando's:
      - a trigger opens it; the same trigger again closes it, a quick second one shows search only;
      - trigger key held, pointer moved, key released: picks the item in that direction;
      - mouse pressed, dragged, released: the same (marking mode);
      - click on no widget: the pie centre goes back, elsewhere closes; Escape closes.
    """

    def __init__(self, launcher: Launcher, daemon: bool) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._launcher, self._daemon, self._bg = launcher, daemon, background()
        self._image: tuple[np.ndarray, QImage] | None = None
        self._dpr = self.devicePixelRatioF()
        w, h = launcher.size
        self.resize(round(w / self._dpr), round(h / self._dpr))
        # BUI timers, animations and focus changes: redraw when the context asks
        self._tick = QTimer(self, interval=FRAME_MS, timeout=self._refresh)
        self._shown_at = 0.0
        self._keys: set[int] = set()  # keys pressed while shown; a release of another is the trigger
        self._stroke: tuple[tuple[int, int], tuple[int, int]] | None = None  # first and last pointer
        self._pressed_at: tuple[int, int] | None = None
        self._fade_at, self._fading_out, self._searching = 0.0, False, False
        if QGuiApplication.platformName() == "wayland":
            layer_surface(self)

    def trigger(self) -> None:
        """The global shortcut fired."""
        if not self.isVisible() or self._fading_out:
            return self.summon()
        if time.monotonic() - self._shown_at < DOUBLE_S:
            return self._launcher.search_only()
        self.dismiss()

    def summon(self) -> None:
        self._shown_at, self._keys, self._stroke, self._pressed_at = time.monotonic(), set(), None, None
        self._fade_at, self._fading_out = self._shown_at, False
        self._launcher.reset()
        self._place()
        self.show()
        self.activateWindow()

    def dismiss(self) -> None:
        """Fade out, then hide."""
        if self.isVisible() and not self._fading_out:
            self._fade_at, self._fading_out = time.monotonic(), True
            self.update()

    def _hide(self) -> None:
        self._fading_out = False
        self.hide()
        if not self._daemon:
            QGuiApplication.quit()

    def _opacity(self) -> float:
        """0..1, eased out."""
        t = min((time.monotonic() - self._fade_at) / (FADE_OUT_S if self._fading_out else FADE_IN_S), 1.0)
        return 1 - t * t if self._fading_out else 1 - (1 - t) ** 2

    def _place(self) -> None:
        """At the pointer on X11. On Wayland, the compositor centres the layer surface."""
        if QGuiApplication.platformName() == "wayland":
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area, pos = screen.availableGeometry(), QCursor.pos()
        rect = QRect(0, 0, self.width(), self.height())
        rect.moveCenter(pos if area.contains(pos) else area.center())
        rect.moveTo(min(max(rect.x(), area.left()), area.right() - rect.width()),
                    min(max(rect.y(), area.top()), area.bottom() - rect.height()))
        self.move(rect.topLeft())

    def showEvent(self, e) -> None:  # noqa: N802
        self._tick.start()

    def hideEvent(self, e) -> None:  # noqa: N802
        self._tick.stop()  # no frames while hidden

    def _refresh(self) -> None:
        if self._fading_out and self._opacity() <= 0:
            return self._hide()
        if self._launcher.app.ctx.needs_render() or self._fading_out or self._opacity() < 1:
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        w, h = self._launcher.size
        raster = self._launcher.app.render_raster(w, h)
        px = matte(raster.rgb32(), w, h, self._launcher.opaque(), self._bg)
        if self._launcher.searching != self._searching and not self._fading_out:
            self._searching, self._fade_at = self._launcher.searching, time.monotonic()  # pie <-> search
        if (alpha := round(self._opacity() * 256)) < 256:
            px = (px.astype(np.uint16) * alpha >> 8).astype(np.uint8)  # premultiplied: scale all channels
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

    def _on_widget(self, x: int, y: int) -> bool:
        return any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in self._launcher.opaque())

    def _flick(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        return self._launcher.flick(end[0] - start[0], end[1] - start[1])

    def mousePressEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        at, ctx = self._at(e), self._launcher.app.ctx
        if e.button() == Qt.MouseButton.RightButton:
            ctx.context_menu(*at, self._mods(e))
        elif self._on_widget(*at):
            ctx.press(*at, self._mods(e))
        else:
            self._pressed_at = at  # empty space: a click there, or the start of a stroke
        self._refresh()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        at, start, self._pressed_at = self._at(e), self._pressed_at, None
        if start is None:
            self._launcher.app.ctx.release(*at, self._mods(e))
        elif math.dist(at, start) <= DRAG_PX:
            self._launcher.click_empty(*start)
        else:
            self._flick(start, at)
        self._refresh()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        at = self._at(e)
        self._stroke = (self._stroke[0] if self._stroke else at, at)
        self._launcher.app.ctx.motion(*at, self._mods(e))
        self._refresh()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        alt_f4 = e.key() == Qt.Key.Key_F4 and e.modifiers() & Qt.KeyboardModifier.AltModifier
        if e.key() == Qt.Key.Key_Escape or alt_f4:
            return self.dismiss()  # before BUI: its pie and search field take Escape for themselves
        if not e.isAutoRepeat():
            self._keys.add(e.key())
        if self._launcher.searching and e.key() == Qt.Key.Key_Backspace and not self._launcher.field.value:
            return self._launcher.reset()  # backspace on an empty search: back to the pie
        if self._launcher.searching and e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._launcher.step(1 if e.key() == Qt.Key.Key_Down else -1)
            return self._refresh()
        if e.text() >= " " and not self._launcher.searching:
            self._launcher.search_only()  # typing at any time searches
        keysym = KEYSYMS.get(Qt.Key(e.key()), "")
        text = "" if keysym or e.text() < " " else e.text()
        self._launcher.app.ctx.key(text, keysym or text, self._mods(e))
        self._refresh()

    def release(self) -> None:
        """The trigger was released. After a hold, pick towards the pointer."""
        if self.isVisible() and self._stroke and time.monotonic() - self._shown_at >= HOLD_S:
            self._flick(*self._stroke)
            self._refresh()
        self._stroke = None

    def keyReleaseEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if e.isAutoRepeat() or e.key() in self._keys:
            return self._keys.discard(e.key())
        self.release()  # a key pressed before the window showed: the trigger

    def closeEvent(self, e) -> None:  # noqa: N802
        e.ignore()
        self.dismiss()  # hide, so the daemon keeps running

    def focusOutEvent(self, e) -> None:  # noqa: N802
        self.dismiss()  # as Kando's hideOnFocusOut
