"""Foreground-app dependent slide-show keys (plan D10)."""

from gescrtl.core.types import Action
from gescrtl.platform import presenter_keys as pk


def test_slides_use_arrow_keys_in_every_application():
    for exe, title in (
        ("powerpnt.exe", "x"),
        ("msedge.exe", "a.pdf"),
        ("", ""),
        ("notepad.exe", ""),
    ):
        assert pk.keys_for_app(Action.SLIDE_NEXT, exe, title) == [pk.VK_RIGHT]
        assert pk.keys_for_app(Action.SLIDE_PREV, exe, title) == [pk.VK_LEFT]


def test_powerpoint_starts_from_the_current_slide_and_ends_with_escape():
    assert pk.keys_for_app(Action.SHOW_START, "POWERPNT.EXE", "Deck") == [pk.VK_SHIFT, pk.VK_F5]
    assert pk.keys_for_app(Action.SHOW_END, "POWERPNT.EXE", "Deck") == [pk.VK_ESCAPE]


def test_google_slides_in_a_browser_uses_ctrl_shift_f5():
    for exe in ("msedge.exe", "chrome.exe"):
        title = "My talk - Google Slides"
        assert pk.keys_for_app(Action.SHOW_START, exe, title) == [
            pk.VK_CONTROL,
            pk.VK_SHIFT,
            pk.VK_F5,
        ]
        assert pk.keys_for_app(Action.SHOW_END, exe, title) == [pk.VK_ESCAPE]


def test_start_and_end_are_unsupported_elsewhere():
    for exe, title in (("msedge.exe", "paper.pdf"), ("notepad.exe", "Google Slides"), ("", "")):
        for action in (Action.SHOW_START, Action.SHOW_END):
            assert pk.keys_for_app(action, exe, title) is None


def test_make_keys_for_asks_the_lookup_each_time():
    seen = [("powerpnt.exe", "d"), ("notepad.exe", "n")]
    keys_for = pk.make_keys_for(lambda: seen.pop(0))
    assert keys_for(Action.SHOW_START) == [pk.VK_SHIFT, pk.VK_F5]
    assert keys_for(Action.SHOW_START) is None


def test_the_live_foreground_lookup_returns_strings():
    exe, title = pk.foreground_window()
    assert isinstance(exe, str) and isinstance(title, str)
