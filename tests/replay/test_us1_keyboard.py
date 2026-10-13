"""US1: Keyboard Mode types with an on-screen keyboard (spec 004 D2, FR-001..FR-009)."""

from support.hands import Script, run
from support.keyboard import (
    POINTER_EVENTS,
    Typing,
    kb_engine,
    key_cam,
    last_view,
    point_key,
    strokes,
    tap_key,
)

from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.state_machine import MODE_HINTS
from gescrtl.core.types import (
    Action,
    Command,
    HintsShown,
    KeyboardView,
    KeyStroke,
    Mode,
    OverlayHidden,
    OverlayKind,
    Pose,
    ReleaseAll,
    SystemAction,
)


def test_choosing_keyboard_shows_its_hints_and_the_keyboard():
    eng, s = kb_engine()
    ev = run(eng, point_key(s, "k:h").frames())
    assert eng.sm.mode is Mode.KEYBOARD
    assert last_view(ev).highlight == "k:h"
    entering = Engine()
    s0 = Script().hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5)).cmd(Command.SET_MODE, "KEYBOARD")
    ev = run(entering, s0.frames())
    assert HintsShown(MODE_HINTS[Mode.KEYBOARD]) in ev


def test_the_highlight_follows_the_hand_over_the_keys():
    eng, s = kb_engine()
    ev = run(eng, point_key(s, "k:q").frames())
    assert last_view(ev).highlight == "k:q"
    ev = run(eng, point_key(s.next(), "k:p").frames())
    assert last_view(ev).highlight == "k:p"


def test_a_small_hand_movement_reaches_the_corner_keys():
    eng, s = kb_engine()
    for ident in ("k:1", "s:copy", "m:shift", "k:enter", "move"):
        ev = run(eng, point_key(s.next(), ident).frames())
        assert last_view(ev).highlight == ident, ident


def test_a_pinch_presses_exactly_one_key_and_sends_no_pointer_input():
    eng, s = kb_engine()
    ev = run(eng, tap_key(s, "k:h").frames())
    assert strokes(ev) == [KeyStroke("h")]
    assert not [e for e in ev if isinstance(e, POINTER_EVENTS)]


def test_holding_the_pinch_does_not_repeat_a_letter():
    eng, s = kb_engine()
    point_key(s, "k:h")
    ev = run(eng, s.hold(Pose.G2_PINCH_INDEX, 1800).frames())
    assert strokes(ev) == [KeyStroke("h")]


def test_the_pinch_presses_the_key_that_was_pointed_before_the_pinch():
    eng, s = kb_engine()
    point_key(s, "k:h")
    # the hand slides toward the next key while the pinch forms
    s.move(Pose.G2_PINCH_INDEX, to=key_cam("k:j"), ms=120)
    s.hold(Pose.G2_PINCH_INDEX, 300).hold(Pose.G1_RELAXED, 200)
    ev = run(eng, s.frames())
    assert strokes(ev) == [KeyStroke("h")]


def test_backspace_and_arrows_repeat_while_held_after_a_delay():
    eng, s = kb_engine()
    point_key(s, "k:backspace")
    ev = run(eng, s.hold(Pose.G2_PINCH_INDEX, 1500).frames())
    n = len(strokes(ev))
    assert 6 <= n <= 14 and set(strokes(ev)) == {KeyStroke("backspace")}


def test_the_shortcut_row_sends_each_shortcut_once():
    expected = {
        "s:copy": Action.COPY,
        "s:paste": Action.PASTE,
        "s:cut": Action.CUT,
        "s:undo": Action.UNDO,
        "s:redo": Action.REDO,
        "s:select_all": Action.SELECT_ALL,
        "s:alt_tab": Action.APP_SWITCH,
        "s:win": Action.WIN,
        "s:esc": Action.ESC,
    }
    for ident, action in expected.items():
        eng, s = kb_engine()
        ev = run(eng, tap_key(s, ident).frames())
        assert [e for e in ev if isinstance(e, SystemAction)] == [SystemAction(action)], ident
        assert not strokes(ev)


def test_the_move_key_moves_the_keyboard_to_the_top_and_back():
    t = Typing()
    assert last_view(t.tap("move")).position == "top"
    assert last_view(t.tap("move", position="top")).position == "bottom"


def test_the_recent_text_strip_shows_what_was_typed():
    t = Typing()
    t.tap("k:h", "k:i")
    assert last_view(t.tap("k:space")).recent == "hi "
    assert last_view(t.tap("k:backspace")).recent == "hi"
    assert last_view(t.tap("k:enter")).recent == ""


def test_pressed_key_flashes_then_clears():
    eng, s = kb_engine()
    ev = run(eng, tap_key(s, "k:h").frames())
    views = [e for e in ev if isinstance(e, KeyboardView)]
    assert any(v.pressed == "k:h" for v in views) and views[-1].pressed == ""


def test_dwell_types_a_key_once_when_selected():
    cfg = CoreConfig(confirm_method="dwell", dwell_ms=500)
    eng, s = kb_engine(cfg)
    ev = run(eng, point_key(s, "k:g", cfg=cfg).hold(Pose.G1_RELAXED, 1500).frames())
    assert strokes(ev) == [KeyStroke("g")]
    assert any(isinstance(e, KeyboardView) and e.dwell > 0 for e in ev)


def test_nothing_is_typed_while_the_hand_only_rests_or_moves():
    eng, s = kb_engine()
    s.hold(Pose.G1_RELAXED, 2000)
    for ident in ("k:a", "k:s", "k:d", "k:f"):
        point_key(s, ident)
    assert not strokes(run(eng, s.frames()))


def test_leaving_keyboard_mode_hides_the_keyboard_and_releases():
    eng, s = kb_engine()
    run(eng, point_key(s, "k:h").frames())
    ev = run(eng, s.next().cmd(Command.SET_MODE, "POINTER").frames())
    assert OverlayHidden(OverlayKind.KEYBOARD) in ev and ReleaseAll("mode change") in ev


def test_keyboard_mode_is_deterministic():
    def go():
        eng, s = kb_engine()
        return run(eng, tap_key(s, "k:h").hold(Pose.G2_PINCH_INDEX, 100).frames())

    assert go() == go()
