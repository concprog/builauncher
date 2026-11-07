import pytest

from buiemenu.apps import read_entry
from buiemenu.config import DEFAULT, load
from buiemenu.fuzzy import score, search
from buiemenu.menu import Action, actions, parse


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
