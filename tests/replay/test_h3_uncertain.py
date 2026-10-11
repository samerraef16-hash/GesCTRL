"""H3: uncertain frames never click, move the cursor wildly, or leave a button held."""

from support.hands import resume_script, run

from gescrtl.core.engine import Engine
from gescrtl.core.types import ButtonDown, Click, MoveCursor, Pose, ReleaseAll

G1, G2 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX
A = (0.45, 0.5)


def active():
    eng = Engine()
    s = resume_script(at=A)
    run(eng, s.frames())
    s = s.next().hold(G1, 300, at=A)
    run(eng, s.frames())
    return eng, s.next()


def test_baseline_a_clean_tap_clicks():
    eng, s = active()
    s.hold(G2, 150).hold(G1, 200)
    assert sum(isinstance(e, Click) for e in run(eng, s.frames())) == 1


def test_low_confidence_inside_a_pinch_onset_means_no_click_until_stable_again():
    eng, s = active()
    s.hold(G2, 60)  # 2 frames: not stable yet
    s.hold(G2, 34, score=0.3)  # 1 uncertain frame restarts the count
    s.hold(G2, 60).hold(G1, 200)  # 2 more frames, then release: never 3 in a row
    assert not [e for e in run(eng, s.frames()) if isinstance(e, Click)]


def test_a_one_frame_anchor_jump_is_rejected_and_the_cursor_holds():
    eng, s = active()
    s.hold(G1, 34, at=(0.75, 0.5))  # one frame far away
    s.hold(G1, 300, at=A)
    xs = [e.nx for e in run(eng, s.frames()) if isinstance(e, MoveCursor)]
    assert xs and max(xs) < 0.6  # the stray frame (x=0.75 -> 0.9) never reached the cursor


def test_lost_confidence_during_a_drag_releases_after_loss_frames():
    eng, s = active()
    s.hold(G2, 500)
    ev = run(eng, s.frames())
    assert any(isinstance(e, ButtonDown) for e in ev)
    ev2 = run(eng, s.next().hold(G2, 200, score=0.3).frames())
    assert any(isinstance(e, ReleaseAll) for e in ev2)


def test_one_or_two_uncertain_frames_do_not_end_a_drag():
    eng, s = active()
    s.hold(G2, 500)
    run(eng, s.frames())
    ev = run(eng, s.next().hold(G2, 67, score=0.3).hold(G2, 300).frames())
    assert not any(isinstance(e, ReleaseAll) for e in ev)
