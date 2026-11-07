from buiemenu.config import DEFAULT, load
from buiemenu.gesture import Gesture
from buiemenu.menu import Action
from buiemenu.pie import BACK, Pie, angle_of, slot_angles


def test_angles():
    assert angle_of((0, 0), (0, -1)) == 0
    assert round(angle_of((0, 0), (1, 0))) == 90
    assert slot_angles(4, None) == [0, 90, 180, 270]
    assert slot_angles(3, 180) == [270, 0, 90]


def test_gesture_corner_and_pause():
    g = Gesture()
    assert g.motion((0, 0), 0) is None
    assert g.motion((150, 0), 0.01) is None
    assert g.motion((150, 100), 0.02) == (150, 0)  # sharp turn
    g.reset()
    g.motion((0, 0), 0)
    g.motion((150, 0), 0.01)
    g.motion((155, 0), 0.02)
    assert g.poll((155, 0), 0.05) is None
    assert g.poll((155, 0), 0.2) == (155, 0)


def test_pie_navigation():
    pie = Pie(load(DEFAULT).menu, radius=130, dead_zone=40)
    pie.open((500, 500))
    assert pie.hit((505, 500)) is None
    assert pie.select((500, 300), at_pointer=False) == Action("Terminal", "konsole", "utilities-terminal")
    # System is the 5th of 5 items: at 288 degrees
    system = pie.angles()[4]
    pie.select((300, 450), at_pointer=False)
    assert pie.level.menu.name == "System"
    assert pie.level.back == (system + 180) % 360
    c = pie.level.center
    assert pie.hit((c[0] + 100, c[1] + 30)) == BACK
    pie.select((c[0] + 100, c[1] + 30), at_pointer=True)
    assert pie.level.menu.name == "root"
