"""Marking-mode gesture detector, after Kando's GestureDetector.

A stroke S->E that is long enough selects at E when the pointer turns
sharply (E->M against S->E) or stays still for PAUSE seconds.
"""
from dataclasses import dataclass
from math import acos, degrees, dist

MIN_STROKE = 100.0
MIN_ANGLE = 20.0
JITTER = 10.0
PAUSE = 0.1

Point = tuple[float, float]


@dataclass(slots=True)
class Gesture:
    start: Point | None = None
    end: Point | None = None
    still_since: float | None = None

    def reset(self, corner: Point | None = None) -> None:
        self.start, self.end, self.still_since = corner, corner, None

    def motion(self, p: Point, now: float) -> Point | None:
        """Feed a pointer position. Return the corner point on a selection."""
        if self.start is None or self.end is None:
            self.reset(p)
            return None
        length = dist(self.start, self.end)
        if length <= MIN_STROKE:
            self.end = p
            return None
        tip = dist(self.end, p)
        if tip > JITTER:
            sx, sy = self.end[0] - self.start[0], self.end[1] - self.start[1]
            tx, ty = p[0] - self.end[0], p[1] - self.end[1]
            cos = max(-1.0, min(1.0, (sx * tx + sy * ty) / (length * tip)))
            if degrees(acos(cos)) > MIN_ANGLE:
                corner = self.end
                self.reset(corner)
                return corner
            self.end, self.still_since = p, None
        self.still_since = self.still_since or now
        return None

    def poll(self, p: Point, now: float) -> Point | None:
        """Call on a timer. Return the pointer point if it paused on a long stroke."""
        if self.still_since is not None and now - self.still_since >= PAUSE:
            self.reset(p)
            return p
        return None
