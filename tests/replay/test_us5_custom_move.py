"""US5: custom movements (circle, line): enrollment checks, recognition, and safety (D9)."""

from support.custom import (
    back_to,
    circle_path,
    enroll,
    gesture_from,
    line_path,
    movement_takes,
    new_engine,
    perform,
)
from support.hands import run
from support.keyboard import POINTER_EVENTS
from support.presenting import swipe

from gescrtl.core.custom import PATH_POINTS, SHAPE_DIM
from gescrtl.core.types import (
    Action,
    ButtonDown,
    Click,
    Command,
    CustomFired,
    MoveCursor,
    Pose,
    Scroll,
    SetupResult,
    SetupView,
    SystemAction,
)

CIRCLE = movement_takes(circle_path)
MIDDLE = dict(kind=Pose.G3_PINCH_MIDDLE, pinch_ratio=0.6)


def enrolled(name="circle", action="MUTE", build=CIRCLE, modes=(), mode="POINTER", **cfg):
    eng, s = new_engine(mode, **cfg)
    ev, values = enroll(eng, s, "move", name, build)
    assert values is not None, [e.text for e in ev if isinstance(e, SetupView)][-3:]
    eng.set_custom_gestures((gesture_from(values, action, modes),))
    return eng, s.next(), values


def fired(ev):
    return [e for e in ev if isinstance(e, CustomFired)]


def texts(ev):
    return [e.text for e in ev if isinstance(e, SetupView)]


# -- enrollment -----------------------------------------------------------------------------------


def test_enrolling_a_movement_records_five_timed_paths():
    eng, s = new_engine()
    ev, values = enroll(eng, s, "move", "circle", CIRCLE)
    assert values["kind"] == "move" and len(values["samples"]) == 5
    assert all(len(t) == 1 + 2 * PATH_POINTS + SHAPE_DIM for t in values["samples"])
    assert values["threshold"] >= 0.2 and 300 < values["samples"][0][0] < 1500


def test_enrollment_counts_down_before_each_take():
    eng, s = new_engine()
    ev, _ = enroll(eng, s, "move", "circle", CIRCLE)
    assert sum("get ready" in t for t in texts(ev)) >= 5 and any(
        "make the movement" in t for t in texts(ev)
    )


def test_a_movement_that_looks_like_the_open_hand_swipe_is_refused():
    def swipes(s):
        s.move(Pose.G6_OPEN_PALM, to=(0.35, 0.5), ms=300).hold(Pose.G6_OPEN_PALM, 2300)
        s.path(Pose.G6_OPEN_PALM, line_path((0.35, 0.5), 0.35), 300)
        return s.hold(Pose.G6_OPEN_PALM, 1500)

    eng, s = new_engine()
    ev, values = enroll(eng, s, "move", "swipe", swipes)
    assert values is None and any("swipe" in t for t in texts(ev))


def test_no_movement_for_a_while_asks_to_try_that_take_again():
    eng, s = new_engine()
    ev, values = enroll(eng, s, "move", "circle", lambda s: s.hold(Pose.G1_RELAXED, 9500))
    assert values is None and any("No movement" in t for t in texts(ev))
    assert eng.session is not None


def test_a_circle_and_a_line_cannot_be_mixed_in_one_gesture():
    def mixed(s):
        s.move(Pose.G1_RELAXED, to=(0.4, 0.5), ms=300).hold(Pose.G1_RELAXED, 2300)
        for i in range(5):
            path = circle_path if i in (0, 2, 4) else line_path
            pts = path((0.4, 0.5))
            s.path(Pose.G1_RELAXED, pts, 700)
            back_to(s, Pose.G1_RELAXED, pts[-1], (0.4, 0.5), 2400)
        return s

    eng, s = new_engine()
    ev, values = enroll(eng, s, "move", "mixed", mixed)
    assert values is None and any("too different" in t for t in texts(ev))


def test_a_movement_too_similar_to_an_existing_one_is_refused():
    eng, s, _ = enrolled()
    ev, second = enroll(eng, s, "move", "circle2", CIRCLE)
    assert second is None and any("too similar" in t for t in texts(ev))


def test_no_input_is_sent_while_enrolling_a_movement():
    eng, s = new_engine()
    ev, _ = enroll(eng, s, "move", "circle", CIRCLE)
    end = max(i for i, e in enumerate(ev) if isinstance(e, SetupResult))
    assert not [e for e in ev[:end] if isinstance(e, POINTER_EVENTS + (SystemAction,))]


# -- recognition ----------------------------------------------------------------------------------


def test_the_movement_fires_once_when_it_is_completed():
    eng, s, _ = enrolled()
    ev = run(eng, perform(s, circle_path).frames())
    assert [(e.name, e.action) for e in fired(ev)] == [("circle", "MUTE")]
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.MUTE]


def test_it_fires_at_the_end_of_the_movement_not_in_the_middle():
    eng, s, _ = enrolled()
    s.move(Pose.G1_RELAXED, to=(0.4, 0.5), ms=300).hold(Pose.G1_RELAXED, 700)
    run(eng, s.frames())
    mid = s.next().path(Pose.G1_RELAXED, circle_path((0.4, 0.5))[:12], 350)
    assert not fired(run(eng, mid.frames()))


def test_a_second_movement_inside_the_cooldown_is_swallowed():
    eng, s, _ = enrolled(custom_cooldown_ms=5000)
    perform(s, circle_path, rest_ms=400)
    perform(s, circle_path, rest_ms=400)
    assert len(fired(run(eng, s.frames()))) == 1


def test_after_the_cooldown_it_fires_again():
    eng, s, _ = enrolled(custom_cooldown_ms=1000)
    perform(s, circle_path)
    perform(s, circle_path, rest_ms=1500)
    assert len(fired(run(eng, s.frames()))) == 2


def test_a_different_movement_does_not_fire_it():
    eng, s, _ = enrolled()
    ev = run(eng, perform(s, line_path).frames())
    assert not fired(ev)


def test_two_movements_each_fire_their_own():
    eng, s, circle = enrolled()
    ev, line = enroll(eng, s, "move", "line", movement_takes(line_path, ms=350))
    assert line is not None
    eng.set_custom_gestures((gesture_from(circle, "MUTE"), gesture_from(line, "PLAY_PAUSE")))
    s2 = s.next()
    perform(s2, circle_path)
    perform(s2, line_path, ms=350, rest_ms=1500)
    ev = run(eng, s2.frames())
    assert [e.name for e in fired(ev)] == ["circle", "line"]


def test_a_movement_made_with_another_hand_shape_does_not_fire():
    eng, s, _ = enrolled()
    s.move(MIDDLE["kind"], to=(0.4, 0.5), ms=300)
    s.hold(MIDDLE["kind"], 700, pinch_ratio=MIDDLE["pinch_ratio"])
    s.path(MIDDLE["kind"], circle_path((0.4, 0.5)), 700)
    s.hold(MIDDLE["kind"], 700, pinch_ratio=MIDDLE["pinch_ratio"])
    assert not fired(run(eng, s.frames()))


def test_a_very_slow_or_very_long_movement_does_not_fire():
    eng, s, _ = enrolled()
    assert not fired(run(eng, perform(s, circle_path, ms=3200).frames()))
    eng, s, _ = enrolled()
    assert not fired(run(eng, perform(s, circle_path, ms=6000).frames()))


def test_in_pointer_mode_the_cursor_keeps_moving_and_nothing_is_clicked():
    eng, s, _ = enrolled()
    ev = run(eng, perform(s, circle_path).frames())
    assert len([e for e in ev if isinstance(e, MoveCursor)]) > 10
    assert not [e for e in ev if isinstance(e, (Click, ButtonDown, Scroll))]
    assert len(fired(ev)) == 1


def test_a_movement_during_a_pinch_or_drag_is_discarded():
    eng, s, _ = enrolled()
    s.move(Pose.G1_RELAXED, to=(0.4, 0.5), ms=300).hold(Pose.G1_RELAXED, 700)
    s.hold(Pose.G2_PINCH_INDEX, 500)  # a drag starts after 300 ms
    s.path(Pose.G2_PINCH_INDEX, circle_path((0.4, 0.5)), 700)
    s.hold(Pose.G2_PINCH_INDEX, 700).hold(Pose.G1_RELAXED, 700)
    assert not fired(run(eng, s.frames()))


def test_an_open_hand_swipe_in_presentation_only_changes_the_slide():
    eng, s, _ = enrolled(mode="PRESENTATION")
    s2 = swipe(s, 0.3, 0.7).hold(Pose.G6_OPEN_PALM, 1500)
    ev = run(eng, s2.frames())
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.SLIDE_NEXT]
    assert not fired(ev)


def test_a_movement_only_works_in_its_modes():
    eng, s, _ = enrolled(modes=("MEDIA",))
    assert not fired(run(eng, perform(s, circle_path).frames()))
    s2 = s.next().cmd(Command.SET_MODE, "MEDIA").hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    perform(s2, circle_path)
    assert len(fired(run(eng, s2.frames()))) == 1


def test_custom_movements_are_deterministic():
    def go():
        eng, s, _ = enrolled()
        return run(eng, perform(s, circle_path).frames())

    assert go() == go()
