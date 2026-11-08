from unittest import mock

import pytest

from builauncher.apps import read_entry
from builauncher.config import DEFAULT, load
from builauncher.fuzzy import score, search
from builauncher.launcher import Launcher
from builauncher.menu import Action, actions, parse
from builauncher.places import places


def test_default_config_loads():
    cfg = load(DEFAULT)
    paths = {f"{p}:{a.name}" for p, a in actions(cfg.menu)}
    assert ":Terminal" in paths
    assert "System / Power:Reboot" in paths


@pytest.mark.parametrize("raw", [{"name": "x"}, {"exec": "a"}, {"name": "x", "exec": "a", "item": [{}]}])
def test_bad_items_rejected(raw):
    with pytest.raises(ValueError):
        parse(raw)


def test_fuzzy_prefers_word_starts():
    assert score("zz", "abc") is None
    assert score("ff", "firefox") is not None
    names = ["Shut down", "Suspend", "System Settings"]
    assert search("sd", names, str)[0] == "Shut down"
    assert search("sus", names, str)[0] == "Suspend"


def test_action_parse():
    assert parse({"name": "t", "exec": "konsole"}) == Action("t", "konsole")


def test_desktop_entry(tmp_path):
    f = tmp_path / "a.desktop"
    f.write_text("[Desktop Entry]\nType=Application\nName=Foo\nExec=foo --x %U\nIcon=foo\n")
    assert read_entry(f) == Action("Foo", "foo --x", "foo")
    f.write_text("[Desktop Entry]\nType=Application\nName=Foo\nExec=foo\nNoDisplay=true\n")
    assert read_entry(f) is None


def test_submenu_fits_pie():
    with pytest.raises(ValueError):
        parse({"name": "m", "item": [{"name": str(i), "exec": "x"} for i in range(9)]})


def test_flick_and_back():
    closed, ran = [], []
    with mock.patch("builauncher.launcher.run", ran.append):
        launcher = Launcher(load(DEFAULT).menu, [], lambda: closed.append(1))
        rows = lambda: (launcher.app.render_raster(*launcher.size), [t for t, _ in launcher.app.ctx.menu_rows(-1)])[1]
        launcher.reset()
        rows()
        assert not launcher.flick(5, 0)  # too short
        assert launcher.flick(-100, -100) and rows()[1:] == ["Lock", "Suspend", "Power"]
        launcher.click_empty(*launcher._center)
        assert rows()[0] == "Terminal" and not closed
        launcher.click_empty(*launcher._center)
        assert closed
        launcher.reset()
        rows()
        launcher.flick(-100, 0)
        assert ran == ["konsole"]


def test_places_fit_a_sub_pie():
    found = places()
    assert found[-1].name == "Trash" and len(found) <= 7  # one slot for Back
    files = parse({"name": "Files", "places": True}, found)
    assert files.items == found
    with pytest.raises(ValueError):
        parse({"name": "Files", "places": True, "exec": "x"}, found)
