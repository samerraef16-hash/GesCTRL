"""Helpers for custom gesture scripts (spec 004 D9)."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date

from support.hands import Script, resume_script, run

from gescrtl.core.config import CoreConfig
from gescrtl.core.custom import CustomGesture
from gescrtl.core.engine import Engine
from gescrtl.core.types import Command, Pose, SetupResult

TAKE_MS = 3100  # one shape take: a 2 s countdown, 1 s of recording, and a little margin


def new_engine(mode: str = "POINTER", **cfg) -> tuple[Engine, Script]:
    """An Active engine with custom gestures switched on, plus a script to continue."""
    cfg.setdefault("custom_gestures_enabled", True)
    eng = Engine(CoreConfig(**cfg))
    s = resume_script().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    if mode != "POINTER":
        s.cmd(Command.SET_MODE, mode).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    return eng, s.next()


def enroll(eng: Engine, s: Script, kind: str, name: str, build: Callable[[Script], Script]):
    """Start an enrollment, run ``build(script)``, and return (events, result values or None)."""
    s.cmd(Command.START_SETUP, f"enroll:{kind}:{name}")
    build(s)
    ev = run(eng, s.frames())
    results = [e for e in ev if isinstance(e, SetupResult)]
    return ev, (results[-1].values if results else None)


def gesture_from(values, action: str = "MUTE", modes: tuple[str, ...] = ()) -> CustomGesture:
    return CustomGesture(
        name=values["name"],
        kind=values["kind"],
        action=action,
        modes=modes,
        enabled=True,
        samples=tuple(tuple(x) for x in values["samples"]),
        threshold=values["threshold"],
        created=date.today().isoformat(),
    )


def shape_takes(kind: Pose = Pose.G1_RELAXED, n: int = 5, **kw) -> Callable[[Script], Script]:
    def build(s: Script) -> Script:
        for _ in range(n):
            s.hold(kind, TAKE_MS, **kw)
        return s

    return build


def circle_path(start: tuple[float, float], r: float = 0.12, n: int = 24):
    """A full circle in camera units that starts and ends at ``start``."""
    cx, cy = start[0] + r, start[1]
    pts = [
        (
            cx + r * math.cos(math.pi + 2 * math.pi * i / n),
            cy + r * math.sin(math.pi + 2 * math.pi * i / n),
        )
        for i in range(n + 1)
    ]
    return pts


def line_path(start: tuple[float, float], dx: float = 0.3):
    return [start, (start[0] + dx, start[1])]


def movement_takes(
    path_fn: Callable[[tuple[float, float]], list[tuple[float, float]]],
    n: int = 5,
    kind: Pose = Pose.G1_RELAXED,
    ms: float = 700,
    start: tuple[float, float] = (0.4, 0.5),
) -> Callable[[Script], Script]:
    def build(s: Script) -> Script:
        s.move(kind, to=start, ms=300)
        s.hold(kind, 2300)
        for _ in range(n):
            pts = path_fn(start)
            s.path(kind, pts, ms)
            _back_to(s, kind, pts[-1], start, 2400)
        return s

    return build


def perform(
    s: Script,
    path_fn,
    kind: Pose = Pose.G1_RELAXED,
    ms: float = 700,
    start: tuple[float, float] = (0.4, 0.5),
    rest_ms: float = 700,
) -> Script:
    """Rest, make one movement, and rest again."""
    s.move(kind, to=start, ms=300)
    s.hold(kind, rest_ms)
    pts = path_fn(start)
    s.path(kind, pts, ms)
    return _back_to(s, kind, pts[-1], start, rest_ms)


def _back_to(
    s: Script, kind: Pose, here: tuple[float, float], start: tuple[float, float], ms: float
) -> Script:
    """Rest for ``ms``; if the movement ended away from ``start``, settle first (so the movement
    ends) and then go back quickly while the next take is still counting down."""
    if math.dist(here, start) > 0.01:
        s.hold(kind, 300)
        s.move(kind, to=start, ms=300)
        return s.hold(kind, ms - 600)
    return s.hold(kind, ms)


back_to = _back_to
