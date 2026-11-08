from unittest import mock

import pytest

from builauncher.items.apps import read_entry
from builauncher.config import DEFAULT, load

LINUX = DEFAULT.with_name("default.toml")  # DEFAULT is the Windows menu on Windows
from builauncher.fuzzy import search
from builauncher.launcher import Launcher
from builauncher.items.menu import Action, actions, parse
from builauncher.items.places import places
from builauncher.shortcut_windows import parse as parse_shortcut


def test_default_config_loads():
    cfg = load(LINUX)
    paths = {f"{p}:{a.name}" for p, a in actions(cfg.menu)}
    assert ":Terminal" in paths
    assert "System / Power:Reboot" in paths
    assert cfg.dwell == 0.3


def test_dwell_config(tmp_path):
    f = tmp_path / "menu.toml"
    f.write_text('[[item]]\nname = "t"\nexec = "t"\n')
    assert load(f).dwell == 0.3  # no dwell in the file: the default
    f.write_text('dwell = 0.5\n[[item]]\nname = "t"\nexec = "t"\n')  # a root key: before [[item]]
    assert load(f).dwell == 0.5
    for bad in ("0.04", "2.1", "-1"):
        f.write_text(f'dwell = {bad}\n[[item]]\nname = "t"\nexec = "t"\n')
        with pytest.raises(ValueError):
            load(f)


PIES = {"m": [{"name": "a", "exec": "a"}], "loop": [{"name": "l", "pie": "loop"}],
        "full": [{"name": str(i), "exec": "x"} for i in range(8)]}


@pytest.mark.parametrize("raw", [{"name": "x"}, {"exec": "a"}, {"name": "x", "exec": "a", "pie": "m"},
                                 {"name": "x", "pie": "nope"}, {"name": "x", "pie": "loop"},
                                 {"name": "x", "pie": "full"}])  # full: no slot left for Back
def test_bad_items_rejected(raw):
    with pytest.raises(ValueError):
        parse(raw, PIES)


def test_fuzzy_search():
    assert search("zz", ["abc"], str) == []
    assert search("firfox", ["Firefox", "Files"], str)[0] == "Firefox"
    names = ["Shut down", "Suspend", "System Settings"]
    assert search("sd", names, str)[0] == "Shut down"
    assert search("sus", names, str)[0] == "Suspend"


def test_action_parse():
    assert parse({"name": "t", "exec": "konsole"}, {}) == Action("t", "konsole")
    assert parse({"name": "s", "pie": "m"}, PIES).items == (Action("a", "a"),)


def test_desktop_entry(tmp_path):
    f = tmp_path / "a.desktop"
    f.write_text("[Desktop Entry]\nType=Application\nName=Foo\nExec=foo --x %U\nIcon=foo\n")
    assert read_entry(f) == Action("Foo", "foo --x", "foo")
    f.write_text("[Desktop Entry]\nType=Application\nName=Foo\nExec=foo\nNoDisplay=true\n")
    assert read_entry(f) is None


def test_flick_and_back():
    closed, ran = [], []
    with mock.patch("builauncher.launcher.run", ran.append):
        launcher = Launcher(load(LINUX).menu, [], lambda: closed.append(1))
        rows = lambda: (launcher.app.render_raster(*launcher.size), [t for t, _ in launcher.app.ctx.menu_rows(-1)])[1]
        launcher.reset()
        rows()
        c = launcher._center
        assert not launcher.flick(c, (c[0] + 5, c[1]))  # too short
        assert rows()[:2] == ["Search", "Terminal"] and not launcher.searching
        assert launcher.flick(c, (c[0] + 100, c[1] - 100)) and rows()[1:] == ["Lock", "Suspend", "Power"]  # NE
        launcher.click_empty(*c)
        assert rows()[0] == "Search" and not closed
        launcher.click_empty(*c)
        assert closed
        launcher.reset()
        rows()
        launcher.flick(c, (c[0] + 100, c[1]))  # E: Terminal
        assert ran == ["konsole"]
        launcher.reset()
        rows()
        launcher.flick(c, (c[0] - 100, c[1]))  # W: Search
        assert launcher.searching and not launcher.app.ctx.popup_count()


def test_flick_picks_the_highlighted_item():
    closed, ran = [], []
    with mock.patch("builauncher.launcher.run", ran.append):
        launcher = Launcher(load(LINUX).menu, [], lambda: closed.append(1))
        rows = lambda: (launcher.app.render_raster(*launcher.size), [t for t, _ in launcher.app.ctx.menu_rows(-1)])[1]
        launcher.reset()
        c = launcher._center
        launcher.flick(c, (c[0] + 100, c[1] - 100))  # NE: the System sub-pie
        suspend = next(a for a in load(LINUX).menu.items[4].items if a.name == "Suspend")
        # the stroke points at Lock (E), but the pointer rests on Suspend's rect (SW): Suspend is lit
        assert launcher.flick((100, 240), (200, 280))
        assert ran == [suspend.exec] and not launcher.app.ctx.popup_count()
        launcher.reset()
        launcher.flick(c, (c[0] + 100, c[1] - 100))
        del ran[:]
        # a twitch of a stroke on the lit item still picks it: the pointer decides, not the stroke
        assert launcher.flick((200, 280), (200, 280))
        assert ran == [suspend.exec]


def test_drag_pick():
    closed, ran = [], []
    with mock.patch("builauncher.launcher.run", ran.append):
        launcher = Launcher(load(LINUX).menu, [], lambda: closed.append(1))
        rows = lambda: (launcher.app.render_raster(*launcher.size), [t for t, _ in launcher.app.ctx.menu_rows(-1)])[1]
        launcher.reset()
        launcher.app.render_raster(*launcher.size)
        centre = lambda t: next((x + w // 2, y + h // 2) for s, (x, y, w, h) in
                                launcher.app.ctx.menu_rows(-1) if s == t)
        assert not launcher.drag_pick(*launcher._center)  # the centre is no item
        assert not launcher.drag_pick(*centre("Search"))  # Search must not open from a drag
        assert not launcher.drag_pick(*centre("Terminal"))  # an Action must not run from a drag
        assert launcher.drag_pick(*centre("System"))  # a sub-pie may open from a drag
        assert rows() == ["Search", "Terminal", "Browser", "Files", "Media", "System"]  # but only a dwell does
        launcher.drag_pick(*centre("System"))()
        assert rows() == ["Back", "Lock", "Suspend", "Power"]
        launcher.drag_pick(*centre("Back"))()
        assert rows()[0] == "Search"
        launcher.search_only()
        assert not launcher.drag_pick(*launcher._center)  # no pie in search mode: nothing to pick
        assert not ran and not closed  # a drag pick never runs an Action nor closes


def test_places_fit_a_sub_pie():
    found = places()
    assert found[-1].name == "Trash" and len(found) <= 7  # one slot for Back
    assert parse({"name": "Files", "pie": "places"}, {"places": found}).items == found


def test_windows_default_and_shortcut():
    paths = {f"{p}:{a.name}" for p, a in actions(load(DEFAULT.with_name("default-windows.toml")).menu)}
    assert "System / Power:Restart" in paths
    assert parse_shortcut("CTRL+ALT+space") == (0x3, 0x20)
    assert parse_shortcut("LOGO+F12") == (0x8, 0x7B)
    for bad in ("HYPER+a", "CTRL+nope"):
        with pytest.raises(ValueError):
            parse_shortcut(bad)
