"""Helpers for scripts in Presentation Mode (spec 003)."""

from __future__ import annotations

from support.hands import Script, run
from support.menu import resumed

from gescrtl.core.engine import Engine
from gescrtl.core.types import Command, Pose, SystemAction


def presenting(fps: int = 30) -> tuple[Engine, Script]:
    """An Active engine in Presentation Mode, plus the script that got it there."""
    eng = Engine()
    s = resumed() if fps == 30 else Script(fps=fps).hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
    s.hold(Pose.G1_RELAXED, 300)
    s.cmd(Command.SET_MODE, "PRESENTATION")
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    return eng, s.next()


def swipe(
    s: Script,
    x0: float,
    x1: float,
    ms: float = 250,
    kind: Pose = Pose.G6_OPEN_PALM,
    y: float = 0.5,
    settle_ms: float = 500,
) -> Script:
    """Rest an open hand at ``x0`` then move it quickly to ``x1`` (camera-normalized x)."""
    return s.hold(kind, settle_ms, at=(x0, y)).move(kind, to=(x1, y), ms=ms)


def actions(events):
    return [e.action for e in events if isinstance(e, SystemAction)]
