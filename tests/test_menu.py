from unittest import mock

import pytest

from builauncher.apps import read_entry
from builauncher.config import DEFAULT, load
from builauncher.fuzzy import search
from builauncher.launcher import Launcher
from builauncher.menu import Action, actions, parse
from builauncher.places import places
from builauncher.shortcut_windows import parse as parse_shortcut


def test_default_config_loads():
    cfg = load(DEFAULT)
    paths = {f"{p}:{a.name}" for p, a in actions(cfg.menu)}
    assert ":Terminal" in paths
    assert "System / Power:Reboot" in paths


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
        launcher = Launcher(load(DEFAULT).menu, [], lambda: closed.append(1))
        rows = lambda: (launcher.app.render_raster(*launcher.size), [t for t, _ in launcher.app.ctx.menu_rows(-1)])[1]
        launcher.reset()
        rows()
        assert not launcher.flick(5, 0)  # too short
        assert rows()[:2] == ["Search", "Terminal"] and not launcher.searching
        assert launcher.flick(100, -100) and rows()[1:] == ["Lock", "Suspend", "Power"]  # NE: System
        launcher.click_empty(*launcher._center)
        assert rows()[0] == "Search" and not closed
        launcher.click_empty(*launcher._center)
        assert closed
        launcher.reset()
        rows()
        launcher.flick(100, 0)  # E: Terminal
        assert ran == ["konsole"]
        launcher.reset()
        rows()
        launcher.flick(-100, 0)  # W: Search
        assert launcher.searching and not launcher.app.ctx.popup_count()


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
