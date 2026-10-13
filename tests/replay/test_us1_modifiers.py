"""US1: modifiers are one-shot or locked and are cleared by every safety transition (D2)."""

from support.keyboard import Typing, last_view, strokes

from gescrtl.core.types import Command, KeyStroke, Pose


def test_shift_is_one_shot_and_folds_into_the_character():
    t = Typing()
    assert strokes(t.tap("m:shift", "k:a", "k:a")) == [KeyStroke("A"), KeyStroke("a")]


def test_shift_changes_digits_and_punctuation():
    t = Typing()
    assert strokes(t.tap("m:shift", "k:1", "m:shift", "k:/")) == [KeyStroke("!"), KeyStroke("?")]


def test_selecting_a_modifier_twice_locks_it_and_a_third_time_clears_it():
    t = Typing()
    assert last_view(t.tap("m:shift", "m:shift")).locked == frozenset({"shift"})
    assert strokes(t.tap("k:a", "k:b")) == [KeyStroke("A"), KeyStroke("B")]
    ev = t.tap("m:shift")
    assert last_view(ev).locked == frozenset() and last_view(ev).oneshot == frozenset()
    assert strokes(t.tap("k:c")) == [KeyStroke("c")]


def test_the_state_of_a_modifier_is_always_visible():
    t = Typing()
    assert last_view(t.tap("m:ctrl")).oneshot == frozenset({"ctrl"})
    assert last_view(t.tap("k:c")).oneshot == frozenset()


def test_ctrl_c_is_sent_as_a_chord_and_clears_the_one_shot():
    t = Typing()
    ev = t.tap("m:ctrl", "k:c", "k:c")
    assert strokes(ev) == [KeyStroke("c", frozenset({"ctrl"})), KeyStroke("c")]


def test_shift_with_ctrl_keeps_both_modifiers():
    t = Typing()
    ev = t.tap("m:ctrl", "m:shift", "k:z")
    assert strokes(ev) == [KeyStroke("z", frozenset({"ctrl", "shift"}))]


def test_shift_with_an_arrow_selects_text():
    t = Typing()
    assert strokes(t.tap("m:shift", "k:right")) == [KeyStroke("right", frozenset({"shift"}))]


def _locked() -> Typing:
    t = Typing()
    t.tap("m:shift", "m:shift")
    return t


def test_locked_modifiers_are_cleared_by_pause():
    t = _locked()
    t.command(Command.PAUSE)
    t.run(lambda s: s.hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).hold(Pose.G1_RELAXED, 300))
    assert strokes(t.tap("k:a")) == [KeyStroke("a")]


def test_locked_modifiers_are_cleared_by_emergency_stop():
    t = _locked()
    t.command(Command.EMERGENCY_STOP)
    t.run(lambda s: s.hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).hold(Pose.G1_RELAXED, 300))
    assert strokes(t.tap("k:a")) == [KeyStroke("a")]


def test_locked_modifiers_are_cleared_by_hand_loss():
    t = _locked()
    t.run(lambda s: s.none(ms=600).hold(Pose.G1_RELAXED, 400, at=(0.5, 0.5)))
    assert strokes(t.tap("k:a")) == [KeyStroke("a")]


def test_locked_modifiers_are_cleared_by_a_mode_change():
    t = _locked()
    t.command(Command.SET_MODE, "MEDIA")
    t.command(Command.SET_MODE, "KEYBOARD")
    assert strokes(t.tap("k:a")) == [KeyStroke("a")]


def test_a_pinch_in_the_air_is_not_a_key():
    t = Typing()
    assert not strokes(t.run(lambda s: s.hold(Pose.G2_PINCH_INDEX, 600)))
