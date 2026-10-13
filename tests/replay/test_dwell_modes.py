"""Dwell confirmation in the menu, the Media grid, the level panel, and Pointer Mode (D4)."""

from support.hands import Script, run
from support.menu import cam_pos, resumed

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Action,
    ButtonDown,
    Click,
    Command,
    CueChanged,
    CueKind,
    Level,
    LevelStep,
    Mode,
    ModeChanged,
    MoveCursor,
    Pose,
    Scroll,
    SystemAction,
)

DWELL = CoreConfig(confirm_method="dwell", dwell_ms=500)


def into(mode: str, cfg: CoreConfig = DWELL):
    eng = Engine(cfg)
    s = resumed().hold(Pose.G1_RELAXED, 300)
    if mode != "POINTER":
        s.cmd(Command.SET_MODE, mode).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    return eng, s.next()


def test_the_mode_menu_chooses_by_dwell():
    eng, s = into("POINTER")
    s.hold(Pose.G7_THREE_FINGERS, 1200)
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MODE_MENU_ITEMS, "media"), ms=500)
    s.hold(Pose.G1_RELAXED, 1500)
    ev = run(eng, s.frames())
    assert [e.mode for e in ev if isinstance(e, ModeChanged)] == [Mode.MEDIA]


def test_the_menu_does_not_choose_while_the_hand_is_still_moving():
    eng, s = into("POINTER")
    s.hold(Pose.G7_THREE_FINGERS, 1200)
    for x in (0.3, 0.4, 0.5, 0.6, 0.7):
        s.move(Pose.G1_RELAXED, to=(x, 0.5), ms=300)
    ev = run(eng, s.frames())
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_the_media_grid_runs_a_target_by_dwell_once():
    eng, s = into("MEDIA")
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MEDIA_TARGETS, "play_pause"), ms=500)
    s.hold(Pose.G1_RELAXED, 2500)
    ev = run(eng, s.frames())
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.PLAY_PAUSE]


def test_a_level_target_chosen_by_dwell_keeps_stepping_while_the_point_stays():
    eng, s = into("MEDIA")
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MEDIA_TARGETS, "volume_up"), ms=500)
    s.hold(Pose.G1_RELAXED, 2000)
    ev = run(eng, s.frames())
    steps = [e for e in ev if isinstance(e, LevelStep)]
    assert len(steps) >= 4 and all(e.level is Level.VOLUME and e.delta > 0 for e in steps)
    s2 = s.next().move(Pose.G1_RELAXED, to=(0.5, 0.2), ms=300)
    run(eng, s2.frames())
    s3 = s2.next().hold(Pose.G1_RELAXED, 1500)
    assert not [e for e in run(eng, s3.frames()) if isinstance(e, LevelStep)]


def test_pinch_still_works_when_dwell_is_selected():
    eng, s = into("MEDIA")
    s.move(Pose.G1_RELAXED, to=cam_pos(layout.MEDIA_TARGETS, "mute"), ms=500)
    s.hold(Pose.G1_RELAXED, 200).hold(Pose.G2_PINCH_INDEX, 300).hold(Pose.G1_RELAXED, 200)
    ev = run(eng, s.frames())
    assert [e.action for e in ev if isinstance(e, SystemAction)] == [Action.MUTE]


def test_the_level_panel_steps_with_plus_and_minus_targets_by_dwell():
    eng, s = into("POINTER")
    s.hold(Pose.G9_CALL_ME, 800)
    items = tuple(layout.LEVEL_SLIDERS) + tuple(layout.LEVEL_STEP_TARGETS)
    s.move(Pose.G1_RELAXED, to=cam_pos(items, "brightness_down"), ms=500)
    s.hold(Pose.G1_RELAXED, 1800)
    ev = run(eng, s.frames())
    steps = [e for e in ev if isinstance(e, LevelStep)]
    assert steps and all(e.level is Level.BRIGHTNESS and e.delta < 0 for e in steps)


def test_a_slider_is_never_chosen_by_dwell():
    eng, s = into("POINTER")
    s.hold(Pose.G9_CALL_ME, 800)
    items = tuple(layout.LEVEL_SLIDERS) + tuple(layout.LEVEL_STEP_TARGETS)
    s.move(Pose.G1_RELAXED, to=cam_pos(items, "volume"), ms=500).hold(Pose.G1_RELAXED, 2000)
    assert not [e for e in run(eng, s.frames()) if isinstance(e, LevelStep)]


# -- pointer dwell click ------------------------------------------------------------------------

CLICKING = CoreConfig(pointer_dwell_click=True, dwell_ms=500)


def test_pointer_dwell_click_is_off_by_default():
    eng, s = into("POINTER", CoreConfig())
    ev = run(eng, s.hold(Pose.G1_RELAXED, 3000).frames())
    assert not [e for e in ev if isinstance(e, Click)]


def test_a_still_cursor_clicks_once_and_needs_to_leave_to_click_again():
    eng, s = into("POINTER", CLICKING)
    s.hold(Pose.G1_RELAXED, 2500, at=(0.5, 0.5))
    assert len([e for e in run(eng, s.frames()) if isinstance(e, Click)]) == 1
    s2 = s.next().move(Pose.G1_RELAXED, to=(0.6, 0.5), ms=300).hold(Pose.G1_RELAXED, 1500)
    assert len([e for e in run(eng, s2.frames()) if isinstance(e, Click)]) == 1


def test_a_moving_cursor_never_dwell_clicks():
    eng, s = into("POINTER", CLICKING)
    for x in (0.4, 0.5, 0.6, 0.5, 0.4, 0.5):
        s.move(Pose.G1_RELAXED, to=(x, 0.5), ms=350)
    assert not [e for e in run(eng, s.frames()) if isinstance(e, Click)]


def test_dwell_click_shows_progress_and_a_click_cue():
    eng, s = into("POINTER", CLICKING)
    ev = run(eng, s.hold(Pose.G1_RELAXED, 1500, at=(0.5, 0.5)).frames())
    kinds = [e.kind for e in ev if isinstance(e, CueChanged)]
    assert CueKind.DWELL in kinds and CueKind.CLICK in kinds


def test_no_dwell_click_during_clutch_fist_scroll_or_drag():
    eng, s = into("POINTER", CLICKING)
    s.hold(Pose.G5_FIST, 2000, at=(0.5, 0.5))
    s.hold(Pose.G4_THUMBS_UP, 2500, tilt=0)
    s.hold(Pose.G1_RELAXED, 300).hold(Pose.G2_PINCH_INDEX, 2500)
    ev = run(eng, s.frames())
    assert not [e for e in ev if isinstance(e, Click)]
    assert [e for e in ev if isinstance(e, ButtonDown)]  # the pinch held long enough to drag


def test_the_pinch_click_still_works_with_dwell_click_on():
    eng, s = into("POINTER", CLICKING)
    s.move(Pose.G1_RELAXED, to=(0.7, 0.5), ms=300)  # leave the spot where setup rested
    run(eng, s.frames())
    s2 = s.next().move(Pose.G1_RELAXED, to=(0.45, 0.5), ms=200).hold(Pose.G1_RELAXED, 100)
    s2.hold(Pose.G2_PINCH_INDEX, 150).hold(Pose.G1_RELAXED, 300)
    ev = run(eng, s2.frames())
    assert len([e for e in ev if isinstance(e, Click)]) == 1
    assert not [e for e in ev if isinstance(e, (Scroll,))] and MoveCursor in {type(e) for e in ev}


def test_unused_script_import():
    assert Script
