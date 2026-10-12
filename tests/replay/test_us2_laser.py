"""US2: the laser dot shows only while the index finger is raised alone (FR-009)."""

import random

from support.hands import HandFrame, pose, run
from support.presenting import presenting

from gescrtl.core.types import (
    ButtonDown,
    Click,
    Command,
    MoveCursor,
    OverlayPointer,
    OverlayPointerHidden,
    PointerStyle,
    Pose,
    Scroll,
)


def lasers(ev):
    return [e for e in ev if isinstance(e, OverlayPointer)]


def hidden(ev):
    return [e for e in ev if isinstance(e, OverlayPointerHidden)]


def test_the_index_finger_shows_the_laser_and_other_hands_do_not():
    eng, s = presenting()
    ev = run(eng, s.hold(Pose.G10_INDEX_POINT, 600).frames())
    assert lasers(ev) and all(e.style is PointerStyle.LASER for e in lasers(ev))
    for kind in (Pose.G1_RELAXED, Pose.G6_OPEN_PALM):
        eng, s = presenting()
        assert not lasers(run(eng, s.hold(kind, 600).frames()))


def test_a_short_slip_off_the_index_pose_keeps_the_dot_where_it_was():
    eng, s = presenting()
    s.hold(Pose.G10_INDEX_POINT, 600).hold(Pose.G1_RELAXED, 200).hold(Pose.G10_INDEX_POINT, 600)
    ev = run(eng, s.frames())
    assert not hidden(ev)
    pts = [(e.nx, e.ny) for e in lasers(ev)]
    assert (
        max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:], strict=False)) < 0.02
    )


def test_the_dot_is_hidden_after_the_grace_period():
    eng, s = presenting()
    ev = run(eng, s.hold(Pose.G10_INDEX_POINT, 600).hold(Pose.G1_RELAXED, 600).frames())
    assert len(hidden(ev)) == 1


def test_pause_loss_and_a_mode_change_hide_it_at_once():
    for stop in ("pause", "loss", "mode"):
        eng, s = presenting()
        run(eng, s.hold(Pose.G10_INDEX_POINT, 600).frames())
        s = s.next()
        if stop == "pause":
            s.cmd(Command.PAUSE)
        elif stop == "loss":
            s.none(ms=400)
        else:
            s.cmd(Command.SET_MODE, "MEDIA")
        assert len(hidden(run(eng, s.frames()))) == 1, stop


def test_the_laser_never_moves_the_cursor_or_clicks():
    eng, s = presenting()
    s.hold(Pose.G10_INDEX_POINT, 400).move(Pose.G10_INDEX_POINT, to=(0.6, 0.4), ms=600)
    ev = run(eng, s.frames())
    assert not [e for e in ev if isinstance(e, MoveCursor | Click | ButtonDown | Scroll)]


def test_a_resting_hand_with_landmark_noise_keeps_the_dot_within_12_px():
    eng, s = presenting()
    t = s.t_ns
    rng = random.Random(7)
    frames = []
    for i in range(60):  # 2 s at 30 fps
        at = (0.5 + rng.uniform(-0.002, 0.002), 0.5 + rng.uniform(-0.002, 0.002))
        frames.append(HandFrame(t_ns=t + i * 33_333_333, hands=(pose(Pose.G10_INDEX_POINT, at),)))
    pts = [(e.nx * 1920, e.ny * 1080) for e in lasers(run(eng, frames))][15:]
    assert len(pts) > 30
    assert max(p[0] for p in pts) - min(p[0] for p in pts) <= 12
    assert max(p[1] for p in pts) - min(p[1] for p in pts) <= 12
