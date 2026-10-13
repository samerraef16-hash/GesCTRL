"""US1: one current mode, kept through Paused / Tracking Lost, shown in the indicator (FR-004/5)."""

from support.hands import resume_script, run
from support.menu import open_menu, pinch, point_at

from gescrtl.core.engine import Engine
from gescrtl.core.state_machine import MODE_HINTS
from gescrtl.core.types import (
    Command,
    HintsShown,
    Mode,
    Pose,
    State,
    StateChanged,
    Sub,
)


def states(events):
    return [(e.state, e.sub, e.hud_text) for e in events if isinstance(e, StateChanged)]


def hints(events):
    return [e.items for e in events if isinstance(e, HintsShown)]


def engine_in(mode: Mode):
    """An Active engine in ``mode``, plus the script that got it there."""
    eng = Engine()
    s = resume_script()
    run(eng, s.frames())
    s2 = s.next().cmd(Command.SET_MODE, mode.name).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s2.frames())
    assert eng.sm.mode is mode
    return eng, s2


def test_every_launch_starts_in_pointer_mode():
    assert Engine().sm.mode is Mode.POINTER
    eng, _ = engine_in(Mode.MEDIA)
    assert Engine().sm.mode is Mode.POINTER  # a new engine does not inherit it
    del eng


def test_the_mode_survives_pause_and_resume():
    eng, s = engine_in(Mode.PRESENTATION)
    s2 = s.next().cmd(Command.PAUSE).wait(200)
    run(eng, s2.frames())
    assert eng.state is State.PAUSED and eng.sm.mode is Mode.PRESENTATION
    ev = run(eng, s2.next().hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).frames())
    assert (State.ACTIVE, Sub.NORMAL, "Presentation") in states(ev)


def test_resume_shows_only_the_hints_of_the_current_mode():
    eng, s = engine_in(Mode.PRESENTATION)
    s2 = s.next().cmd(Command.PAUSE).wait(200).hold(Pose.G5_FIST, 600)
    run(eng, s2.frames())
    ev = run(eng, s2.next().hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).frames())
    assert hints(ev) == [MODE_HINTS[Mode.PRESENTATION]]
    pause_line = "Flat hand 1.5 s: pause"  # the one hint every mode shares
    other = {h for m, items in MODE_HINTS.items() if m is not Mode.PRESENTATION for h in items}
    assert not (other - {pause_line}) & set(hints(ev)[0])


def test_every_mode_has_one_to_four_hints():
    for mode in (Mode.POINTER, Mode.PRESENTATION, Mode.MEDIA, Mode.KEYBOARD):
        assert 1 <= len(MODE_HINTS[mode]) <= 4


def test_the_mode_survives_hand_loss_and_comes_back_without_hints():
    eng, s = engine_in(Mode.MEDIA)
    s2 = s.next().none(ms=400)
    run(eng, s2.frames())
    assert eng.state is State.TRACKING_LOST and eng.sm.mode is Mode.MEDIA
    ev = run(eng, s2.next().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).frames())
    assert (State.ACTIVE, Sub.NORMAL, "Media") in states(ev)
    assert not hints(ev)


def test_the_mode_survives_emergency_stop():
    eng, s = engine_in(Mode.MEDIA)
    run(eng, s.next().cmd(Command.EMERGENCY_STOP).frames())
    assert eng.state is State.PAUSED and eng.sm.mode is Mode.MEDIA


def test_the_mode_survives_camera_loss_and_recovery():
    eng, s = engine_in(Mode.PRESENTATION)
    s2 = s.next().cmd(Command.CAMERA_LOST, "unplugged").cmd(Command.CAMERA_BACK)
    run(eng, s2.frames())
    assert eng.sm.mode is Mode.PRESENTATION
    ev = run(eng, s2.next().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).frames())
    assert (State.ACTIVE, Sub.NORMAL, "Presentation") in states(ev)


def test_the_indicator_names_the_mode_while_clutched():
    eng, s = engine_in(Mode.MEDIA)
    ev = run(eng, s.next().hold(Pose.G8_FLAT_HAND, 500).frames())
    assert (State.ACTIVE, Sub.CLUTCHED, "Media · Hold") in states(ev)


def test_a_mode_chosen_with_the_menu_is_also_kept_through_a_pause():
    eng = Engine()
    s = pinch(point_at(open_menu(), "media"))
    run(eng, s.frames())
    assert eng.sm.mode is Mode.MEDIA
    run(eng, s.next().hold(Pose.G1_RELAXED, 300).cmd(Command.PAUSE).frames())
    assert eng.state is State.PAUSED and eng.sm.mode is Mode.MEDIA
