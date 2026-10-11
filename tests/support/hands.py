"""Synthetic hands and a tiny script DSL for deterministic replay tests (plan D17).

Hands are built in aspect-corrected space with hand size ``scale`` (wrist to middle knuckle, in
units of frame height); ``pose(...)`` places the palm-center anchor exactly at ``at``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    DEFAULT_ASPECT,
    Command,
    CommandRecord,
    Event,
    Hand,
    HandFrame,
    Landmark,
    Pose,
)

T0_NS = 1_000_000_000

# knuckle positions (X right, Y down) in hand sizes, wrist at the origin
_MCP = {
    "index": (-0.22, -0.95),
    "middle": (0.0, -1.0),
    "ring": (0.2, -0.95),
    "pinky": (0.38, -0.85),
}
_ANGLE_DEG = {"index": -10.0, "middle": 0.0, "ring": 8.0, "pinky": 18.0}
_LENGTH = {"index": 1.0, "middle": 1.05, "ring": 1.0, "pinky": 0.8}
_FINGERS = ("index", "middle", "ring", "pinky")


def _finger_points(
    name: str, extended: bool
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    mx, my = _MCP[name]
    k = _LENGTH[name]
    a = math.radians(_ANGLE_DEG[name])
    ux, uy = math.sin(a), -math.cos(a)
    l1, l2, l3 = 0.45 * k, 0.25 * k, 0.20 * k
    pip = (mx + l1 * ux, my + l1 * uy)
    if extended:
        dip = (pip[0] + l2 * ux, pip[1] + l2 * uy)
        tip = (dip[0] + l3 * ux, dip[1] + l3 * uy)
    else:  # folded into the palm: tip ends below its knuckle
        tip = (mx, my + 0.2)
        dip = ((pip[0] + tip[0]) / 2, (pip[1] + tip[1]) / 2)
    return (mx, my), pip, dip, tip


def pose(
    kind: Pose,
    at: tuple[float, float] = (0.5, 0.5),
    scale: float = 0.2,
    score: float = 0.95,
    aspect: float = DEFAULT_ASPECT,
    pinch_ratio: float | None = None,
    thumb_tilt_deg: float = 0.0,
    thumb_right: bool = False,
) -> Hand:
    """Build a hand in pose ``kind`` whose palm center is at ``at`` (normalized image coords).

    ``pinch_ratio`` overrides the thumb-to-fingertip distance (in hand sizes) for G2/G3.
    For G4 (fist, thumb out sideways) ``thumb_tilt_deg`` tilts the thumb (up positive) and
    ``thumb_right`` makes it point right instead of left.
    """
    ext = {
        Pose.G1_RELAXED: (True, False, False, False),
        Pose.G2_PINCH_INDEX: (True, False, False, False),
        Pose.G3_PINCH_MIDDLE: (False, True, False, False),
        Pose.G4_THUMBS_UP: (False, False, False, False),
        Pose.G5_FIST: (False, False, False, False),
        Pose.G6_OPEN_PALM: (True, True, True, True),
        Pose.G7_THREE_FINGERS: (True, True, True, False),
        Pose.G8_FLAT_HAND: (True, True, True, True),
    }[kind]
    chains = {n: _finger_points(n, e) for n, e in zip(_FINGERS, ext, strict=True)}

    ix, iy = _MCP["index"]
    if kind in (Pose.G2_PINCH_INDEX, Pose.G3_PINCH_MIDDLE):
        target = chains["index" if kind is Pose.G2_PINCH_INDEX else "middle"][3]
        r = 0.07 if pinch_ratio is None else pinch_ratio
        thumb_tip = (target[0] + r, target[1])
    elif kind is Pose.G6_OPEN_PALM:
        thumb_tip = (ix - 0.7, iy + 0.1)  # thumb out to the side
    elif kind is Pose.G4_THUMBS_UP:
        thumb_tip = (-1.3, -0.7)  # replaced below by the straight, tiltable thumb chain
    elif kind is Pose.G8_FLAT_HAND:
        thumb_tip = (0.15, -0.7)  # thumb tucked across the center of the palm
    else:
        thumb_tip = (ix + 0.05, iy + 0.3)  # tucked beside the fingers
    t1 = (-0.10, -0.10)
    thumb = [
        t1,
        (t1[0] + (thumb_tip[0] - t1[0]) * 0.4, t1[1] + (thumb_tip[1] - t1[1]) * 0.4),
        (t1[0] + (thumb_tip[0] - t1[0]) * 0.75, t1[1] + (thumb_tip[1] - t1[1]) * 0.75),
        thumb_tip,
    ]

    if kind is Pose.G4_THUMBS_UP:  # straight thumb of length 1 from its base, tilted
        a = math.radians(thumb_tilt_deg)
        side = 1.0 if thumb_right else -1.0
        d = (side * math.cos(a), -math.sin(a))
        base = (0.30 if thumb_right else -0.30, -0.70)
        thumb = [
            (base[0] - 0.2 * d[0], base[1] - 0.2 * d[1]),
            base,
            (base[0] + 0.5 * d[0], base[1] + 0.5 * d[1]),
            (base[0] + d[0], base[1] + d[1]),
        ]

    local: list[tuple[float, float]] = [(0.0, 0.0), *thumb]
    for n in _FINGERS:
        mcp, pip, dip, tip = chains[n]
        local.extend([mcp, pip, dip, tip])
    assert len(local) == 21

    # translate so the palm-center anchor (mean of landmarks 0,5,9,13,17) sits at ``at``
    anchor_idx = (0, 5, 9, 13, 17)
    ax = sum(local[i][0] for i in anchor_idx) / 5 * scale / aspect
    ay = sum(local[i][1] for i in anchor_idx) / 5 * scale
    wx, wy = at[0] - ax, at[1] - ay
    lms = tuple(Landmark(wx + x * scale / aspect, wy + y * scale, 0.0) for x, y in local)
    return Hand(landmarks=lms, handedness="Right", score=score)


class Script:
    """Builds a list of HandFrame / CommandRecord items at a fixed frame rate."""

    def __init__(self, fps: int = 30, t0_ns: int = T0_NS) -> None:
        self.fps = fps
        self.t_ns = t0_ns
        self.items: list[HandFrame | CommandRecord] = []
        self._pos: tuple[float, float] = (0.5, 0.5)
        self._tilt = 0.0

    @property
    def frame_ns(self) -> int:
        return round(1_000_000_000 / self.fps)

    def _frames(self, ms: float) -> int:
        return max(1, round(ms * self.fps / 1000))

    def _emit(self, hands: Sequence[Hand]) -> None:
        self.items.append(HandFrame(t_ns=self.t_ns, hands=tuple(hands)))
        self.t_ns += self.frame_ns

    def hold(
        self,
        kind: Pose,
        ms: float,
        at: tuple[float, float] | None = None,
        score: float = 0.95,
        pinch_ratio: float | None = None,
        others: Iterable[tuple[Pose, tuple[float, float]]] = (),
        tilt: float | None = None,
    ) -> Script:
        """Hold ``kind`` at ``at`` (default: where the last item ended) for ``ms``.

        ``tilt`` sets the G4 thumb tilt in degrees (kept for later holds until changed).
        """
        if at is not None:
            self._pos = at
        if tilt is not None:
            self._tilt = tilt
        extra = [pose(k, p) for k, p in others]
        for _ in range(self._frames(ms)):
            hand = pose(
                kind, self._pos, score=score, pinch_ratio=pinch_ratio, thumb_tilt_deg=self._tilt
            )
            self._emit([hand, *extra])
        return self

    def ramp_tilt(self, kind: Pose, to_deg: float, ms: float, score: float = 0.95) -> Script:
        """Tilt the thumb linearly to ``to_deg`` while the hand stays where it is."""
        n = self._frames(ms)
        start = self._tilt
        for i in range(1, n + 1):
            tilt = start + (to_deg - start) * i / n
            self._emit([pose(kind, self._pos, score=score, thumb_tilt_deg=tilt)])
        self._tilt = to_deg
        return self

    def move(
        self,
        kind: Pose,
        to: tuple[float, float],
        ms: float,
        score: float = 0.95,
        pinch_ratio: float | None = None,
        others: Iterable[tuple[Pose, tuple[float, float]]] = (),
    ) -> Script:
        """Move linearly from the current position to ``to`` while holding ``kind``."""
        extra = [pose(k, p) for k, p in others]
        n = self._frames(ms)
        x0, y0 = self._pos
        for i in range(1, n + 1):
            f = i / n
            pos = (x0 + (to[0] - x0) * f, y0 + (to[1] - y0) * f)
            self._emit([pose(kind, pos, score=score, pinch_ratio=pinch_ratio), *extra])
        self._pos = to
        return self

    def none(self, frames: int = 1, ms: float | None = None) -> Script:
        """Frames with no hand in view."""
        n = self._frames(ms) if ms is not None else frames
        for _ in range(n):
            self._emit([])
        return self

    def others_only(self, others: Iterable[tuple[Pose, tuple[float, float]]], ms: float) -> Script:
        """Frames where only other hands are visible (the primary is absent)."""
        extra = [pose(k, p) for k, p in others]
        for _ in range(self._frames(ms)):
            self._emit(extra)
        return self

    def wait(self, ms: float) -> Script:
        """Advance time without emitting frames (e.g. a stalled camera)."""
        self.t_ns += round(ms * 1_000_000)
        return self

    def cmd(self, command: Command, arg: str = "") -> Script:
        self.items.append(CommandRecord(t_ns=self.t_ns, cmd=command, arg=arg))
        return self

    def next(self) -> Script:
        """A new script that continues from this one's time and hand position."""
        nxt = Script(fps=self.fps, t0_ns=self.t_ns)
        nxt._pos = self._pos
        nxt._tilt = self._tilt
        return nxt

    def frames(self) -> list[HandFrame | CommandRecord]:
        return list(self.items)


def run(engine: Engine, items: Iterable[HandFrame | CommandRecord]) -> list[Event]:
    """Feed ``items`` to ``engine`` in order and return every emitted event."""
    out: list[Event] = []
    for it in items:
        if isinstance(it, CommandRecord):
            out.extend(engine.command(it.cmd, it.t_ns, it.arg))
        else:
            out.extend(engine.step(it, it.t_ns))
    return out


def resume_script(fps: int = 30, at: tuple[float, float] = (0.5, 0.5)) -> Script:
    """A script that starts with an open palm held long enough to resume control."""
    return Script(fps=fps).hold(Pose.G6_OPEN_PALM, 1300, at=at)
