"""US1: the cursor follows the palm across the whole screen (FR-009, plan D4)."""

from support.hands import Script, run
from support.registry import scenario

from gescrtl.core.engine import Engine
from gescrtl.core.types import Command, MoveCursor, Pose


def resumed_engine():
    eng = Engine()
    s = Script().hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
    run(eng, s.frames())
    return eng, s


def moves(events):
    return [e for e in events if isinstance(e, MoveCursor)]


@scenario("move_corners")
def corners_script():
    s = Script().hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
    for corner in [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8), (0.5, 0.5)]:
        s.move(Pose.G1_RELAXED, to=corner, ms=1500).hold(Pose.G1_RELAXED, 1500)
    return s.frames()


def test_cursor_reaches_every_corner_and_center():
    ev = moves(run(Engine(), corners_script()))
    pts = [(m.nx, m.ny) for m in ev]
    for cx, cy in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]:
        assert any(abs(x - cx) < 0.05 and abs(y - cy) < 0.05 for x, y in pts), (cx, cy)
    assert 0.45 < ev[-1].nx < 0.55 and 0.45 < ev[-1].ny < 0.55


def test_hand_outside_region_clamps_without_jumping():
    eng, s = resumed_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 600, at=(0.5, 0.5))
    s2.move(Pose.G1_RELAXED, to=(0.97, 0.5), ms=900).hold(Pose.G1_RELAXED, 900)
    ev = moves(run(eng, s2.frames()))
    assert max(m.nx for m in ev) == 1.0
    xs = [m.nx for m in ev]
    assert max(abs(b - a) for a, b in zip(xs, xs[1:], strict=False)) < 0.2


def test_movement_is_smooth():
    eng, s = resumed_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300, at=(0.4, 0.5))
    s2.move(Pose.G1_RELAXED, to=(0.6, 0.5), ms=800)
    xs = [m.nx for m in moves(run(eng, s2.frames()))]
    assert max(abs(b - a) for a, b in zip(xs, xs[1:], strict=False)) < 0.2


def test_no_cursor_events_while_paused():
    s = Script().hold(Pose.G1_RELAXED, 2000, at=(0.5, 0.5)).move(Pose.G1_RELAXED, (0.7, 0.7), 500)
    assert not moves(run(Engine(), s.frames()))


def test_no_cursor_events_after_pause_command():
    eng, s = resumed_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).cmd(Command.PAUSE)
    run(eng, s2.frames())
    s3 = Script(t0_ns=s2.t_ns).hold(Pose.G1_RELAXED, 600, at=(0.6, 0.6))
    assert not moves(run(eng, s3.frames()))


def test_index_point_moves_the_cursor_like_a_relaxed_hand():
    """G10 (index finger alone) is the presentation pointer pose; in Pointer Mode it just points."""
    eng, s = resumed_engine()
    s2 = Script(t0_ns=s.t_ns).hold(Pose.G10_INDEX_POINT, 300, at=(0.4, 0.5))
    s2.move(Pose.G10_INDEX_POINT, to=(0.6, 0.5), ms=800)
    ev = moves(run(eng, s2.frames()))
    assert ev and ev[-1].nx > 0.55  # the hand ended at 0.6, which maps to about 0.67
    assert min(m.nx for m in ev) < 0.5  # and it did start on the left
