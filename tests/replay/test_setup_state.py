"""The SETUP sub-state: no input is sent and every exit path ends the session (spec 004 D7)."""

import pytest
from support.hands import Script, resume_script, run
from support.keyboard import POINTER_EVENTS

from gescrtl.core import engine as engine_module
from gescrtl.core.engine import Engine
from gescrtl.core.setup import SetupStep
from gescrtl.core.types import (
    Command,
    KeyStroke,
    LevelStep,
    Pose,
    ReleaseAll,
    SetupResult,
    SetupView,
    State,
    StateChanged,
    Sub,
    SystemAction,
    Warning,
)


class Dummy:
    """A session that finishes after ``frames`` good frames."""

    kind = "calibration"

    def __init__(self, frames: int = 10**9) -> None:
        self.frames = frames
        self.bad = 0

    def start(self, t_ns):
        return [SetupView("check", "hello", 0.0)]

    def update(self, feats, raw, stable, t_ns, hand=None):
        self.frames -= 1
        if self.frames <= 0:
            return SetupStep([SetupView("done", "ok", 1.0)], done=True, values={"x": 1})
        return SetupStep()

    def bad_frame(self, t_ns):
        self.bad += 1


@pytest.fixture
def dummy(monkeypatch):
    holder = {"session": Dummy()}
    monkeypatch.setattr(
        engine_module, "make_session", lambda arg, cfg, existing=(): holder["session"]
    )
    return holder


def active():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 300)
    run(eng, s.frames())
    return eng, s.next()


def results(events):
    return [e for e in events if isinstance(e, SetupResult)]


def test_start_enters_setup_releases_everything_and_shows_progress(dummy):
    eng, s = active()
    ev = run(eng, s.cmd(Command.START_SETUP, "calibration").frames())
    assert (eng.state, eng.sub) == (State.ACTIVE, Sub.SETUP)
    assert ReleaseAll("setup") in ev
    assert StateChanged(State.ACTIVE, Sub.SETUP, "Setup") in ev
    assert SetupView("check", "hello", 0.0) in ev


def test_no_input_of_any_kind_is_sent_in_setup(dummy):
    eng, s = active()
    s.cmd(Command.START_SETUP, "calibration")
    s.hold(Pose.G1_RELAXED, 300).hold(Pose.G2_PINCH_INDEX, 500).hold(Pose.G3_PINCH_MIDDLE, 500)
    s.hold(Pose.G4_THUMBS_UP, 600, tilt=60).hold(Pose.G5_FIST, 400).hold(
        Pose.G7_THREE_FINGERS, 1000
    )
    s.hold(Pose.G9_CALL_ME, 800).hold(Pose.G10_INDEX_POINT, 400)
    ev = run(eng, s.frames())
    forbidden = POINTER_EVENTS + (KeyStroke, LevelStep, SystemAction)
    assert not [e for e in ev if isinstance(e, forbidden)]
    assert eng.sub is Sub.SETUP


def test_a_long_flat_hand_does_not_pause_in_setup(dummy):
    eng, s = active()
    s.cmd(Command.START_SETUP, "calibration").hold(Pose.G8_FLAT_HAND, 2500)
    run(eng, s.frames())
    assert eng.sub is Sub.SETUP and eng.state is State.ACTIVE


def test_a_finished_session_reports_its_values_and_returns_to_normal(dummy):
    dummy["session"] = Dummy(frames=5)
    eng, s = active()
    ev = run(eng, s.cmd(Command.START_SETUP, "calibration").hold(Pose.G1_RELAXED, 400).frames())
    assert results(ev) == [SetupResult("calibration", {"x": 1})]
    assert (eng.state, eng.sub) == (State.ACTIVE, Sub.NORMAL)
    assert eng.session is None


@pytest.mark.parametrize(
    "command", [Command.END_SETUP, Command.PAUSE, Command.EMERGENCY_STOP, Command.EXIT]
)
def test_every_command_exit_cancels_without_a_result_value(dummy, command):
    eng, s = active()
    run(eng, s.cmd(Command.START_SETUP, "calibration").hold(Pose.G1_RELAXED, 300).frames())
    ev = run(eng, s.next().cmd(command).frames())
    assert results(ev) == [SetupResult("calibration", None)]
    assert eng.session is None and eng.sub is not Sub.SETUP


def test_a_short_loss_keeps_the_session_a_long_loss_cancels_it(dummy):
    eng, s = active()
    run(eng, s.cmd(Command.START_SETUP, "calibration").hold(Pose.G1_RELAXED, 300).frames())
    ev = run(eng, s.next().none(ms=1500).hold(Pose.G1_RELAXED, 300).frames())
    assert eng.sub is Sub.SETUP and not results(ev)
    assert dummy["session"].bad > 0  # the step in progress was told to start over
    ev = run(eng, s.next().none(ms=3500).frames())
    assert results(ev) == [SetupResult("calibration", None)]
    assert eng.state is State.TRACKING_LOST


def test_setup_needs_an_active_app_and_a_known_session(dummy):
    eng = Engine()
    ev = eng.command(Command.START_SETUP, 0, "calibration")
    assert any(isinstance(e, Warning) for e in ev) and eng.sub is Sub.NONE
    eng, s = active()
    dummy["session"] = None
    ev = run(eng, s.cmd(Command.START_SETUP, "nonsense").frames())
    assert any(isinstance(e, Warning) for e in ev) and eng.sub is Sub.NORMAL


def test_changing_settings_cancels_a_running_setup(dummy):
    eng, s = active()
    run(eng, s.cmd(Command.START_SETUP, "calibration").hold(Pose.G1_RELAXED, 200).frames())
    ev = eng.apply_config(eng.cfg)
    assert results(ev) == [SetupResult("calibration", None)] and eng.sub is Sub.NORMAL


def test_setup_is_deterministic(dummy):
    def go():
        dummy["session"] = Dummy(frames=8)
        eng, s = active()
        return run(
            eng, s.cmd(Command.START_SETUP, "calibration").hold(Pose.G1_RELAXED, 500).frames()
        )

    assert go() == go()


def test_unused_script_class_is_importable():
    assert Script
