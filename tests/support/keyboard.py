"""Helpers for scripts that drive Keyboard Mode (spec 004)."""

from __future__ import annotations

from support.hands import Script, run

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    ButtonDown,
    ButtonUp,
    Click,
    Command,
    KeyboardView,
    KeyStroke,
    MoveCursor,
    Pose,
    Scroll,
)

# pointer-style output that Keyboard Mode must never produce
POINTER_EVENTS = (MoveCursor, Click, ButtonDown, ButtonUp, Scroll)


def key_cam(ident: str, position: str = "bottom", cfg: CoreConfig | None = None):
    """Camera position of the palm that points at the centre of keyboard key ``ident``."""
    cfg = cfg or CoreConfig()
    rect = layout.keyboard_rect(position)
    key = dict(layout.keyboard_keys(position))[ident]
    clip = cfg.target_margin + 1e-6
    nx = (key.x + key.w / 2 - rect.x - clip) / (rect.w - 2 * clip)
    ny = (key.y + key.h / 2 - rect.y - clip) / (rect.h - 2 * clip)
    r = cfg.active_region
    return cfg.active_center_x - r / 2 + r * nx, cfg.active_center_y - r / 2 + r * ny


def kb_engine(cfg: CoreConfig | None = None) -> tuple[Engine, Script]:
    """An Active engine in Keyboard Mode, plus a script that continues from there."""
    eng = Engine(cfg)
    s = (
        Script()
        .hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
        .hold(Pose.G1_RELAXED, 300)
        .cmd(Command.SET_MODE, "KEYBOARD")
        .hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    )
    run(eng, s.frames())
    return eng, s.next()


def point_key(
    s: Script, ident: str, position: str = "bottom", cfg: CoreConfig | None = None, **kw
) -> Script:
    """Move the relaxed hand to a key and settle on it."""
    s.move(Pose.G1_RELAXED, to=key_cam(ident, position, cfg), ms=400, **kw)
    return s.hold(Pose.G1_RELAXED, 800, **kw)


def tap_key(
    s: Script,
    ident: str,
    position: str = "bottom",
    cfg: CoreConfig | None = None,
    pinch_ms: float = 300,
) -> Script:
    """Point at a key, pinch (press), release."""
    point_key(s, ident, position, cfg)
    s.hold(Pose.G2_PINCH_INDEX, pinch_ms)
    return s.hold(Pose.G1_RELAXED, 250)


def strokes(events) -> list[KeyStroke]:
    return [e for e in events if isinstance(e, KeyStroke)]


def last_view(events) -> KeyboardView | None:
    views = [e for e in events if isinstance(e, KeyboardView)]
    return views[-1] if views else None


class Typing:
    """An engine in Keyboard Mode plus a timeline that carries on after every action."""

    def __init__(self, cfg: CoreConfig | None = None) -> None:
        self.cfg = cfg
        self.eng, self.s = kb_engine(cfg)

    def run(self, build) -> list:
        """Run ``build(script)``; the script continues from where the last action ended."""
        s = build(self.s.next())
        self.s = s
        return run(self.eng, s.frames())

    def tap(self, *idents: str, position: str = "bottom") -> list:
        out: list = []
        for ident in idents:
            out += self.run(lambda s, i=ident: tap_key(s, i, position, self.cfg))
        return out

    def command(self, cmd: Command, arg: str = "") -> list:
        return self.run(lambda s: s.cmd(cmd, arg).hold(Pose.G1_RELAXED, 100))
