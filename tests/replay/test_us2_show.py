"""US2: thumbs-up held 1 s starts the show, thumbs-down ends it (FR-010)."""

from support.hands import run
from support.presenting import actions, presenting

from gescrtl.core.types import Action, Pose


def g4(s, ms, tilt):
    return s.hold(Pose.G4_THUMBS_UP, ms, tilt=tilt)


def test_thumbs_up_held_one_second_starts_once_even_when_held_longer():
    eng, s = presenting()
    assert actions(run(eng, g4(s, 3000, 70).frames())) == [Action.SHOW_START]


def test_a_shorter_hold_does_nothing():
    eng, s = presenting()
    assert actions(run(eng, g4(s, 700, 70).frames())) == []


def test_thumbs_down_ends_the_show_and_a_level_thumb_does_nothing():
    eng, s = presenting()
    assert actions(run(eng, g4(s, 1500, -70).frames())) == [Action.SHOW_END]
    eng, s = presenting()
    assert actions(run(eng, g4(s, 2000, 20).frames())) == []


def test_firing_again_needs_another_pose_and_the_cooldown():
    eng, s = presenting()
    g4(s, 1300, 70).hold(Pose.G1_RELAXED, 200)
    g4(s, 1300, 70)  # the cooldown (2 s) has not passed: swallowed, and not fired late
    g4(s, 1500, 70).hold(Pose.G1_RELAXED, 3000)
    g4(s, 1300, 70)
    assert actions(run(eng, s.frames())) == [Action.SHOW_START, Action.SHOW_START]


def test_a_tilt_that_reached_the_enter_angle_stays_up_above_the_exit_angle():
    eng, s = presenting()
    g4(s, 300, 55)
    g4(s, 1100, 45)
    assert actions(run(eng, s.frames())) == [Action.SHOW_START]


def test_a_tilt_that_never_reaches_the_enter_angle_never_fires():
    eng, s = presenting()
    assert actions(run(eng, g4(s, 3000, 49).frames())) == []


def test_dipping_below_the_exit_angle_restarts_the_timer():
    eng, s = presenting()
    g4(s, 700, 55)
    g4(s, 150, 30)
    g4(s, 700, 55)
    assert actions(run(eng, s.frames())) == []
