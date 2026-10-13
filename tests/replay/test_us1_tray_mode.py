"""US1 scenario 8: switching modes from the tray (FR-025) is the SET_MODE command."""

from support.hands import run
from support.menu import open_menu, resumed

from gescrtl.core.engine import Engine
from gescrtl.core.state_machine import MODE_HINTS
from gescrtl.core.types import (
    Command,
    HintsShown,
    Mode,
    ModeChanged,
    OverlayHidden,
    Pose,
    ReleaseAll,
    State,
    StateChanged,
    Sub,
)
from gescrtl.recording import jsonl


def states(events):
    return [(e.state, e.sub, e.hud_text) for e in events if isinstance(e, StateChanged)]


def active_engine():
    eng = Engine()
    s = resumed().hold(Pose.G1_RELAXED, 300)
    run(eng, s.frames())
    return eng, s


def test_set_mode_while_active_switches_like_the_gesture_menu():
    eng, s = active_engine()
    ev = run(eng, s.next().cmd(Command.SET_MODE, "MEDIA").frames())
    assert eng.sm.mode is Mode.MEDIA and eng.sub is Sub.NORMAL
    assert ReleaseAll("mode change") in ev
    assert ModeChanged(Mode.MEDIA) in ev
    assert (State.ACTIVE, Sub.NORMAL, "Media") in states(ev)
    assert HintsShown(MODE_HINTS[Mode.MEDIA]) in ev


def test_set_mode_closes_an_open_gesture_menu():
    eng = Engine()
    s = open_menu()
    run(eng, s.frames())
    assert eng.sub is Sub.MODE_MENU
    ev = run(eng, s.next().cmd(Command.SET_MODE, "PRESENTATION").frames())
    assert eng.sub is Sub.NORMAL and eng.sm.mode is Mode.PRESENTATION
    assert any(isinstance(e, OverlayHidden) for e in ev)


def test_set_mode_while_clutched_releases_the_clutch():
    eng, s = active_engine()
    s2 = s.next().hold(Pose.G8_FLAT_HAND, 500)
    run(eng, s2.frames())
    assert eng.sub is Sub.CLUTCHED
    run(eng, s2.next().cmd(Command.SET_MODE, "PRESENTATION").frames())
    assert eng.sub is Sub.NORMAL and eng.sm.mode is Mode.PRESENTATION


def test_set_mode_while_paused_applies_on_resume_and_keeps_the_paused_text():
    eng = Engine()
    assert eng.state is State.PAUSED  # every engine starts Paused
    ev = eng.command(Command.SET_MODE, 1, "PRESENTATION")
    assert ev == [ModeChanged(Mode.PRESENTATION)]
    assert not states(ev)  # the indicator still says "Paused"
    ev = run(eng, resumed().frames())
    assert (State.ACTIVE, Sub.NORMAL, "Presentation") in states(ev)
    assert HintsShown(MODE_HINTS[Mode.PRESENTATION]) in ev


def test_set_mode_while_tracking_lost_applies_when_the_hand_returns():
    eng, s = active_engine()
    s2 = s.next().none(ms=400)
    run(eng, s2.frames())
    assert eng.state is State.TRACKING_LOST
    ev = run(eng, s2.next().cmd(Command.SET_MODE, "MEDIA").frames())
    assert ev == [ModeChanged(Mode.MEDIA)]
    ev = run(eng, s2.next().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).frames())
    assert (State.ACTIVE, Sub.NORMAL, "Media") in states(ev)


def test_keyboard_can_be_chosen_from_the_tray():
    eng, s = active_engine()
    ev = eng.command(Command.SET_MODE, s.t_ns, "KEYBOARD")
    assert eng.sm.mode is Mode.KEYBOARD and ModeChanged(Mode.KEYBOARD) in ev


def test_unknown_names_and_the_current_mode_do_nothing():
    eng, s = active_engine()
    for arg in ("BOGUS", "", "pointer", "POINTER"):
        assert eng.command(Command.SET_MODE, s.t_ns, arg) == [], arg
    assert eng.sm.mode is Mode.POINTER


def test_set_mode_while_inactive_does_nothing():
    eng, s = active_engine()
    eng.command(Command.TURN_OFF, s.t_ns)
    assert eng.state is State.INACTIVE
    assert eng.command(Command.SET_MODE, s.t_ns + 1, "MEDIA") == []
    assert eng.sm.mode is Mode.POINTER


def test_a_recorded_set_mode_command_replays_to_the_same_events(tmp_path):
    s = resumed().hold(Pose.G1_RELAXED, 300).cmd(Command.SET_MODE, "PRESENTATION")
    s.hold(Pose.G1_RELAXED, 300)
    path = tmp_path / "tray.jsonl"
    with jsonl.RecordingWriter(path, scenario="tray") as w:
        for it in s.frames():
            if hasattr(it, "cmd"):
                w.command(it.t_ns, it.cmd, it.arg)
            else:
                w.frame(it)
    direct = run(Engine(), s.frames())
    replayed = run(Engine(), list(jsonl.read(path)))
    assert ModeChanged(Mode.PRESENTATION) in direct
    assert [type(e) for e in replayed] == [type(e) for e in direct]
    assert [e for e in replayed if isinstance(e, ModeChanged)] == [ModeChanged(Mode.PRESENTATION)]
    assert states(replayed) == states(direct)
