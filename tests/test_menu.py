import pytest

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
