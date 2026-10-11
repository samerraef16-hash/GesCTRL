"""US1: state transitions of the Pointer-Mode subset of the interaction model."""

import pytest
from support.hands import Script, resume_script, run
from support.registry import scenario

from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Command,
    CueChanged,
    CueKind,
    HintsShown,
    MoveCursor,
    Pose,
    ReleaseAll,
    State,
    StateChanged,
    Sub,
    Warning,
)

NOW = 10_000_000_000


def states(events):
    return [(e.state, e.sub, e.hud_text) for e in events if isinstance(e, StateChanged)]


def active_engine():
    eng = Engine()
    s = resume_script()
    run(eng, s.frames())
    assert eng.state is State.ACTIVE
    return eng, s


# -- launch and resume -------------------------------------------------------------------


def test_launch_is_paused_and_sends_nothing():
    eng = Engine()
    assert (eng.state, eng.sub) == (State.PAUSED, Sub.NONE)
    start = eng.start()
    assert states(start) == [(State.PAUSED, Sub.NONE, "Paused")]
    assert any(isinstance(e, HintsShown) and "palm" in e.items[0] for e in start)
    ev = run(eng, Script().hold(Pose.G1_RELAXED, 3000).frames())
    assert not any(isinstance(e, MoveCursor) for e in ev)
    assert eng.state is State.PAUSED


@scenario("resume_gesture")
def resume_gesture_script():
    return resume_script().frames()


def test_open_palm_held_resumes_into_pointer_with_hints():
    eng = Engine()
    ev = run(eng, resume_gesture_script())
    assert (State.ACTIVE, Sub.NORMAL, "Pointer") in states(ev)
    hints = [e for e in ev if isinstance(e, HintsShown)]
    assert hints and 0 < len(hints[0].items) <= 4


def test_open_palm_shorter_than_hold_does_not_resume():
    eng = Engine()
    run(eng, Script().hold(Pose.G6_OPEN_PALM, 700).hold(Pose.G1_RELAXED, 500).frames())
    assert eng.state is State.PAUSED


def test_hand_interrupting_the_palm_hold_restarts_it():
    eng = Engine()
    s = Script().hold(Pose.G6_OPEN_PALM, 700).none(2).hold(Pose.G6_OPEN_PALM, 700)
    run(eng, s.frames())
    assert eng.state is State.PAUSED


def test_resume_via_command():
    eng = Engine()
    ev = eng.command(Command.RESUME, NOW)
    assert (State.ACTIVE, Sub.NORMAL, "Pointer") in states(ev)


# -- clutch and pause ----------------------------------------------------------------------


@scenario("clutch")
def clutch_script():
    s = resume_script()
    s.hold(Pose.G1_RELAXED, 300, at=(0.4, 0.4))
    s.hold(Pose.G8_FLAT_HAND, 600, at=(0.4, 0.4))
    s.move(Pose.G8_FLAT_HAND, to=(0.7, 0.7), ms=300)
    s.hold(Pose.G1_RELAXED, 600, at=(0.7, 0.7))
    return s.frames()


def test_flat_hand_freezes_cursor_then_resumes_following():
    ev = run(Engine(), clutch_script())
    sts = states(ev)
    assert (State.ACTIVE, Sub.CLUTCHED, "Pointer · Hold") in sts
    assert sts[-1] == (State.ACTIVE, Sub.NORMAL, "Pointer")
    i = next(k for k, e in enumerate(ev) if isinstance(e, StateChanged) and e.sub is Sub.CLUTCHED)
    j = next(
        k for k, e in enumerate(ev) if k > i and isinstance(e, StateChanged) and e.sub is Sub.NORMAL
    )
    assert not any(isinstance(e, MoveCursor) for e in ev[i:j])
    assert any(isinstance(e, ReleaseAll) for e in ev[max(0, i - 2) : i + 1])
    assert any(isinstance(e, CueChanged) and e.kind is CueKind.CLUTCH for e in ev[i:j])
    assert any(isinstance(e, MoveCursor) for e in ev[j:])


def test_flat_hand_held_for_pause_time_pauses_and_releases():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 300).hold(Pose.G8_FLAT_HAND, 2200)
    ev = run(eng, s.frames())
    assert (State.PAUSED, Sub.NONE, "Paused") in states(ev)
    assert eng.state is State.PAUSED
    assert any(isinstance(e, ReleaseAll) for e in ev)


def test_flat_hand_shorter_than_the_pause_time_only_clutches():
    eng, s = active_engine()
    run(eng, s.next().hold(Pose.G1_RELAXED, 300).hold(Pose.G8_FLAT_HAND, 1200).frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.CLUTCHED


def test_pause_cooldown_blocks_instant_gesture_resume():
    eng = Engine()
    s = resume_script().hold(Pose.G8_FLAT_HAND, 2000)
    run(eng, s.frames())
    assert eng.state is State.PAUSED
    # the flat hand opens straight into an open palm: needs the hold time *and* the cooldown
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G6_OPEN_PALM, 600)
    run(eng, s2.frames())
    assert eng.state is State.PAUSED
    s3 = Script(t0_ns=s2.t_ns).hold(Pose.G6_OPEN_PALM, 800)
    run(eng, s3.frames())
    assert eng.state is State.ACTIVE


def test_pausing_with_an_open_hand_does_not_resume_by_itself():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G6_OPEN_PALM, 300).cmd(Command.PAUSE)
    s2.hold(Pose.G6_OPEN_PALM, 4000)  # hand stays open for 4 s after pausing
    run(eng, s2.frames())
    assert eng.state is State.PAUSED
    # showing a different pose and then the palm again does resume
    s3 = Script(t0_ns=s2.t_ns).hold(Pose.G1_RELAXED, 300).hold(Pose.G6_OPEN_PALM, 1300)
    run(eng, s3.frames())
    assert eng.state is State.ACTIVE


def test_fist_freezes_the_cursor_but_is_not_a_clutch_or_pause():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s2.hold(Pose.G5_FIST, 600).move(Pose.G5_FIST, to=(0.7, 0.7), ms=600)
    ev = run(eng, s2.frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.NORMAL
    i = next(k for k, e in enumerate(ev) if isinstance(e, ReleaseAll))
    assert not any(isinstance(e, MoveCursor) for e in ev[i:])  # frozen while the fist is held
    s3 = Script(t0_ns=s2.t_ns).hold(Pose.G1_RELAXED, 600, at=(0.7, 0.7))
    assert any(isinstance(e, MoveCursor) for e in run(eng, s3.frames()))


def test_a_long_fist_never_pauses():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G8_FLAT_HAND, 400).hold(Pose.G5_FIST, 3000)
    run(eng, s2.frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.NORMAL


def test_thumbs_up_is_neither_clutch_nor_pause():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300).hold(Pose.G4_THUMBS_UP, 2500)
    run(eng, s2.frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.NORMAL


# -- emergency stop ---------------------------------------------------------------------------


def test_emergency_stop_from_active_stops_then_pauses():
    eng, s = active_engine()
    t = s.t_ns
    ev = eng.command(Command.EMERGENCY_STOP, t)
    assert any(isinstance(e, ReleaseAll) for e in ev)
    assert states(ev)[-1] == (State.PAUSED, Sub.NONE, "Stopped")
    later = eng.step(None, t + 700_000_000)
    assert states(later) == [(State.PAUSED, Sub.NONE, "Paused")]


def test_emergency_stop_in_paused_only_releases():
    eng = Engine()
    ev = eng.command(Command.EMERGENCY_STOP, NOW)
    assert [type(e) for e in ev] == [ReleaseAll]


def test_emergency_stop_in_inactive_is_a_no_op():
    eng = Engine()
    eng.command(Command.TURN_OFF, NOW)
    assert eng.command(Command.EMERGENCY_STOP, NOW + 1) == []


def test_emergency_stop_from_tracking_lost():
    eng, s = active_engine()
    run(eng, Script(t0_ns=s.t_ns).none(5).frames())
    assert eng.state is State.TRACKING_LOST
    ev = eng.command(Command.EMERGENCY_STOP, s.t_ns + 10**9)
    assert eng.state is State.PAUSED and any(isinstance(e, ReleaseAll) for e in ev)


# -- tracking loss --------------------------------------------------------------------------------


@scenario("hand_loss_and_return")
def loss_script():
    s = resume_script()
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).none(5).hold(Pose.G1_RELAXED, 600, at=(0.5, 0.5))
    return s.frames()


def test_short_dropout_changes_nothing():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300).none(2).hold(Pose.G1_RELAXED, 300)
    ev = run(eng, s2.frames())
    assert not states(ev) and eng.state is State.ACTIVE


def test_hand_loss_releases_shows_message_and_returns_automatically():
    eng = Engine()
    ev = run(eng, loss_script())
    sts = states(ev)
    assert (State.TRACKING_LOST, Sub.HAND_MISSING, "Hand not visible") in sts
    assert sts[-1] == (State.ACTIVE, Sub.NORMAL, "Pointer")
    i = next(
        k for k, e in enumerate(ev) if isinstance(e, StateChanged) and e.sub is Sub.HAND_MISSING
    )
    assert isinstance(ev[i - 1], ReleaseAll)
    assert eng.state is State.ACTIVE


def test_paused_stays_paused_when_hand_leaves_and_returns():
    eng = Engine()
    run(eng, Script().hold(Pose.G1_RELAXED, 300).none(10).hold(Pose.G1_RELAXED, 600).frames())
    assert eng.state is State.PAUSED


# -- turn off / on -----------------------------------------------------------------------------


@pytest.mark.parametrize("where", ["paused", "active", "clutched", "lost"])
def test_turn_off_from_every_state_then_on_returns_to_paused(where):
    eng = Engine()
    t = NOW
    if where != "paused":
        s = resume_script()
        run(eng, s.frames())
        t = s.t_ns
    if where == "clutched":
        s2 = Script(t0_ns=t).hold(Pose.G8_FLAT_HAND, 300)
        run(eng, s2.frames())
        t = s2.t_ns
        assert eng.sub is Sub.CLUTCHED
    if where == "lost":
        s2 = Script(t0_ns=t).none(5)
        run(eng, s2.frames())
        t = s2.t_ns
        assert eng.state is State.TRACKING_LOST
    ev = eng.command(Command.TURN_OFF, t)
    assert eng.state is State.INACTIVE
    assert any(isinstance(e, ReleaseAll) for e in ev)
    assert states(ev)[-1][2] == ""  # indicator hidden
    ev = eng.command(Command.TURN_ON, t + 1000)
    assert eng.state is State.PAUSED and states(ev)[0][2] == "Paused"


def test_frames_are_ignored_while_inactive():
    eng = Engine()
    eng.command(Command.TURN_OFF, NOW)
    assert run(eng, resume_script().frames()) == []
    assert eng.state is State.INACTIVE


# -- pause / resume commands --------------------------------------------------------------------


def test_toggle_pause_round_trip():
    eng = Engine()
    eng.command(Command.TOGGLE_PAUSE, NOW)
    assert eng.state is State.ACTIVE
    ev = eng.command(Command.TOGGLE_PAUSE, NOW + 10**9)
    assert eng.state is State.PAUSED and any(isinstance(e, ReleaseAll) for e in ev)


def test_pause_from_tracking_lost():
    eng, s = active_engine()
    run(eng, Script(t0_ns=s.t_ns).none(5).frames())
    eng.command(Command.PAUSE, s.t_ns + 10**9)
    assert eng.state is State.PAUSED


# -- camera -------------------------------------------------------------------------------------


def test_camera_lost_and_back():
    eng, s = active_engine()
    t = s.t_ns
    ev = eng.command(Command.CAMERA_LOST, t, "in use by another app")
    assert any(isinstance(e, ReleaseAll) for e in ev)
    assert (
        State.TRACKING_LOST,
        Sub.CAMERA_UNAVAILABLE,
        "Camera unavailable · in use by another app",
    ) in states(ev)
    eng.command(Command.CAMERA_BACK, t + 10**9)
    assert eng.sub is Sub.HAND_MISSING
    run(eng, Script(t0_ns=t + 2 * 10**9).hold(Pose.G1_RELAXED, 300).frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.NORMAL


def test_camera_lost_while_paused_is_shown_and_blocks_resume():
    eng = Engine()
    ev = eng.command(Command.CAMERA_LOST, NOW, "disconnected")
    assert states(ev)[-1][2] == "Paused · Camera unavailable"
    ev = eng.command(Command.RESUME, NOW + 1)
    assert eng.state is State.PAUSED and any(isinstance(e, Warning) for e in ev)
    eng.command(Command.CAMERA_BACK, NOW + 2)
    eng.command(Command.RESUME, NOW + 3)
    assert eng.state is State.ACTIVE


# -- emergency hotkey missing (FR-008) -----------------------------------------------------------


def test_resume_refused_while_hotkey_unavailable():
    eng = Engine()
    eng.command(Command.HOTKEY_UNAVAILABLE, NOW)
    ev = run(eng, resume_script().frames())
    assert eng.state is State.PAUSED
    assert any(isinstance(e, Warning) for e in ev)
    eng.command(Command.RESUME, NOW + 10**10)
    assert eng.state is State.PAUSED
    eng.command(Command.HOTKEY_AVAILABLE, NOW + 10**10 + 1)
    eng.command(Command.RESUME, NOW + 10**10 + 2)
    assert eng.state is State.ACTIVE


# -- G7 does nothing -----------------------------------------------------------------------------


def test_three_finger_gesture_has_no_effect():
    eng, s = active_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s2.frames())
    s3 = Script(t0_ns=s2.t_ns).hold(Pose.G7_THREE_FINGERS, 2000, at=(0.5, 0.5))
    ev = run(eng, s3.frames())
    assert eng.state is State.ACTIVE and eng.sub is Sub.NORMAL
    # before G7 is stable (3 frames) the pose still reads as relaxed: the cursor may be re-sent
    # at the same spot, but never anything else, and nothing once G7 is stable
    others = [e for e in ev if not isinstance(e, CueChanged | MoveCursor)]
    assert not others
    moves = [e for e in ev if isinstance(e, MoveCursor)]
    assert len(moves) <= 2 and len({(m.nx, m.ny) for m in moves}) <= 1


# -- exit -----------------------------------------------------------------------------------------


def test_exit_releases_everything():
    eng, s = active_engine()
    ev = eng.command(Command.EXIT, s.t_ns)
    assert isinstance(ev[0], ReleaseAll) and eng.state is State.INACTIVE


def test_moving_flat_hand_clutches_but_never_pauses():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 300, at=(0.3, 0.5))
    for k in range(8):  # keeps travelling for 4 s: not still, so no pause
        s.move(Pose.G8_FLAT_HAND, to=(0.3 + 0.05 * (k + 1), 0.5), ms=500)
    ev = run(eng, s.frames())
    assert not any(isinstance(e, StateChanged) and e.state is State.PAUSED for e in ev)
    assert eng.sm.sub is Sub.CLUTCHED


def test_hand_that_only_passes_through_flat_does_not_clutch():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 300).hold(Pose.G8_FLAT_HAND, 100)  # 3 frames
    s.hold(Pose.G1_RELAXED, 300)
    run(eng, s.frames())
    assert eng.sm.sub is Sub.NORMAL
