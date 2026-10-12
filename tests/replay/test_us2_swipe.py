"""US2: an open-hand swipe changes slides, and nothing else does (FR-008)."""

from support.hands import HandFrame, pose, run
from support.presenting import actions, presenting, swipe

from gescrtl.core.types import Action, CueChanged, CueKind, Pose, State


def test_a_fast_move_right_is_next_and_left_is_previous():
    eng, s = presenting()
    ev = run(eng, swipe(s, 0.35, 0.65).hold(Pose.G6_OPEN_PALM, 600).frames())
    assert actions(ev) == [Action.SLIDE_NEXT]
    eng, s = presenting()
    ev = run(eng, swipe(s, 0.65, 0.35).hold(Pose.G6_OPEN_PALM, 600).frames())
    assert actions(ev) == [Action.SLIDE_PREV]


def test_too_slow_too_short_or_diagonal_does_nothing():
    for x1, ms, y1 in ((0.65, 1500, 0.5), (0.45, 250, 0.5), (0.65, 250, 0.8)):
        eng, s = presenting()
        s = swipe(s, 0.35, 0.35)  # settle
        s.move(Pose.G6_OPEN_PALM, to=(x1, y1), ms=ms).hold(Pose.G6_OPEN_PALM, 600)
        assert actions(run(eng, s.frames())) == [], (x1, ms, y1)


def test_an_immediate_return_stroke_does_nothing():
    eng, s = presenting()
    s = swipe(s, 0.35, 0.65).move(Pose.G6_OPEN_PALM, to=(0.35, 0.5), ms=250)
    ev = run(eng, s.hold(Pose.G6_OPEN_PALM, 800).frames())
    assert actions(ev) == [Action.SLIDE_NEXT]


def test_a_second_swipe_within_the_cooldown_needs_the_hand_to_slow_down_first():
    eng, s = presenting()
    s = swipe(s, 0.2, 0.5).move(Pose.G6_OPEN_PALM, to=(0.8, 0.5), ms=250)  # continuous
    assert actions(run(eng, s.hold(Pose.G6_OPEN_PALM, 800).frames())) == [Action.SLIDE_NEXT]


def test_after_rearming_the_next_swipe_fires():
    eng, s = presenting()
    s = swipe(s, 0.2, 0.5).hold(Pose.G6_OPEN_PALM, 700)
    s.move(Pose.G6_OPEN_PALM, to=(0.2, 0.5), ms=2000).hold(Pose.G6_OPEN_PALM, 700)  # slow return
    s.move(Pose.G6_OPEN_PALM, to=(0.5, 0.5), ms=250).hold(Pose.G6_OPEN_PALM, 600)
    assert actions(run(eng, s.frames())) == [Action.SLIDE_NEXT, Action.SLIDE_NEXT]


def test_the_same_swipe_at_ten_fps_fires_exactly_once():
    eng, s = presenting(fps=10)
    s = swipe(s, 0.3, 0.7, ms=400, settle_ms=800).hold(Pose.G6_OPEN_PALM, 1000)
    assert actions(run(eng, s.frames())) == [Action.SLIDE_NEXT]


def test_a_dropped_frame_in_the_middle_cancels_the_swipe():
    eng, s = presenting()
    s = swipe(s, 0.35, 0.5, ms=125)
    s.none(1).move(Pose.G6_OPEN_PALM, to=(0.65, 0.5), ms=125).hold(Pose.G6_OPEN_PALM, 600)
    assert actions(run(eng, s.frames())) == []


def test_a_fast_index_point_move_is_not_a_swipe():
    eng, s = presenting()
    s = swipe(s, 0.35, 0.65, kind=Pose.G10_INDEX_POINT).hold(Pose.G10_INDEX_POINT, 600)
    assert actions(run(eng, s.frames())) == []


def test_a_flat_hand_swipe_while_clutched_fires_without_pausing():
    eng, s = presenting()
    s = swipe(s, 0.35, 0.65, kind=Pose.G8_FLAT_HAND, settle_ms=700)
    ev = run(eng, s.hold(Pose.G8_FLAT_HAND, 400).frames())
    assert actions(ev) == [Action.SLIDE_NEXT]
    assert eng.state is State.ACTIVE


def test_a_flat_hand_held_still_still_pauses_and_shows_no_cursor_cue():
    eng, s = presenting()
    ev = run(eng, s.hold(Pose.G8_FLAT_HAND, 2000, at=(0.5, 0.5)).frames())
    assert eng.state is State.PAUSED
    assert not [e for e in ev if isinstance(e, CueChanged) and e.kind is CueKind.CLUTCH]


def test_a_second_hand_swiping_never_fires():
    eng, s = presenting()
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    t = s.t_ns
    frames = []
    for i in range(40):  # the primary hand rests, another hand sweeps across the frame
        x = 0.2 + 0.6 * min(i, 8) / 8
        hands = (pose(Pose.G6_OPEN_PALM, (0.5, 0.5)), pose(Pose.G6_OPEN_PALM, (x, 0.5), scale=0.1))
        frames.append(HandFrame(t_ns=t + i * 33_333_333, hands=hands))
    assert actions(run(eng, frames)) == []
