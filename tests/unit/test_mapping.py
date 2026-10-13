"""Remapping: slots, allowed actions, and the effect in Presentation and Media (spec 004 D6)."""

import pytest
from support.hands import run
from support.menu import cam_pos
from support.presenting import actions, swipe

from gescrtl.core import layout, mapping
from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Action,
    Command,
    HintsShown,
    LevelStep,
    Mode,
    ModeChanged,
    OverlayKind,
    OverlayShown,
    Pose,
    ReleaseAll,
    SystemAction,
)


def test_defaults_are_the_spec_003_behaviour():
    assert mapping.resolve((), "presentation.swipe_right") == "SLIDE_NEXT"
    assert mapping.resolve((), "presentation.thumb_down") == "SHOW_END"
    ids = [i for i, _ in layout.MEDIA_TARGETS]
    assert set(ids) == set(mapping.MEDIA_TARGET_IDS)
    assert [mapping.resolve((), f"media.t{i}") for i in range(10)][:3] == [
        "PLAY_PAUSE",
        "PREV_TRACK",
        "NEXT_TRACK",
    ]


def test_an_override_replaces_the_default_for_that_slot_only():
    m = (("media.t5", "COPY"),)
    assert mapping.resolve(m, "media.t5") == "COPY"
    assert mapping.resolve(m, "media.t4") == "VOLUME_UP"


def test_safety_actions_cannot_be_assigned():
    for name in (
        "CLICK",
        "LEFT_CLICK",
        "RIGHT_CLICK",
        "PAUSE",
        "RESUME",
        "EMERGENCY_STOP",
        "MODE_MENU",
        "LEVEL_PANEL",
        "TURN_OFF",
        "pause",
    ):
        assert not mapping.is_allowed(name), name
        assert mapping.validate("media.t0", name)
    assert mapping.resolve((("media.t0", "PAUSE"),), "media.t0") == "PLAY_PAUSE"


def test_unknown_slots_are_rejected():
    assert mapping.validate("pointer.click", "COPY")
    assert mapping.validate("media.t0", "COPY") is None
    assert mapping.validate("media.t10", "COPY")


def test_every_allowed_action_has_a_label():
    for name in mapping.ALLOWED:
        assert mapping.label(name)


def test_grid_labels_follow_the_mapping():
    labels = dict(mapping.grid_labels((("media.t0", "COPY"),)))
    assert labels["play_pause"] == "Copy" and labels["mute"] == "Mute"


def presenting_with(mappings):
    from support.hands import Script
    from support.menu import resumed

    eng = Engine(CoreConfig(mappings=tuple(mappings)))
    s = resumed().hold(Pose.G1_RELAXED, 300).cmd(Command.SET_MODE, "PRESENTATION")
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    assert isinstance(s, Script)
    return eng, s.next()


def test_a_remapped_swipe_sends_its_new_action():
    eng, s = presenting_with([("presentation.swipe_right", "MUTE")])
    ev = run(eng, swipe(s, 0.3, 0.7).hold(Pose.G6_OPEN_PALM, 600).frames())
    assert actions(ev) == [Action.MUTE]


def test_the_other_swipe_keeps_its_default():
    eng, s = presenting_with([("presentation.swipe_right", "MUTE")])
    ev = run(eng, swipe(s, 0.7, 0.3).hold(Pose.G6_OPEN_PALM, 600).frames())
    assert actions(ev) == [Action.SLIDE_PREV]


def test_a_swipe_can_be_assigned_a_level_step():
    eng, s = presenting_with([("presentation.swipe_left", "VOLUME_DOWN")])
    ev = run(eng, swipe(s, 0.7, 0.3).hold(Pose.G6_OPEN_PALM, 600).frames())
    assert [e for e in ev if isinstance(e, LevelStep)] and not actions(ev)


def test_a_remapped_thumb_can_change_the_mode_through_the_tray_path():
    eng, s = presenting_with([("presentation.thumb_up", "MODE_MEDIA")])
    ev = run(eng, s.hold(Pose.G4_THUMBS_UP, 1500, tilt=70).frames())
    assert eng.sm.mode is Mode.MEDIA
    assert ModeChanged(Mode.MEDIA) in ev and ReleaseAll("mode change") in ev
    assert any(isinstance(e, HintsShown) for e in ev)
    assert not actions(ev)


@pytest.mark.parametrize("target", ["play_pause", "screenshot"])
def test_a_remapped_grid_target_runs_its_new_action(target):
    index = mapping.MEDIA_TARGET_IDS.index(target)
    eng = Engine(CoreConfig(mappings=((f"media.t{index}", "COPY"),)))
    from support.menu import resumed

    s = resumed().hold(Pose.G1_RELAXED, 300).cmd(Command.SET_MODE, "MEDIA")
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MEDIA_TARGETS, target), ms=500)
    s.hold(Pose.G1_RELAXED, 500).hold(Pose.G2_PINCH_INDEX, 400).hold(Pose.G1_RELAXED, 400)
    ev = run(eng, s.frames())
    assert actions(ev) == [Action.COPY]  # no second confirmation: COPY is not a confirmed action
    shown = [e for e in ev if isinstance(e, OverlayShown) and e.kind is OverlayKind.MEDIA]
    assert dict(shown[0].labels)[target] == "Copy"


def test_a_confirmed_action_keeps_its_double_confirmation_wherever_it_is_mapped():
    eng = Engine(CoreConfig(mappings=(("media.t0", "SCREENSHOT"),)))
    from support.menu import resumed

    s = resumed().hold(Pose.G1_RELAXED, 300).cmd(Command.SET_MODE, "MEDIA")
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MEDIA_TARGETS, "play_pause"), ms=500)
    s.hold(Pose.G1_RELAXED, 500).hold(Pose.G2_PINCH_INDEX, 400).hold(Pose.G1_RELAXED, 600)
    assert actions(run(eng, s.frames())) == []  # one pinch only waits for the second
    s2 = s.next().hold(Pose.G2_PINCH_INDEX, 400).hold(Pose.G1_RELAXED, 300)
    assert actions(run(eng, s2.frames())) == [Action.SCREENSHOT]


def test_system_action_is_still_a_plain_event():
    assert SystemAction(Action.COPY) == mapping.events_for("COPY", 2)[0]
