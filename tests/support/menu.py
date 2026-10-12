"""Helpers for scripts that drive the mode menu (spec 003)."""

from __future__ import annotations

from support.hands import Script

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.types import (
    ButtonDown,
    ButtonUp,
    Click,
    LevelStep,
    MoveCursor,
    Pose,
    Scroll,
    SystemAction,
)

# Anything that reaches the operating system; none of it may be sent while an overlay is open.
INPUT_EVENTS = (MoveCursor, Click, ButtonDown, ButtonUp, Scroll, SystemAction, LevelStep)


def cam_pos(
    items: layout.Items, ident: str, dx: float = 0.0, dy: float = 0.0
) -> tuple[float, float]:
    """Camera position of the palm that points at the centre of target ``ident``."""
    rect = dict(items)[ident]
    edge = 0.5 - CoreConfig().active_region / 2
    r = CoreConfig().active_region
    sx, sy = rect.x + rect.w / 2 + dx, rect.y + rect.h / 2 + dy
    return edge + r * sx, edge + r * sy


def resumed() -> Script:
    """Resume into Pointer Mode with the hand at the centre."""
    return Script().hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))


def open_menu(s: Script | None = None, extra_ms: float = 300) -> Script:
    """Hold three fingers long enough to open the menu, plus ``extra_ms`` inside it."""
    s = s or resumed()
    return s.hold(Pose.G7_THREE_FINGERS, 900 + extra_ms)


def point_at(s: Script, ident: str, ms: float = 600, dx: float = 0.0, dy: float = 0.0) -> Script:
    """Move the (relaxed) hand to target ``ident`` of the mode menu and settle there."""
    to = cam_pos(layout.MODE_MENU_ITEMS, ident, dx, dy)
    return s.move(Pose.G1_RELAXED, to=to, ms=ms).hold(Pose.G1_RELAXED, 500)


def pinch(s: Script, ms: float = 400) -> Script:
    return s.hold(Pose.G2_PINCH_INDEX, ms)


def active_in(mode_name: str, fps: int = 30):
    """An Active engine in ``mode_name`` (a ``Mode`` member name), plus a script to continue."""
    from support.hands import run

    from gescrtl.core.engine import Engine
    from gescrtl.core.types import Command

    eng = Engine()
    s = Script(fps=fps).hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5)).hold(Pose.G1_RELAXED, 300)
    if mode_name != "POINTER":
        s.cmd(Command.SET_MODE, mode_name).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    run(eng, s.frames())
    return eng, s.next()


def timed_run(engine, items):
    """Like ``run`` but returns (t_ns, event) pairs."""
    from gescrtl.core.types import CommandRecord

    out = []
    for it in items:
        evs = (
            engine.command(it.cmd, it.t_ns, it.arg)
            if isinstance(it, CommandRecord)
            else engine.step(it, it.t_ns)
        )
        out.extend((it.t_ns, e) for e in evs)
    return out
