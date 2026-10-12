"""Keyboard actions of WinInput: the INPUT sequences are built and checked without sending."""

from gescrtl.core.types import Action
from gescrtl.platform import win_input
from gescrtl.platform.win_input import KEYEVENTF_KEYUP, WinInput, build_key_inputs

VK_MENU, VK_TAB, VK_LWIN, VK_SNAPSHOT = 0x12, 0x09, 0x5B, 0x2C
VK_LEFT, VK_RIGHT = 0x25, 0x27


def seq(vks):
    return [(i.ki.wVk, bool(i.ki.dwFlags & KEYEVENTF_KEYUP)) for i in build_key_inputs(vks)]


def test_alt_tab_presses_in_order_and_releases_in_reverse():
    assert seq([VK_MENU, VK_TAB]) == [
        (VK_MENU, False),
        (VK_TAB, False),
        (VK_TAB, True),
        (VK_MENU, True),
    ]


def test_single_key_is_a_down_and_an_up():
    assert seq([0xB3]) == [(0xB3, False), (0xB3, True)]


def test_arrow_keys_are_sent_as_extended_keys():
    down = build_key_inputs([VK_RIGHT])[0]
    assert down.ki.dwFlags & win_input.KEYEVENTF_EXTENDEDKEY


class Recorder:
    def __init__(self, ok=True):
        self.sent = []
        self.ok = ok

    def __call__(self, *inputs):
        self.sent.append([(i.ki.wVk, bool(i.ki.dwFlags & KEYEVENTF_KEYUP)) for i in inputs])
        return self.ok


def test_media_and_system_actions_send_the_expected_keys(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(win_input, "_send", rec)
    backend = WinInput()
    expected = {
        Action.PLAY_PAUSE: 0xB3,
        Action.NEXT_TRACK: 0xB0,
        Action.PREV_TRACK: 0xB1,
        Action.MUTE: 0xAD,
    }
    for action, vk in expected.items():
        assert backend.system_action(action) is True
        assert rec.sent[-1] == [(vk, False), (vk, True)]
    assert backend.system_action(Action.SCREENSHOT) is True
    assert [k for k, up in rec.sent[-1] if not up] == [VK_LWIN, VK_SNAPSHOT]
    assert backend.system_action(Action.APP_SWITCH) is True
    assert [k for k, up in rec.sent[-1] if not up] == [VK_MENU, VK_TAB]


def test_slides_default_to_right_and_left_and_start_end_are_unsupported(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(win_input, "_send", rec)
    backend = WinInput()
    assert backend.system_action(Action.SLIDE_NEXT) is True
    assert rec.sent[-1][0] == (VK_RIGHT, False)
    assert backend.system_action(Action.SLIDE_PREV) is True
    assert rec.sent[-1][0] == (VK_LEFT, False)
    n = len(rec.sent)
    assert backend.system_action(Action.SHOW_START) is False
    assert backend.system_action(Action.SHOW_END) is False
    assert len(rec.sent) == n  # nothing was sent


def test_a_custom_key_table_decides_what_is_supported(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(win_input, "_send", rec)
    table = {Action.SHOW_START: [0x10, 0x74]}
    backend = WinInput(keys_for=lambda a: table.get(a))
    assert backend.system_action(Action.SHOW_START) is True
    assert backend.system_action(Action.SHOW_END) is False


def test_a_failed_send_leaves_the_keys_to_release_all(monkeypatch):
    rec = Recorder(ok=False)
    monkeypatch.setattr(win_input, "_send", rec)
    backend = WinInput()
    backend.system_action(Action.APP_SWITCH)
    rec.ok = True
    backend.release_all()
    released = [k for batch in rec.sent[1:] for k, up in batch if up]
    assert set(released) == {VK_MENU, VK_TAB}
    n = len(rec.sent)
    backend.release_all()  # idempotent
    assert len(rec.sent) == n
