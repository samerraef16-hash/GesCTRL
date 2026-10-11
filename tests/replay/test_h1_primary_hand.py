"""H1: only one hand ever controls; a second hand never clicks, moves or takes over."""

from support.hands import Script, pose, resume_script, run

from gescrtl.core.engine import Engine
from gescrtl.core.types import Click, HandFrame, MoveCursor, Pose, State

G1, G2, G6 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX, Pose.G6_OPEN_PALM
LEFT, RIGHT = (0.35, 0.5), (0.75, 0.5)


def active(at=LEFT):
    eng = Engine()
    s = resume_script(at=at)
    run(eng, s.frames())
    return eng, s.next()


def moves(events):
    return [(e.nx, e.ny) for e in events if isinstance(e, MoveCursor)]


def test_a_second_hand_pinching_anywhere_never_clicks():
    eng, s = active()
    s.hold(G1, 300, at=LEFT)
    for p in ((0.75, 0.5), (0.7, 0.3), (0.8, 0.7)):
        s.hold(G1, 200, others=[(G2, p)]).hold(G1, 100, others=[(G1, p)])
    s.hold(G1, 300, others=[(Pose.G3_PINCH_MIDDLE, (0.72, 0.55))])
    ev = run(eng, s.frames())
    assert not [e for e in ev if isinstance(e, Click)]


def test_cursor_follows_only_the_primary_hand():
    eng, s = active()
    s.hold(G1, 300, at=LEFT)
    s.move(G1, to=(0.4, 0.5), ms=400, others=[(G1, (0.8, 0.8))])
    xs = [x for x, _ in moves(run(eng, s.frames()))]
    assert xs and max(xs) < 0.5  # the other hand at x=0.8 would have pulled the cursor right


def test_primary_leaving_while_a_second_hand_stays_means_tracking_lost_not_a_swap():
    eng, s = active()
    s.hold(G1, 300, at=LEFT, others=[(G1, RIGHT)])  # the second hand is in view already
    run(eng, s.frames())
    s2 = s.next().others_only([(G1, RIGHT)], 500)
    ev = run(eng, s2.frames())
    assert eng.state is State.TRACKING_LOST
    assert not moves(ev)


def test_on_return_the_hand_nearest_the_last_position_is_chosen():
    eng, s = active()
    s.hold(G1, 300, at=LEFT, others=[(G1, RIGHT)])  # the second hand is in view already
    run(eng, s.frames())
    s2 = s.next().others_only([(G1, RIGHT)], 400)
    run(eng, s2.frames())
    s3 = s2.next().hold(G1, 600, at=(0.4, 0.5), others=[(G1, RIGHT)])
    xs = [x for x, _ in moves(run(eng, s3.frames()))]
    assert eng.state is State.ACTIVE
    assert xs and max(xs) < 0.5


def test_the_hand_that_completed_the_resume_hold_becomes_primary():
    eng = Engine()
    frames = []
    s = Script()
    for _ in range(int(1.4 * 30)):  # palm on the left, a more confident relaxed hand on the right
        palm = pose(G6, LEFT, score=0.85)
        other = pose(G1, RIGHT, score=0.99)
        frames.append(HandFrame(s.t_ns, (other, palm)))
        s.t_ns += s.frame_ns
    for _ in range(30):  # then both just sit there
        palm = pose(G1, LEFT, score=0.85)
        other = pose(G1, RIGHT, score=0.99)
        frames.append(HandFrame(s.t_ns, (other, palm)))
        s.t_ns += s.frame_ns
    ev = run(eng, frames)
    assert eng.state is State.ACTIVE
    xs = [x for x, _ in moves(ev)]
    assert xs and max(xs) < 0.5
