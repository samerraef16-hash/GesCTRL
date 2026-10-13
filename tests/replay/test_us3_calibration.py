"""US3: guided calibration measures reach and pinch, sends no input, and can be cancelled."""

import pytest
from support.hands import T0_NS, Script, pose, resume_script, run
from support.keyboard import POINTER_EVENTS

from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Command,
    HandFrame,
    KeyStroke,
    Pose,
    SetupResult,
    SetupView,
    State,
    Sub,
    SystemAction,
)

CORNERS = [(0.3, 0.3), (0.7, 0.3), (0.7, 0.7), (0.3, 0.7)]


def start():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 300)
    run(eng, s.frames())
    return eng, s.next().cmd(Command.START_SETUP, "calibration")


def check_step(s, fps_hold_ms=2400):
    return s.hold(Pose.G6_OPEN_PALM, fps_hold_ms, at=(0.5, 0.5))


def reach_step(s, corners=CORNERS):
    for c in corners:
        s.move(Pose.G1_RELAXED, to=c, ms=400).hold(Pose.G1_RELAXED, 1300)
    return s


def open_step(s, ratio=None):
    s.move(Pose.G6_OPEN_PALM, to=(0.5, 0.5), ms=500)
    if ratio is None:
        return s.hold(Pose.G6_OPEN_PALM, 2400)
    return s.hold(Pose.G2_PINCH_INDEX, 2400, pinch_ratio=ratio)


def pinch_step(s, n=5, ratio=0.07):
    for _ in range(n):
        s.hold(Pose.G2_PINCH_INDEX, 300, pinch_ratio=ratio).hold(Pose.G6_OPEN_PALM, 300)
    return s.hold(Pose.G6_OPEN_PALM, 300)


def full_run(corners=CORNERS):
    eng, s = start()
    pinch_step(open_step(reach_step(check_step(s), corners)))
    return eng, s, run(eng, s.frames())


def result_of(events):
    got = [e for e in events if isinstance(e, SetupResult)]
    return got[-1] if got else None


def test_a_full_run_returns_region_center_and_pinch_thresholds():
    eng, s, ev = full_run()
    res = result_of(ev)
    assert res is not None and res.kind == "calibration" and res.values is not None
    v = res.values
    assert v["active_region"] == pytest.approx(0.4, abs=0.02)
    assert (v["active_center_x"], v["active_center_y"]) == pytest.approx((0.5, 0.5), abs=0.02)
    assert 0.05 <= v["pinch_enter"] < v["pinch_release"] <= 0.6  # hysteresis kept
    assert (eng.state, eng.sub) == (State.ACTIVE, Sub.NORMAL)


def test_a_wide_and_short_reach_uses_the_smaller_side_so_every_corner_is_reachable():
    corners = [(0.25, 0.3), (0.75, 0.3), (0.75, 0.6), (0.25, 0.6)]
    _, _, ev = full_run(corners)
    v = result_of(ev).values
    assert v["active_region"] == pytest.approx(0.3, abs=0.02)
    assert (v["active_center_x"], v["active_center_y"]) == pytest.approx((0.5, 0.45), abs=0.02)


def test_no_pointer_key_or_action_input_is_sent_during_calibration():
    _, _, ev = full_run()
    inside = ev[: ev.index(result_of(ev))]  # everything up to the end of the session
    assert any(isinstance(e, SetupView) for e in inside)
    assert not [e for e in inside if isinstance(e, POINTER_EVENTS + (KeyStroke, SystemAction))]


def test_progress_is_shown_for_every_step():
    _, _, ev = full_run()
    steps = [e.step for e in ev if isinstance(e, SetupView)]
    for step in ("check", "reach", "open", "pinch", "done"):
        assert step in steps
    targets = [e.target for e in ev if isinstance(e, SetupView) and e.step == "reach"]
    assert {(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)} <= set(targets)


def texts(events):
    return [e.text for e in events if isinstance(e, SetupView)]


def test_a_slow_camera_is_reported_and_the_run_does_not_advance():
    eng = Engine()
    s = Script(fps=10).hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).hold(Pose.G1_RELAXED, 400)
    run(eng, s.frames())
    s = s.next().cmd(Command.START_SETUP, "calibration")
    s.hold(Pose.G6_OPEN_PALM, 3000, at=(0.5, 0.5))
    ev = run(eng, s.frames())
    assert any("slow" in t for t in texts(ev)) and "reach" not in [
        e.step for e in ev if isinstance(e, SetupView)
    ]


def sized_frames(kind, scale, ms, t0, fps=30):
    step = 1_000_000_000 // fps
    hand = pose(kind, (0.5, 0.5), scale=scale)
    return [HandFrame(t0 + i * step, (hand,)) for i in range(round(ms * fps / 1000))]


@pytest.mark.parametrize(("scale", "word"), [(0.04, "closer"), (0.6, "back")])
def test_a_hand_too_far_or_too_close_is_told_how_to_fix_it(scale, word):
    eng = Engine()
    frames = sized_frames(Pose.G6_OPEN_PALM, scale, 1400, T0_NS)
    run(eng, frames)  # resumes
    t = frames[-1].t_ns + 33_000_000
    eng.command(Command.START_SETUP, t, "calibration")
    ev = run(eng, sized_frames(Pose.G1_RELAXED, scale, 2600, t + 33_000_000))
    assert eng.sub is Sub.SETUP
    assert any(word in text for text in texts(ev))


def test_the_hand_must_travel_between_corners():
    eng, s = start()
    check_step(s).hold(Pose.G1_RELAXED, 3000, at=(0.3, 0.3))  # stays at the first corner only
    ev = run(eng, s.frames())
    reach = [e for e in ev if isinstance(e, SetupView) and e.step == "reach"]
    assert reach and "top-left" in reach[-1].text and "top-right" not in " ".join(texts(ev))


def test_corners_that_are_too_close_together_are_refused():
    eng, s = start()
    check_step(s)
    reach_step(s, [(0.50, 0.50), (0.52, 0.50), (0.52, 0.52), (0.50, 0.52)])
    ev = run(eng, s.frames())
    assert result_of(ev) is None


def test_a_pinch_that_looks_like_the_open_hand_is_refused_and_asks_again():
    eng, s = start()
    pinch_step(open_step(reach_step(check_step(s)), ratio=0.30), ratio=0.24)
    ev = run(eng, s.frames())
    assert result_of(ev) is None and eng.sub is Sub.SETUP
    assert any("too alike" in t for t in texts(ev))


@pytest.mark.parametrize("how", ["cancel", "pause", "stop", "loss"])
def test_cancelling_or_interrupting_changes_nothing(how):
    eng, s = start()
    cfg_before = eng.cfg
    reach_step(check_step(s), CORNERS[:2])
    run(eng, s.frames())
    s2 = s.next()
    if how == "cancel":
        s2.cmd(Command.END_SETUP)
    elif how == "pause":
        s2.cmd(Command.PAUSE)
    elif how == "stop":
        s2.cmd(Command.EMERGENCY_STOP)
    else:
        s2.none(ms=4000)
    ev = run(eng, s2.frames())
    assert result_of(ev) == SetupResult("calibration", None)
    assert eng.cfg is cfg_before and eng.session is None


def test_losing_the_hand_mid_step_restarts_that_step():
    eng, s = start()
    check_step(s).move(Pose.G1_RELAXED, to=CORNERS[0], ms=400).hold(Pose.G1_RELAXED, 600)
    s.none(ms=400).hold(Pose.G1_RELAXED, 600, at=CORNERS[0])
    ev = run(eng, s.frames())
    reach = [e for e in ev if isinstance(e, SetupView) and e.step == "reach"]
    assert reach and "top-right" not in " ".join(texts(ev)) and eng.sub is Sub.SETUP


def test_calibration_is_deterministic():
    assert full_run()[2] == full_run()[2]
