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


# -- key strokes for Keyboard Mode (spec 004 D10) ----------------------------------------------

from gescrtl.platform.win_input import (  # noqa: E402
    KEYEVENTF_UNICODE,
    build_stroke,
)


def desc(inputs):
    return [
        (
            i.ki.wVk,
            i.ki.wScan,
            bool(i.ki.dwFlags & KEYEVENTF_KEYUP),
            bool(i.ki.dwFlags & KEYEVENTF_UNICODE),
        )
        for i in inputs
    ]


def test_plain_characters_are_sent_as_unicode_down_and_up():
    inputs, vks = build_stroke("a")
    assert vks == [] and desc(inputs) == [(0, ord("a"), False, True), (0, ord("a"), True, True)]
    inputs, _ = build_stroke("é")
    assert desc(inputs)[0][1] == ord("é")
    inputs, _ = build_stroke("A")
    assert desc(inputs)[0][1] == ord("A")


def test_a_character_outside_the_basic_plane_is_two_utf16_units():
    inputs, _ = build_stroke("😀")
    assert len(inputs) == 4


def test_named_keys_use_virtual_keys():
    for name, vk in (
        ("enter", 0x0D),
        ("backspace", 0x08),
        ("tab", 0x09),
        ("space", 0x20),
        ("left", 0x25),
        ("down", 0x28),
        ("esc", 0x1B),
    ):
        inputs, vks = build_stroke(name)
        assert vks == [vk] and [d[0] for d in desc(inputs)] == [vk, vk]


def test_shift_with_an_arrow_is_a_chord():
    inputs, vks = build_stroke("right", frozenset({"shift"}))
    assert vks == [0x10, 0x27]
    assert [(d[0], d[2]) for d in desc(inputs)] == [
        (0x10, False),
        (0x27, False),
        (0x27, True),
        (0x10, True),
    ]


def test_ctrl_c_uses_the_virtual_key_of_the_active_layout():
    inputs, vks = build_stroke("c", frozenset({"ctrl"}), scan=lambda ch: ord(ch.upper()))
    assert vks == [0x11, 0x43]
    assert [d[0] for d in desc(inputs)] == [0x11, 0x43, 0x43, 0x11]


def test_a_shifted_layout_character_adds_shift_to_a_chord():
    inputs, vks = build_stroke("?", frozenset({"ctrl"}), scan=lambda ch: 0x0100 | 0xBF)
    assert vks == [0x11, 0x10, 0xBF]


def test_an_unmappable_character_or_name_is_not_sent():
    assert build_stroke("é", frozenset({"alt"}), scan=lambda ch: -1) is None
    assert build_stroke("nonsense") is None


def test_key_stroke_marks_a_chord_before_sending_and_clears_it_after(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(win_input, "_send", rec)
    backend = WinInput()
    assert backend.key_stroke("right", frozenset({"shift"})) is True
    assert backend._keys_down == []
    rec.ok = False
    backend.key_stroke("right", frozenset({"shift"}))
    assert backend._keys_down == [0x10, 0x27]  # a failed send is released later
    rec.ok = True
    rec.sent.clear()
    backend.release_all()
    assert rec.sent and all(up for _, up in rec.sent[0])


def test_shortcut_actions_send_their_chords(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(win_input, "_send", rec)
    backend = WinInput()
    expected = {
        Action.COPY: [0x11, 0x43],
        Action.PASTE: [0x11, 0x56],
        Action.CUT: [0x11, 0x58],
        Action.UNDO: [0x11, 0x5A],
        Action.REDO: [0x11, 0x59],
        Action.SELECT_ALL: [0x11, 0x41],
        Action.WIN: [0x5B],
        Action.ESC: [0x1B],
    }
    for action, chord in expected.items():
        assert backend.system_action(action) is True
        assert [k for k, up in rec.sent[-1] if not up] == chord, action


def test_desktop_mode_maps_over_the_virtual_rectangle(monkeypatch):
    sent = []
    monkeypatch.setattr(WinInput, "move_px", lambda self, px, py: sent.append((px, py)))
    monkeypatch.setattr(WinInput, "primary_rect", lambda self: (0, 0, 1920, 1080))
    monkeypatch.setattr(WinInput, "_virtual_rect", staticmethod(lambda: (-1920, 0, 3840, 1080)))
    backend = WinInput()
    backend.move(0.0, 0.0)
    assert sent[-1] == (0, 0)
    backend.desktop_mode = True
    backend.move(0.0, 0.0)
    backend.move(1.0, 1.0)
    assert sent[-2:] == [(-1920, 0), (-1920 + 3839, 1079)]
