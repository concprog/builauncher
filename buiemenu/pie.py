"""Pie navigation: slot angles, hit test and the submenu stack.

Angles are in degrees, 0 at the top, clockwise. A submenu keeps one slot that
points back to its parent, as in Kando.
"""
from dataclasses import dataclass, field
from math import atan2, cos, degrees, dist, radians, sin

from .gesture import Point
from .menu import Action, Item, Menu

BACK = -1


@dataclass(frozen=True, slots=True)
class Level:
    menu: Menu
    center: Point
    back: float | None  # angle of the back slot; None at the root


def angle_of(center: Point, p: Point) -> float:
    return degrees(atan2(p[0] - center[0], center[1] - p[1])) % 360


def offset(center: Point, angle: float, r: float) -> Point:
    return center[0] + r * sin(radians(angle)), center[1] - r * cos(radians(angle))


def slot_angles(count: int, back: float | None) -> list[float]:
    """Angles of the item slots. With a back slot, items fill the rest of the circle."""
    if back is None:
        return [i * 360 / count for i in range(count)]
    return [(back + (i + 1) * 360 / (count + 1)) % 360 for i in range(count)]


def nearest(angle: float, angles: list[float]) -> int:
    return min(range(len(angles)), key=lambda i: abs((angles[i] - angle + 180) % 360 - 180))


@dataclass(slots=True)
class Pie:
    root: Menu
    radius: float
    dead_zone: float
    stack: list[Level] = field(default_factory=list)

    def open(self, center: Point) -> None:
        self.stack = [Level(self.root, center, None)]

    @property
    def level(self) -> Level:
        return self.stack[-1]

    def angles(self) -> list[float]:
        return slot_angles(len(self.level.menu.items), self.level.back)

    def hit(self, p: Point) -> int | None:
        """Item index under p, BACK for the back slot, None in the dead zone."""
        lv = self.level
        if dist(lv.center, p) < self.dead_zone:
            return None
        a = angle_of(lv.center, p)
        angles = self.angles() + ([lv.back] if lv.back is not None else [])
        i = nearest(a, angles)
        return BACK if i == len(lv.menu.items) else i

    def select(self, p: Point, at_pointer: bool, submenu_only: bool = False) -> Action | None:
        """Select the slot under p. A submenu opens at p (gesture) or at its slot (click).

        submenu_only: a gesture opens submenus but does not run actions.
        """
        match self.hit(p):
            case None:
                return None
            case -1:
                if len(self.stack) > 1:
                    self.stack.pop()
                return None
            case i:
                item: Item = self.level.menu.items[i]
                if isinstance(item, Action):
                    return None if submenu_only else item
                a = self.angles()[i]
                center = p if at_pointer else offset(self.level.center, a, self.radius)
                self.stack.append(Level(item, center, (a + 180) % 360))
                return None
