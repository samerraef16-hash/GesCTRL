"""US4: "call me" opens the volume/brightness panel in every mode (FR-021..FR-024)."""

import pytest
from support.hands import run
from support.menu import active_in, cam_pos, timed_run

from gescrtl.core import layout
from gescrtl.core.types import (
    ButtonDown,
    ButtonUp,
    Click,
    Command,
    Level,
    LevelStep,
    MoveCursor,
    OverlayHidden,
    OverlayKind,
    OverlayShown,
    Pose,
    ReleaseAll,
    Scroll,
    Sub,
    SystemAction,
)

NO_POINTER_INPUT = (MoveCursor, Click, ButtonDown, ButtonUp, Scroll, SystemAction)
HALF_SLIDER_CAM = 0.45 / 2 * 0.6  # half a slider height as camera travel (active region 60 %)


def opened(ev):
    return [e for e in ev if isinstance(e, OverlayShown) and e.kind is OverlayKind.LEVELS]


def panel_script(eng, s, slider="volume", hold_ms=800):
    """Open the panel and rest the hand on ``slider``, ready to pinch."""
    s.hold(Pose.G9_CALL_ME, hold_ms)
    to = cam_pos(layout.LEVEL_SLIDERS, slider)
    s.move(Pose.G1_RELAXED, to=to, ms=500).hold(Pose.G1_RELAXED, 500)
    return s, to


def drag(s, to, dy_cam, ms=2000, settle=1200):
    s.hold(Pose.G2_PINCH_INDEX, 300)
    s.move(Pose.G2_PINCH_INDEX, to=(to[0], to[1] + dy_cam), ms=ms)
    return s.hold(Pose.G2_PINCH_INDEX, settle)


@pytest.mark.parametrize("mode", ["POINTER", "PRESENTATION", "MEDIA"])
def test_call_me_opens_the_panel_in_every_mode(mode):
    eng, s = active_in(mode)
    ev = run(eng, s.hold(Pose.G9_CALL_ME, 800).frames())
    assert opened(ev) and ReleaseAll("level panel") in ev
    assert eng.sub is Sub.LEVEL_PANEL


@pytest.mark.parametrize("mode", ["POINTER", "PRESENTATION", "MEDIA"])
def test_a_shorter_call_me_does_nothing(mode):
    eng, s = active_in(mode)
    ev = run(eng, s.hold(Pose.G9_CALL_ME, 400).hold(Pose.G1_RELAXED, 300).frames())
    assert not opened(ev) and eng.sub is Sub.NORMAL


def test_pinch_and_move_up_half_a_slider_raises_the_volume_by_half_in_bounded_steps():
    eng, s = active_in("POINTER")
    s, to = panel_script(eng, s)
    drag(s, to, -HALF_SLIDER_CAM)
    timed = timed_run(eng, s.frames())
    steps = [(t, e) for t, e in timed if isinstance(e, LevelStep)]
    assert steps and all(e.level is Level.VOLUME and e.delta == 2 for _, e in steps)
    assert 48 <= sum(e.delta for _, e in steps) <= 52
    times = [t for t, _ in steps]
    for i, t in enumerate(times):  # never more than level_max_rate in any second
        in_second = [x for x in times[i:] if x - t < 1_000_000_000]
        assert len(in_second) * 2 <= 40 + 4


def test_moving_down_lowers_the_level_and_releasing_stops_the_change():
    eng, s = active_in("PRESENTATION")
    s, to = panel_script(eng, s)
    drag(s, to, +HALF_SLIDER_CAM / 2)
    timed = timed_run(eng, s.frames())
    down = [e for _, e in timed if isinstance(e, LevelStep)]
    assert down and all(e.delta == -2 for e in down)
    assert -27 <= sum(e.delta for e in down) <= -23
    s2 = s.next().hold(Pose.G1_RELAXED, 300)
    s2.move(Pose.G1_RELAXED, to=(to[0], to[1] - 0.1), ms=600).hold(Pose.G1_RELAXED, 500)
    assert not [e for e in run(eng, s2.frames()) if isinstance(e, LevelStep)]


def test_pinching_the_brightness_slider_changes_brightness():
    eng, s = active_in("MEDIA")
    s, to = panel_script(eng, s, slider="brightness")
    drag(s, to, -0.05)
    steps = [e for e in run(eng, s.frames()) if isinstance(e, LevelStep)]
    assert steps and all(e.level is Level.BRIGHTNESS for e in steps)


def test_a_fist_or_five_idle_seconds_close_the_panel():
    eng, s = active_in("POINTER")
    run(eng, s.hold(Pose.G9_CALL_ME, 800).frames())
    ev = run(eng, s.next().hold(Pose.G5_FIST, 600).frames())
    assert eng.sub is Sub.NORMAL and any(isinstance(e, OverlayHidden) for e in ev)
    eng, s = active_in("POINTER")
    run(eng, s.hold(Pose.G9_CALL_ME, 800).frames())
    ev = run(eng, s.next().hold(Pose.G1_RELAXED, 5600).frames())
    assert eng.sub is Sub.NORMAL and any(isinstance(e, OverlayHidden) for e in ev)


@pytest.mark.parametrize("how", ["loss", "pause", "g7", "emergency"])
def test_loss_pause_three_fingers_and_emergency_stop_close_it(how):
    eng, s = active_in("POINTER")
    run(eng, s.hold(Pose.G9_CALL_ME, 800).frames())
    s2 = s.next()
    if how == "loss":
        s2.none(ms=400)
    elif how == "pause":
        s2.cmd(Command.PAUSE)
    elif how == "g7":
        s2.hold(Pose.G7_THREE_FINGERS, 400)
    else:
        s2.cmd(Command.EMERGENCY_STOP)
    ev = run(eng, s2.frames())
    assert eng.sub is not Sub.LEVEL_PANEL and any(isinstance(e, OverlayHidden) for e in ev)


def test_nothing_reaches_the_pointer_or_the_system_while_the_panel_is_open():
    eng, s = active_in("POINTER")
    s, to = panel_script(eng, s)
    drag(s, to, -0.05)
    ev = run(eng, s.frames())
    ev = ev[ev.index(opened(ev)[0]) :]  # call-me moves the cursor until the panel opens
    assert not [e for e in ev if isinstance(e, NO_POINTER_INPUT)]


def test_call_me_during_a_scroll_is_ignored():
    eng, s = active_in("POINTER")
    s.hold(Pose.G4_THUMBS_UP, 700, tilt=60)
    s.hold(Pose.G9_CALL_ME, 1200, tilt=60)
    ev = run(eng, s.frames())
    assert not opened(ev) and eng.sub is Sub.NORMAL


def test_a_loosely_curled_pinky_scroll_never_opens_the_panel():
    eng, s = active_in("POINTER")
    s.hold(Pose.G4_THUMBS_UP, 2000, tilt=60, pinky_curl=1.10)
    assert not opened(run(eng, s.frames()))
