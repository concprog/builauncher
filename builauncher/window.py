"""Frameless, translucent Qt window that shows a BUI context under the pointer.

On Wayland no app may place its window or ask for the pointer, so the window covers the
screen (a layer surface if Qt has the layer-shell plugin, else a full-screen window) and
draws the menu where the pointer enters it. On X11 and Windows it moves to the pointer.

BUI draws into an opaque raster over the region background. This window
makes that background clear again, with no change to BUI:
  - pixels inside widget rects (search row, results, pie items) stay opaque;
  - elsewhere a pixel is the background, maybe under a black shadow, so a grey
    pixel at or below the background gets alpha 1 - v / background.
"""
import ctypes
import math
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import buipy
import numpy as np
from PySide6.QtCore import QLibraryInfo, QObject, QPointF, QRect, Qt, QTimer
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
DRAG_PX = 15  # px of drag before a release picks instead of clicks
DWELL_MOVE_PX = 4  # px of pointer travel that restarts a dwell wait: only stillness counts
FADE_IN_S, FADE_OUT_S = 0.15, 0.1  # fade durations; also between pie and search
ENTER_WAIT_MS = 150  # Wayland: no pointer enter by then (pointer not over the screen), centre it
# LayerShellQt::Window: all four anchors (full screen), overlay layer, exclusive keyboard
LAYER_SHELL = "libLayerShellQtInterface.so.6"
LAYER_GET = "_ZN12LayerShellQt6Window3getEP7QWindow"
LAYER = {"anchors": 15, "layer": 3, "keyboardInteractivity": 1, "exclusionZone": -1}


def background() -> int:
    """The region background grey (0..255). The matting needs a grey."""
    r, g, b, _ = buipy.kit_theme_color("region_bg")
    assert abs(r - g) < 1e-3 and abs(g - b) < 1e-3, "region background is not grey"
    return round(r * 255)


def layer_shell() -> bool:
    """True if this Qt has the layer-shell plugin. A distro's plugin does not load in PyPI's Qt."""
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    return (plugins / "wayland-shell-integration" / "liblayer-shell.so").exists()


def layer_surface(widget: QWidget) -> None:
    """Make a Wayland window a full-screen overlay layer surface. Call before show()."""
    get = getattr(ctypes.CDLL(LAYER_SHELL), LAYER_GET)
    get.restype, get.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
    widget.winId()  # create the QWindow
    surface = wrapInstance(get(getCppPointer(widget.windowHandle())[0]), QObject)
    for name, value in LAYER.items():
        assert surface.setProperty(name, value), name


def matte(bgrx: bytes, w: int, h: int, opaque: Iterable[Rect], bg: int) -> np.ndarray:
    """Premultiplied BGRA from BUI's opaque BGRX raster."""
    px = np.frombuffer(bgrx, np.uint8).reshape(h, w, 4).copy()
    b, g, r = px[..., 0], px[..., 1], px[..., 2]  # views: the mask needs no channel copies
    shadow = (b == g) & (g == r) & (r <= bg)
    for x, y, rw, rh in opaque:
        shadow[max(y, 0):y + rh, max(x, 0):x + rw] = False
    # r * 255 overflows a byte where the pointer is not: uint16 holds it, where() discards it.
    # Alpha comes from the original pixels: the word store below zeroes r's bytes, so it goes first
    alpha = np.where(shadow, 255 - r.astype(np.uint16) * 255 // bg, 255)
    # one word per pixel zeroes rgb and alpha together; a masked store on the rgb view is 30x slower
    px.reshape(h, w, 4).view(np.uint32)[..., 0][shadow] = 0  # black shadow, premultiplied
    px[..., 3] = alpha
    return px


class Overlay(QWidget):
    """The launcher's window. Gestures:
      - a trigger opens it; the same trigger again closes it, a quick second one shows search only;
      - trigger key held, pointer moved, key released: picks the item in that direction;
      - mouse pressed, dragged, released: the same (marking mode);
      - in either stroke, waiting on a submenu or Back opens it, the stroke continuing there;
      - click on no widget: the pie centre goes back, elsewhere closes; Escape closes.
    """

    def __init__(self, launcher: Launcher, daemon: bool, dwell: float) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._launcher, self._daemon, self._bg = launcher, daemon, background()
        self._image: tuple[np.ndarray, QImage] | None = None
        self._dpr = self.devicePixelRatioF()
        self._wayland = QGuiApplication.platformName() == "wayland"
        self._layer = self._wayland and layer_shell()
        # top left of the menu in the window, in logical pixels. None: the pointer has not entered yet
        self._origin: QPointF | None = QPointF(0, 0)
        self._enter_wait = QTimer(self, singleShot=True, interval=ENTER_WAIT_MS,
                                  timeout=lambda: self._put(self.rect().center().toPointF()))
        if not self._wayland:
            w, h = launcher.size
            self.resize(round(w / self._dpr), round(h / self._dpr))
        # BUI timers, animations and focus changes: redraw when the context asks
        self._tick = QTimer(self, interval=FRAME_MS, timeout=self._refresh)
        self._shown_at = 0.0
        self._keys: set[int] = set()  # keys pressed while shown; a release of another is the trigger
        self._stroke: tuple[tuple[int, int], tuple[int, int]] | None = None  # first and last pointer
        self._pressed_at: tuple[int, int] | None = None
        self._holding = False  # the trigger key is down: a stroke of motion, no button
        self._picked = False  # the stroke's last act was a dwell pick: a release then keeps the new pie
        self._dwell_at: tuple[int, int] | None = None  # the pointer in the drag, for the dwell pick
        self._dwell_cb: Callable[[], None] | None = None  # the pick the dwell wait is for
        self._dwell = QTimer(self, singleShot=True, interval=round(dwell * 1000), timeout=self._dwell_pick)
        self._fade_at, self._fading_out, self._searching = 0.0, False, False
        if self._layer:
            layer_surface(self)

    def trigger(self) -> None:
        """The global shortcut fired (pressed: a stroke of motion starts, no button)."""
        self._holding = True
        if not self.isVisible() or self._fading_out:
            return self.summon()
        if time.monotonic() - self._shown_at < DOUBLE_S:
            return self._launcher.search_only()
        self.dismiss()

    def summon(self) -> None:
        self._shown_at, self._keys, self._stroke, self._pressed_at = time.monotonic(), set(), None, None
        self._picked, self._dwell_cb, self._dwell_at = False, None, None
        self._dwell.stop()  # a drag's dwell wait does not survive a reopen
        self._fade_at, self._fading_out = self._shown_at, False
        self._launcher.reset()
        self._place()
        self.showFullScreen() if self._wayland and not self._layer else self.show()
        self.activateWindow()

    def dismiss(self) -> None:
        """Fade out, then hide."""
        if self.isVisible() and not self._fading_out:
            self._dwell.stop()  # a wait may not open a pie in a closing window
            self._dwell_cb = None
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

    def _put(self, pointer: QPointF) -> None:
        """Wayland: centre the menu on pointer, kept inside the window."""
        if self._origin is None:
            w, h = (v / self._dpr for v in self._launcher.size)
            self._origin = QPointF(min(max(pointer.x() - w / 2, 0), max(self.width() - w, 0)),
                                   min(max(pointer.y() - h / 2, 0), max(self.height() - h, 0)))
            self._enter_wait.stop()
            self.update()

    def _place(self) -> None:
        """At the pointer on X11 and Windows. On Wayland, where the pointer enters the window."""
        if self._wayland:
            self._origin = None
            return self._enter_wait.start()
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
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        if self._origin is not None:
            painter.drawImage(self._origin, image)
        painter.end()

    def enterEvent(self, e) -> None:  # noqa: N802
        self._put(e.position())

    def _at(self, e: QMouseEvent) -> tuple[int, int]:
        self._put(e.position())  # a motion with no enter before it
        p = (e.position() - self._origin) * self._dpr
        w, h = self._launcher.size
        # the pointer may leave BUI's raster (the menu is a small region of the overlay), but BUI
        # drops motions beyond its window and would light nothing while a stroke is out there
        return round(min(max(p.x(), 0), w - 1)), round(min(max(p.y(), 0), h - 1))

    def _mods(self, e) -> int:
        held = sum(bit for mod, bit in MODS if e.modifiers() & mod)
        left = isinstance(e, QMouseEvent) and bool(e.buttons() & Qt.MouseButton.LeftButton)
        return held | (8 if left else 0)

    def _on_widget(self, x: int, y: int) -> bool:
        return any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in self._launcher.opaque())

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
        picked, self._picked = self._picked, False
        self._dwell.stop()
        self._dwell_cb = None
        if start is None:
            self._launcher.app.ctx.release(*at, self._mods(e))
        elif math.dist(at, start) > DRAG_PX:
            self._launcher.flick(start, at)
        elif not picked:  # a dwell pick just opened a pie here: keep it
            self._launcher.click_empty(*start)
        self._refresh()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        at = self._at(e)
        self._stroke = (self._stroke[0] if self._stroke else at, at)
        self._launcher.app.ctx.motion(*at, self._mods(e))
        self._drag(at)
        self._refresh()

    @property
    def _stroking(self) -> bool:
        """A stroke is live: a button drag from empty space, or a held trigger's motion."""
        return self._pressed_at is not None or self._holding

    def _drag(self, at: tuple[int, int]) -> None:
        """In a stroke: waiting still on a submenu or Back readies its pick."""
        pick = self._launcher.drag_pick(*at) if self._stroking else None
        # travel since the wait's anchor (not per event: a slow drift must not fire mid-move)
        moved = self._dwell_at is not None and math.dist(at, self._dwell_at) > DWELL_MOVE_PX
        if pick is not self._dwell_cb or moved:  # a new item, or real travel: (re)start the wait
            self._dwell_cb = pick
            self._dwell_at = at  # the anchor: travel is measured from here until the next reset
            (self._dwell.stop if pick is None else self._dwell.start)()

    def _dwell_pick(self) -> None:
        """A stroke waited still on a submenu or Back: make the pick once its highlight is drawn."""
        pick, self._dwell_cb = self._dwell_cb, None
        if pick is None or not self._stroking or pick is not self._launcher.drag_pick(*self._dwell_at):
            return  # the pointer left, or the menu changed under it
        self._launcher.app.ctx.motion(*self._dwell_at, 0)  # BUI tracks the pointer: re-light the item
        self._launcher.app.render_raster(*self._launcher.size)  # and draw it before the pick lands
        if pick is not self._launcher.drag_pick(*self._dwell_at):
            return  # the freshly lit item is not the one we waited on
        pick()
        if self._pressed_at is not None:  # a button stroke restarts at the pick; a trigger's has no press
            self._pressed_at = self._dwell_at
        self._stroke, self._picked = None, True

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
        self._holding = False
        if self.isVisible() and self._stroke and time.monotonic() - self._shown_at >= HOLD_S:
            self._launcher.flick(*self._stroke)
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
        self.dismiss()  # hide on focus loss
