"""US3: Media/System Mode runs the pointed target once per stable pinch (FR-012..FR-016)."""

import pytest
from support.hands import run
from support.menu import active_in, cam_pos

from gescrtl.core import layout
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Action,
    Command,
    Level,
    LevelStep,
    MoveCursor,
    OverlayKind,
    OverlayShown,
    Pose,
    ReleaseAll,
    SystemAction,
)


def actions(ev):
    return [e.action for e in ev if isinstance(e, SystemAction)]


def steps(ev):
    return [e for e in ev if isinstance(e, LevelStep)]


def pending(ev):
    return [e.pending for e in ev if isinstance(e, OverlayShown) and e.kind is OverlayKind.MEDIA]


def point(s, ident, ms=500, dx=0.0, dy=0.0):
    to = cam_pos(layout.MEDIA_TARGETS, ident, dx, dy)
    return s.move(Pose.G1_RELAXED, to=to, ms=ms).hold(Pose.G1_RELAXED, 500), to


def pinch(s, ms=400, rest=500):
    return s.hold(Pose.G2_PINCH_INDEX, ms).hold(Pose.G1_RELAXED, rest)


def test_entering_media_mode_shows_the_grid():
    from support.menu import resumed

    eng = Engine()
    s = resumed().hold(Pose.G1_RELAXED, 300).cmd(Command.SET_MODE, "MEDIA")
    ev = run(eng, s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).frames())
    shown = [e for e in ev if isinstance(e, OverlayShown) and e.kind is OverlayKind.MEDIA]
    assert shown


@pytest.mark.parametrize(
    ("ident", "action"),
    [
        ("play_pause", Action.PLAY_PAUSE),
        ("prev_track", Action.PREV_TRACK),
        ("next_track", Action.NEXT_TRACK),
        ("mute", Action.MUTE),
    ],
)
def test_a_pinch_on_a_one_shot_target_sends_exactly_one_action(ident, action):
    eng, s = active_in("MEDIA")
    point(s, ident)
    pinch(s, ms=800)  # a long pinch still fires once
    assert actions(run(eng, s.frames())) == [action]


@pytest.mark.parametrize(
    ("ident", "level", "delta"),
    [("volume_up", Level.VOLUME, 2), ("brightness_down", Level.BRIGHTNESS, -2)],
)
def test_a_held_pinch_on_a_level_target_repeats_about_every_150_ms(ident, level, delta):
    eng, s = active_in("MEDIA")
    point(s, ident)
    s.hold(Pose.G2_PINCH_INDEX, 1000).hold(Pose.G1_RELAXED, 500)
    got = steps(run(eng, s.frames()))
    assert 5 <= len(got) <= 8 and all(e.level is level and e.delta == delta for e in got)


def test_sliding_off_the_target_stops_the_repeats():
    eng, s = active_in("MEDIA")
    point(s, "volume_up")
    s.hold(Pose.G2_PINCH_INDEX, 300)
    first = len(steps(run(eng, s.frames())))
    s2 = s.next()
    to = cam_pos(layout.MEDIA_TARGETS, "volume_down")
    s2.move(Pose.G2_PINCH_INDEX, to=to, ms=400).hold(Pose.G2_PINCH_INDEX, 1000)
    ev = run(eng, s2.frames())
    assert first >= 1
    assert len(steps(ev)) <= 2  # at most what was already due while sliding away
    assert all(e.level is Level.VOLUME and e.delta == 2 for e in steps(ev))


@pytest.mark.parametrize(
    ("ident", "action"),
    [("screenshot", Action.SCREENSHOT), ("app_switch", Action.APP_SWITCH)],
)
class TestConfirmedTargets:
    def first(self, ident):
        eng, s = active_in("MEDIA")
        point(s, ident)
        pinch(s)
        return eng, s

    def test_one_pinch_only_asks_and_a_second_confirms(self, ident, action):
        eng, s = self.first(ident)
        ev = run(eng, s.frames())
        assert actions(ev) == [] and ident in pending(ev)
        ev = run(eng, pinch(s.next()).frames())
        assert actions(ev) == [action] and pending(ev)[-1] == ""

    def test_a_fist_cancels_it(self, ident, action):
        eng, s = self.first(ident)
        run(eng, s.frames())
        s2 = s.next().hold(Pose.G5_FIST, 500).hold(Pose.G1_RELAXED, 500)
        run(eng, s2.frames())
        ev = run(eng, pinch(s2.next()).frames())
        assert actions(ev) == [] and ident in pending(ev)

    def test_it_expires_after_three_seconds(self, ident, action):
        eng, s = self.first(ident)
        run(eng, s.frames())
        s2 = s.next().hold(Pose.G1_RELAXED, 3300)
        run(eng, s2.frames())
        ev = run(eng, pinch(s2.next()).frames())
        assert actions(ev) == [] and ident in pending(ev)

    def test_pinching_another_target_cancels_it(self, ident, action):
        eng, s = self.first(ident)
        run(eng, s.frames())
        s2 = s.next()
        point(s2, "next_track")
        pinch(s2)
        ev = run(eng, s2.frames())
        assert actions(ev) == [Action.NEXT_TRACK]
        s3 = s2.next()
        point(s3, ident)
        pinch(s3)
        ev = run(eng, s3.frames())
        assert actions(ev) == [] and ident in pending(ev)  # asks again instead of running


def test_pinching_in_a_gap_or_outside_the_grid_does_nothing():
    eng, s = active_in("MEDIA")
    point(s, "play_pause", dx=0.09)  # centre of the gap to the next target
    pinch(s)
    s.move(Pose.G1_RELAXED, to=(0.5, 0.2), ms=400).hold(Pose.G1_RELAXED, 400)
    pinch(s)
    ev = run(eng, s.frames())
    assert actions(ev) == [] and steps(ev) == []


def test_a_second_pinch_inside_the_cooldown_does_not_fire_again():
    eng, s = active_in("MEDIA")
    point(s, "play_pause")
    s.hold(Pose.G2_PINCH_INDEX, 200).hold(Pose.G1_RELAXED, 100).hold(Pose.G2_PINCH_INDEX, 300)
    s.hold(Pose.G1_RELAXED, 500)
    assert actions(run(eng, s.frames())) == [Action.PLAY_PAUSE]


def test_the_media_grid_never_moves_the_cursor():
    eng, s = active_in("MEDIA")
    point(s, "mute")
    pinch(s)
    assert not [e for e in run(eng, s.frames()) if isinstance(e, MoveCursor)]


@pytest.mark.parametrize("how", ["loss", "pause", "mode"])
def test_loss_pause_or_a_mode_change_clear_the_pending_confirmation_and_held_input(how):
    eng, s = active_in("MEDIA")
    point(s, "screenshot")
    pinch(s)
    run(eng, s.frames())
    s2 = s.next()
    if how == "loss":
        s2.none(ms=500).hold(Pose.G1_RELAXED, 400)
    elif how == "pause":
        s2.cmd(Command.PAUSE).wait(300).hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5))
        s2.hold(Pose.G1_RELAXED, 300)
    else:
        s2.cmd(Command.SET_MODE, "POINTER").cmd(Command.SET_MODE, "MEDIA")
        s2.hold(Pose.G1_RELAXED, 400)
    ev = run(eng, s2.frames())
    assert ReleaseAll in {type(e) for e in ev}
    s3 = s2.next()
    point(s3, "screenshot")
    pinch(s3)
    ev = run(eng, s3.frames())
    assert actions(ev) == [] and "screenshot" in pending(ev)  # asked again, nothing was left over


def test_pausing_while_a_level_is_repeating_stops_it():
    eng, s = active_in("MEDIA")
    point(s, "volume_up")
    s.hold(Pose.G2_PINCH_INDEX, 400)
    run(eng, s.frames())
    s2 = s.next().cmd(Command.PAUSE).hold(Pose.G2_PINCH_INDEX, 1000)
    ev = run(eng, s2.frames())
    assert ReleaseAll("pause") in ev and not steps(ev)
