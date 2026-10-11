"""US3: a fist with the thumb out scrolls like a held scroll wheel (FR-014, plan D6).

Thumb tilt away from where the pose started sets the speed; up scrolls up, down scrolls down.
"""

from support.hands import Script, pose, resume_script, run
from support.registry import scenario

from gescrtl.core import features
from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    DEFAULT_ASPECT,
    Command,
    CueChanged,
    CueKind,
    MoveCursor,
    Pose,
    ReleaseAll,
    Scroll,
)

CFG = CoreConfig()
G4 = Pose.G4_THUMBS_UP


def active(fps: int = 30):
    eng = Engine()
    s = resume_script(fps=fps)
    run(eng, s.frames())
    s2 = s.next().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s2.frames())
    return eng, s2.next()


def engage(s: Script, start_tilt: float = 0.0) -> Script:
    """Form the scroll pose and let it settle (the start angle is taken here)."""
    return s.hold(G4, 500, tilt=start_tilt)


def deltas(events):
    return [e.delta for e in events if isinstance(e, Scroll)]


def total_for_tilt(tilt: float, fps: int = 30, ms: int = 1000) -> int:
    eng, s = active(fps)
    run(eng, engage(s).frames())
    s2 = s.next().ramp_tilt(G4, tilt, 200).hold(G4, ms)
    return sum(deltas(run(eng, s2.frames())))


@scenario("thumb_scroll")
def scroll_scenario():
    s = resume_script().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    engage(s).ramp_tilt(G4, 35, 300).hold(G4, 600).ramp_tilt(G4, -35, 500).hold(G4, 600)
    s.hold(Pose.G1_RELAXED, 300)
    return s.frames()


def test_neutral_thumb_does_not_scroll():
    eng, s = active()
    engage(s).hold(G4, 2000)
    assert not deltas(run(eng, s.frames()))


def test_thumb_up_scrolls_up_and_thumb_down_scrolls_down():
    up, down = total_for_tilt(30), total_for_tilt(-30)
    assert up > 400 and down < -400  # wheel positive = up
    assert abs(up + down) < 0.15 * up  # symmetric


def test_more_tilt_scrolls_faster():
    totals = [total_for_tilt(t) for t in (15, 25, 35, 45)]
    assert totals == sorted(totals) and len(set(totals)) == 4
    assert totals[0] > 0


def test_inside_the_dead_zone_nothing_happens():
    assert total_for_tilt(CFG.scroll_deadzone_deg - 2) == 0


def test_speed_is_capped_beyond_full_tilt():
    a, b = total_for_tilt(60), total_for_tilt(89)
    assert abs(a - b) < 0.1 * a  # past full tilt, tilting more changes nothing
    assert b <= CFG.scroll_max_rate * 1.2 * 1.05  # 1.2 s at the maximum rate
    assert b > CFG.scroll_max_rate * 0.8


def test_neutral_is_where_the_pose_started():
    eng, s = active()
    engage(s, start_tilt=30).hold(G4, 1500)  # pose formed already tilted: that is zero
    assert not deltas(run(eng, s.frames()))
    s2 = s.next().ramp_tilt(G4, 60, 300).hold(G4, 800)
    assert sum(deltas(run(eng, s2.frames()))) > 300


def test_classic_vertical_thumbs_up_does_not_run_away():
    eng, s = active()
    engage(s, start_tilt=85).hold(G4, 2000)
    assert not deltas(run(eng, s.frames()))


def test_no_scrolling_while_the_pose_is_still_settling():
    eng, s = active()
    s.hold(G4, 200, tilt=0).ramp_tilt(G4, 40, 100)  # thumb still moving into place
    assert not deltas(run(eng, s.frames()))


def test_speed_does_not_depend_on_frame_rate():
    t30, t60 = total_for_tilt(30, fps=30), total_for_tilt(30, fps=60)
    assert t30 > 0 and abs(t30 - t60) < 0.15 * t30


def test_scroll_events_are_whole_steps():
    eng, s = active()
    engage(s).ramp_tilt(G4, 40, 300).hold(G4, 500)
    assert all(d % CFG.scroll_step == 0 for d in deltas(run(eng, s.frames())))


def test_cursor_does_not_move_while_scrolling():
    eng, s = active()
    engage(s).ramp_tilt(G4, 35, 300).hold(G4, 500)
    ev = run(eng, s.frames())
    first = next(
        k for k, e in enumerate(ev) if isinstance(e, CueChanged) and e.kind is CueKind.SCROLL
    )
    assert not any(isinstance(e, MoveCursor) for e in ev[first:])


def test_cue_shows_direction_and_strength():
    eng, s = active()
    engage(s).ramp_tilt(G4, 40, 300).hold(G4, 500)
    cues = [e.progress for e in run(eng, s.frames()) if isinstance(e, CueChanged)]
    assert cues and max(cues) > 0.3
    eng2, s2 = active()
    engage(s2).ramp_tilt(G4, -40, 300).hold(G4, 500)
    assert min(e.progress for e in run(eng2, s2.frames()) if isinstance(e, CueChanged)) < -0.3


def test_scrolling_stops_when_the_pose_ends():
    eng, s = active()
    engage(s).ramp_tilt(G4, 40, 300).hold(G4, 500)
    run(eng, s.frames())
    s2 = s.next().hold(Pose.G1_RELAXED, 1000)
    assert not deltas(run(eng, s2.frames()))


def test_pause_stops_scrolling_at_once():
    eng, s = active()
    engage(s).ramp_tilt(G4, 40, 300).hold(G4, 300)
    run(eng, s.frames())
    s2 = s.next().cmd(Command.PAUSE).hold(G4, 1000)
    ev = run(eng, s2.frames())
    assert any(isinstance(e, ReleaseAll) for e in ev) and not deltas(ev)


def test_hand_loss_stops_scrolling():
    eng, s = active()
    engage(s).ramp_tilt(G4, 40, 300).hold(G4, 300)
    run(eng, s.frames())
    s2 = s.next().none(6).hold(G4, 300)
    assert not deltas(run(eng, s2.frames()))


def test_low_confidence_does_not_scroll():
    eng, s = active()
    s.hold(G4, 500, score=0.3).hold(G4, 1000, score=0.3, tilt=40)
    assert not deltas(run(eng, s.frames()))


def test_tilt_is_measured_the_same_for_a_thumb_pointing_either_way():
    for tilt in (-30.0, 0.0, 30.0):
        for right in (False, True):
            hand = pose(G4, thumb_tilt_deg=tilt, thumb_right=right)
            f = features.compute(hand, DEFAULT_ASPECT)
            assert f is not None and abs(f.thumb_tilt_deg - tilt) < 0.5
