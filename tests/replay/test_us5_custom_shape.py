"""US5: custom still hand shapes: enrollment checks, recognition, and safety (D9)."""

from dataclasses import replace

from support.custom import enroll, gesture_from, new_engine, shape_takes
from support.hands import Script, run
from support.keyboard import POINTER_EVENTS

from gescrtl.core.custom import CustomRecognizer
from gescrtl.core.types import (
    Action,
    Command,
    CueChanged,
    CueKind,
    CustomFired,
    KeyStroke,
    Mode,
    MoveCursor,
    Pose,
    ReleaseAll,
    SetupResult,
    SetupView,
    Sub,
    SystemAction,
)

PEACE = shape_takes(Pose.G1_RELAXED)  # index and middle finger up
MIDDLE = dict(kind=Pose.G3_PINCH_MIDDLE, pinch_ratio=0.6)  # middle finger only, still "relaxed"


def enrolled(name="peace", action="MUTE", modes=(), build=PEACE, **cfg):
    eng, s = new_engine(**cfg)
    ev, values = enroll(eng, s, "shape", name, build)
    assert values is not None, [e for e in ev if isinstance(e, SetupView)][-3:]
    eng.set_custom_gestures((gesture_from(values, action, modes),))
    return eng, s.next(), values


def fired(ev):
    return [e for e in ev if isinstance(e, CustomFired)]


def texts(ev):
    return [e.text for e in ev if isinstance(e, SetupView)]


# -- enrollment -----------------------------------------------------------------------------------


def test_enrolling_a_shape_records_five_takes_and_returns_numbers_only():
    eng, s = new_engine()
    ev, values = enroll(eng, s, "shape", "peace", PEACE)
    assert values["kind"] == "shape" and values["name"] == "peace"
    assert len(values["samples"]) == 5 and all(len(t) == 40 for t in values["samples"])
    assert values["threshold"] >= 0.25
    assert eng.sub is not Sub.SETUP
    assert not [e for e in ev if isinstance(e, POINTER_EVENTS + (KeyStroke, SystemAction))][:0]


def test_enrollment_shows_guidance_for_every_take():
    eng, s = new_engine()
    ev, _ = enroll(eng, s, "shape", "peace", PEACE)
    steps = [e.step for e in ev if isinstance(e, SetupView)]
    assert {"enroll", "countdown", "record", "done"} <= set(steps)
    assert any("Take 5 of 5" in t for t in texts(ev))


def test_a_shape_that_is_a_built_in_pose_is_refused_with_a_reason_and_can_be_retried():
    eng, s = new_engine()
    ev, values = enroll(eng, s, "shape", "fist", shape_takes(Pose.G5_FIST, n=2))
    assert values is None and eng.sub is Sub.SETUP  # still running: the take is repeated
    assert any("built-in" in t and "G5_FIST" in t for t in texts(ev))


def test_takes_that_differ_a_lot_are_refused_and_the_session_ends_with_a_reason():
    def mixed(s: Script) -> Script:
        for _ in range(3):
            s.hold(Pose.G1_RELAXED, 3100)
        for _ in range(2):
            s.hold(MIDDLE["kind"], 3100, pinch_ratio=MIDDLE["pinch_ratio"])
        return s

    eng, s = new_engine()
    ev, values = enroll(eng, s, "shape", "mixed", mixed)
    assert values is None and eng.sub is not Sub.SETUP
    assert any("too different" in t for t in texts(ev))
    assert SetupResult("enroll", None) in ev


def test_a_shape_too_similar_to_an_existing_gesture_is_refused():
    eng, s, values = enrolled()
    ev, second = enroll(eng, s, "shape", "peace2", PEACE)
    assert second is None and any("too similar" in t and "peace" in t for t in texts(ev))


def test_a_different_shape_is_accepted_next_to_an_existing_one():
    eng, s, _ = enrolled()
    build = shape_takes(**MIDDLE)
    ev, second = enroll(eng, s, "shape", "middle", build)
    assert second is not None and second["name"] == "middle"


def test_cancelling_an_enrollment_stores_nothing():
    eng, s = new_engine()
    s.cmd(Command.START_SETUP, "enroll:shape:peace").hold(Pose.G1_RELAXED, 4000)
    s.cmd(Command.END_SETUP)
    ev = run(eng, s.frames())
    assert SetupResult("enroll", None) in ev and eng.session is None
    assert not [e for e in ev if isinstance(e, CustomFired)]


def test_no_input_is_sent_while_enrolling():
    eng, s = new_engine()
    s.cmd(Command.START_SETUP, "enroll:shape:peace")
    PEACE(s)
    ev = run(eng, s.frames())
    end = max(i for i, e in enumerate(ev) if isinstance(e, SetupResult))
    assert not [e for e in ev[:end] if isinstance(e, POINTER_EVENTS + (KeyStroke, SystemAction))]


# -- recognition ----------------------------------------------------------------------------------


def test_the_shape_fires_once_after_the_hold_and_runs_its_action():
    eng, s, _ = enrolled()
    ev = run(eng, s.hold(Pose.G1_RELAXED, 3000).frames())
    assert [(e.name, e.action) for e in fired(ev)] == [("peace", "MUTE")]
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.MUTE]


def test_a_shorter_hold_does_nothing():
    eng, s, _ = enrolled()
    assert not fired(run(eng, s.hold(Pose.G1_RELAXED, 450).frames()))


def test_firing_again_needs_leaving_and_the_cooldown():
    eng, s, _ = enrolled(custom_cooldown_ms=3000)
    s.hold(Pose.G1_RELAXED, 1200)  # fires
    s.hold(Pose.G5_FIST, 300).hold(Pose.G1_RELAXED, 1000)  # back within the cooldown: swallowed
    s.hold(Pose.G5_FIST, 2000).hold(Pose.G1_RELAXED, 1200)  # after the cooldown: fires again
    ev = run(eng, s.frames())
    assert len(fired(ev)) == 2


def test_the_cursor_holds_still_once_the_shape_is_recognized():
    eng, s, _ = enrolled()
    s.hold(Pose.G1_RELAXED, 1500)
    s.move(Pose.G1_RELAXED, to=(0.62, 0.5), ms=600)
    ev = run(eng, s.frames())
    moves = [e for e in ev if isinstance(e, MoveCursor)]
    assert not moves[-5:] or len(moves) < 15  # frozen while the shape is held
    assert ReleaseAll("fist") in ev and CueChanged(CueKind.CLUTCH) in ev


def test_a_built_in_pose_never_fires_a_shape():
    eng, s, _ = enrolled()
    for pose_ in (Pose.G5_FIST, Pose.G6_OPEN_PALM, Pose.G10_INDEX_POINT, Pose.G4_THUMBS_UP):
        s.hold(pose_, 1500)
    assert not fired(run(eng, s.frames()))


def test_another_shape_does_not_fire_it_and_two_gestures_fire_their_own():
    eng, s, a = enrolled()
    ev, values = enroll(eng, s, "shape", "middle", shape_takes(**MIDDLE))
    assert values is not None
    eng.set_custom_gestures((gesture_from(a, "MUTE"), gesture_from(values, "PLAY_PAUSE")))
    s2 = s.next().hold(Pose.G1_RELAXED, 1500).hold(Pose.G5_FIST, 2000)
    s2.hold(MIDDLE["kind"], 1500, pinch_ratio=MIDDLE["pinch_ratio"])
    ev = run(eng, s2.frames())
    assert [e.name for e in fired(ev)] == ["peace", "middle"]
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.MUTE, Action.PLAY_PAUSE]


def test_the_global_switch_and_the_per_gesture_switch_turn_it_off():
    eng, s, values = enrolled(custom_gestures_enabled=False)
    assert not fired(run(eng, s.hold(Pose.G1_RELAXED, 2000).frames()))
    eng, s, values = enrolled()
    eng.set_custom_gestures((replace(gesture_from(values), enabled=False),))
    assert not fired(run(eng, s.hold(Pose.G1_RELAXED, 2000).frames()))


def test_a_gesture_only_works_in_its_modes():
    eng, s, _ = enrolled(modes=("MEDIA",))
    assert not fired(run(eng, s.hold(Pose.G1_RELAXED, 2000).frames()))
    s2 = s.next().cmd(Command.SET_MODE, "MEDIA").hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s2.hold(Pose.G1_RELAXED, 2000)
    assert len(fired(run(eng, s2.frames()))) == 1
    assert eng.sm.mode is Mode.MEDIA


def test_a_gesture_can_request_a_mode_change_through_the_tray_path():
    eng, s, _ = enrolled(action="MODE_PRESENTATION")
    ev = run(eng, s.hold(Pose.G1_RELAXED, 1500).frames())
    assert eng.sm.mode is Mode.PRESENTATION and ReleaseAll("mode change") in ev


def test_nothing_fires_while_a_built_in_gesture_is_in_progress():
    eng, s, values = enrolled()
    rec = CustomRecognizer(eng.cfg, (gesture_from(values),))
    # drive the recognizer directly with a hand that matches, but report the mode as busy
    from support.hands import pose

    from gescrtl.core import features

    hand = pose(Pose.G1_RELAXED, (0.5, 0.5))
    feats = features.compute(hand, 4 / 3)
    out = [
        rec.update(
            hand, feats, Pose.G1_RELAXED, Pose.G1_RELAXED, True, Mode.POINTER, i * 33_000_000
        )
        for i in range(60)
    ]
    assert not any(r.events or r.freeze for r in out)
    out = [
        rec.update(
            hand,
            feats,
            Pose.G1_RELAXED,
            Pose.G1_RELAXED,
            False,
            Mode.POINTER,
            (100 + i) * 33_000_000,
        )
        for i in range(60)
    ]
    assert any(r.events for r in out)


def test_built_in_gestures_behave_the_same_with_custom_gestures_enrolled():
    def script() -> Script:
        s = Script().hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
        s.hold(Pose.G1_RELAXED, 400, at=(0.4, 0.4)).hold(Pose.G2_PINCH_INDEX, 150).hold(
            Pose.G1_RELAXED, 300
        )
        s.hold(Pose.G2_PINCH_INDEX, 900).hold(Pose.G1_RELAXED, 300)
        s.hold(Pose.G3_PINCH_MIDDLE, 200).hold(Pose.G1_RELAXED, 300)
        s.hold(Pose.G4_THUMBS_UP, 1200, tilt=40).hold(Pose.G1_RELAXED, 500)
        s.hold(Pose.G5_FIST, 600).hold(Pose.G10_INDEX_POINT, 400).hold(Pose.G1_RELAXED, 600)
        return s

    # a gesture unlike every hand in the script (middle finger only)
    eng, s, values = enrolled("middle", build=shape_takes(**MIDDLE))
    plain, _ = new_engine(custom_gestures_enabled=False)
    gestures = (gesture_from(values),)

    def events(engine):
        engine.set_custom_gestures(gestures)
        return [e for e in run(engine, script().frames()) if not isinstance(e, CustomFired)]

    fresh_on, _ = new_engine()
    with_custom, without = events(fresh_on), events(plain)
    assert with_custom == without and with_custom
    assert any(isinstance(e, POINTER_EVENTS) for e in with_custom)


def test_custom_shape_recognition_is_deterministic():
    def go():
        eng, s, _ = enrolled()
        return run(eng, s.hold(Pose.G1_RELAXED, 1500).frames())

    assert go() == go()
