"""US1: both hands type in Keyboard Mode, each pressing the key it points at (ADR 0007)."""

from support.hands import HandFrame, pose, run
from support.keyboard import POINTER_EVENTS, kb_engine, key_cam, last_view, strokes

from gescrtl.core.config import CoreConfig
from gescrtl.core.types import Click, Command, KeyStroke, Pose, ReleaseAll


def _setup(cfg=None, first="h", other="j"):
    """Primary hand on key ``first``, second hand on key ``other``, both relaxed."""
    eng, s = kb_engine(cfg)
    ident = lambda k: k if ":" in k else f"k:{k}"  # noqa: E731
    a, b = key_cam(ident(first)), key_cam(ident(other))
    s.move(Pose.G1_RELAXED, to=a, ms=400)
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    return eng, s, a, b


def test_a_pinch_of_the_second_hand_presses_the_key_it_points_at():
    eng, s, a, b = _setup()
    s.hold(Pose.G1_RELAXED, 400, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    ev = run(eng, s.frames())
    assert strokes(ev) == [KeyStroke("j")]
    assert not [e for e in ev if isinstance(e, POINTER_EVENTS)]


def test_the_primary_hand_still_types_with_the_second_hand_resting():
    eng, s, a, b = _setup()
    s.hold(Pose.G2_PINCH_INDEX, 400, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    assert strokes(run(eng, s.frames())) == [KeyStroke("h")]


def test_both_hands_type_one_after_the_other():
    eng, s, a, b = _setup()
    s.hold(Pose.G2_PINCH_INDEX, 300, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G2_PINCH_INDEX, 300, second=(Pose.G1_RELAXED, b))
    assert strokes(run(eng, s.frames())) == [KeyStroke("h"), KeyStroke("j"), KeyStroke("h")]


def test_both_hands_pinching_together_press_both_keys():
    eng, s, a, b = _setup()
    s.hold(Pose.G2_PINCH_INDEX, 400, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    assert sorted(k.key for k in strokes(run(eng, s.frames()))) == ["h", "j"]


def test_both_hands_on_the_same_key_press_it_once():
    eng, s, a, _ = _setup(other="h")
    s.hold(Pose.G2_PINCH_INDEX, 400, second=(Pose.G2_PINCH_INDEX, a))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, a))
    assert strokes(run(eng, s.frames())) == [KeyStroke("h")]


def test_the_view_shows_where_each_hand_points():
    eng, s, a, b = _setup()
    v = last_view(run(eng, s.frames()))
    assert (v.highlight, v.highlight2) == ("k:h", "k:j")


def test_a_modifier_pressed_by_one_hand_applies_to_a_key_of_the_other():
    eng, s, a, b = _setup(first="m:shift", other="j")
    s.hold(Pose.G1_RELAXED, 600, second=(Pose.G1_RELAXED, b))  # let the pointer settle on Shift
    s.hold(Pose.G2_PINCH_INDEX, 300, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    assert strokes(run(eng, s.frames())) == [KeyStroke("J")]


def _second_pinch(**kw):
    eng, s, a, b = _setup(cfg=kw.pop("cfg", None))
    dx = kw.pop("dx", 0.0)
    far = (b[0] + dx, b[1])
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, far), **kw)
    s.hold(Pose.G1_RELAXED, 500, second=(Pose.G2_PINCH_INDEX, far), **kw)
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, far), **kw)
    return strokes(run(eng, s.frames()))


def test_a_hand_with_the_same_handedness_label_is_ignored():
    assert _second_pinch(second_hand="Right") == []


def test_a_hand_too_far_from_the_primary_is_ignored():
    assert _second_pinch(dx=0.9) == []  # well past the 5 hand size limit


def test_hands_a_natural_shoulder_width_apart_still_work():
    eng, s, a, b = _setup(first="f", other="j")
    s.hold(Pose.G1_RELAXED, 400, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300, second=(Pose.G1_RELAXED, b))
    assert strokes(run(eng, s.frames())) == [KeyStroke("j")]


def test_a_low_confidence_hand_is_ignored():
    eng, s, a, b = _setup()
    low = pose(Pose.G2_PINCH_INDEX, b, score=0.3, handedness="Left")
    base = pose(Pose.G1_RELAXED, a)
    t = s.t_ns
    frames = [HandFrame(t + i * s.frame_ns, (base, low)) for i in range(20)]
    assert not strokes(run(eng, frames))


def test_a_hand_that_just_appeared_must_be_stable_first():
    eng, s = kb_engine()
    a, b = key_cam("k:h"), key_cam("k:j")
    s.move(Pose.G1_RELAXED, to=a, ms=400).hold(Pose.G1_RELAXED, 300)
    # the second hand appears already pinching and leaves again within two frames
    s.hold(Pose.G2_PINCH_INDEX, 66, second=(Pose.G2_PINCH_INDEX, b))
    s.hold(Pose.G1_RELAXED, 300)
    assert strokes(run(eng, s.frames())) == []


def test_losing_the_second_hand_presses_and_releases_nothing_extra():
    eng, s, a, b = _setup()
    s.hold(Pose.G1_RELAXED, 300)  # it leaves the view
    ev = run(eng, s.frames())
    assert not strokes(ev) and not [e for e in ev if isinstance(e, ReleaseAll)]


def test_the_second_hand_cannot_do_anything_but_type():
    eng, s, a, b = _setup()
    # a fist, an open palm and a thumbs up of the second hand change nothing
    for pz in (Pose.G5_FIST, Pose.G6_OPEN_PALM, Pose.G4_THUMBS_UP, Pose.G8_FLAT_HAND):
        s.hold(Pose.G1_RELAXED, 500, second=(pz, b))
    ev = run(eng, s.frames())
    assert not strokes(ev) and not [e for e in ev if isinstance(e, POINTER_EVENTS)]


def test_the_setting_turns_two_handed_typing_off():
    assert _second_pinch(cfg=CoreConfig(two_hand_press=False)) == []


def test_other_modes_ignore_the_second_hand():
    from support.menu import active_in

    eng, s = active_in("POINTER")
    pos = (0.5, 0.5)
    s.hold(Pose.G1_RELAXED, 300, at=pos, second=(Pose.G1_RELAXED, (0.7, 0.5)))
    s.hold(Pose.G1_RELAXED, 500, second=(Pose.G2_PINCH_INDEX, (0.7, 0.5)))
    ev = run(eng, s.frames())
    assert not [e for e in ev if isinstance(e, Click)] and not strokes(ev)


def test_leaving_keyboard_mode_forgets_the_second_hand():
    eng, s, a, b = _setup()
    s.cmd(Command.SET_MODE, "POINTER").hold(Pose.G1_RELAXED, 300)
    assert not strokes(run(eng, s.frames()))
