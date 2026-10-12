"""Pointer Mode actions: move, click, double click, right click, drag, scroll (plan D4-D6).

Called by the engine only while the application is Active (Normal) and the frame is good.
Pure logic: positions in, events out; time comes from the frame timestamps.
"""

from __future__ import annotations

import math
from collections import deque
from enum import Enum, auto

from gescrtl.core.config import CoreConfig
from gescrtl.core.features import PINCH_MIN_REACH, Features
from gescrtl.core.one_euro import OneEuro
from gescrtl.core.types import (
    Button,
    ButtonDown,
    ButtonUp,
    Click,
    CueChanged,
    CueKind,
    Event,
    MoveCursor,
    Pose,
    Scroll,
)

_PINCH_POSES = (Pose.G2_PINCH_INDEX, Pose.G3_PINCH_MIDDLE)
# G6 is ordinary movement while Active; G10 (index point) is the presentation laser pose and
# just points here
_MOVE_POSES = (Pose.G1_RELAXED, Pose.G6_OPEN_PALM, Pose.G10_INDEX_POINT)


class _Phase(Enum):
    MOVE = auto()
    PINCH = auto()
    DRAG = auto()
    SCROLL = auto()


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


class Pointer:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._fx = OneEuro(cfg.one_euro_min_cutoff, cfg.one_euro_beta, cfg.one_euro_d_cutoff)
        self._fy = OneEuro(cfg.one_euro_min_cutoff, cfg.one_euro_beta, cfg.one_euro_d_cutoff)
        self._history: deque[tuple[float, float]] = deque(maxlen=max(cfg.pinch_lookback_frames, 1))
        self._tilt = OneEuro(2.0, 0.0, 1.0)  # ~2 Hz low-pass on the thumb angle
        self.reset()

    # -- lifecycle ---------------------------------------------------------------------------

    def reset(self) -> None:
        """Forget all in-progress actions (the engine emits ReleaseAll separately)."""
        self._fx.reset()
        self._fy.reset()
        self._tilt.reset()
        self._history.clear()
        self._phase = _Phase.MOVE
        self._need_release = True  # a pinch still held after a reset must be released and redone
        self._hold_until_ns = 0
        self._last_left: tuple[int, tuple[float, float]] | None = None
        self._last_right_ns: int | None = None
        # pinch
        self._pinch_pose = Pose.NONE
        self._pinch_pos = (0.0, 0.0)
        self._pinch_t_ns = 0
        self._confirmed = False
        # drag / scroll
        self._last_pos = (0.5, 0.5)
        self._prev_raw = Pose.NONE
        self._tilt_f = 0.0
        self._scroll_anchor = 0.0
        self._scroll_acc = 0.0
        self._scroll_t_ns = 0
        self._scroll_settle_until_ns = 0
        self.scroll_rel_deg = 0.0  # for the preview readout
        self.scroll_rate = 0.0
        # cue
        self._cue: tuple[CueKind, int] | None = None
        self._cue_hold_until_ns = 0

    @property
    def busy(self) -> bool:
        """True while a pinch, drag, or scroll is in progress."""
        return self._phase is not _Phase.MOVE

    # -- helpers -----------------------------------------------------------------------------

    def _map(self, ax: float, ay: float) -> tuple[float, float]:
        r = self.cfg.active_region
        edge = 0.5 - r / 2
        return _clamp01((ax - edge) / r), _clamp01((ay - edge) / r)

    def _set_cue(self, kind: CueKind, progress: float, t_ns: int) -> list[Event]:
        q = round(max(-1.0, min(1.0, progress)) * 10)  # SCROLL carries a signed strength
        if kind is not CueKind.CLICK and t_ns < self._cue_hold_until_ns:
            return []
        if self._cue == (kind, q):
            return []
        self._cue = (kind, q)
        if kind is CueKind.CLICK:
            self._cue_hold_until_ns = t_ns + self.cfg.click_flash_ms * 1_000_000
        return [CueChanged(kind, q / 10)]

    def _pinch_progress(self, f: Features) -> float | None:
        ratios = []
        if f.reach[0] > PINCH_MIN_REACH:
            ratios.append(f.pinch_index)
        if f.reach[1] > PINCH_MIN_REACH:
            ratios.append(f.pinch_middle)
        if not ratios:
            return None
        r = min(ratios)
        if r >= self.cfg.pinch_release:
            return None
        span = self.cfg.pinch_release - self.cfg.pinch_enter
        return _clamp01((self.cfg.pinch_release - r) / span)

    def _dist(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    # -- per-frame update ---------------------------------------------------------------------

    def update(self, f: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        t_s = t_ns / 1e9
        fx = self._fx(f.anchor[0], t_s)
        fy = self._fy(f.anchor[1], t_s)
        pos = self._map(fx, fy)
        if raw is Pose.G4_THUMBS_UP and self._prev_raw is not Pose.G4_THUMBS_UP:
            self._tilt.reset()  # start from the real thumb angle, not the relaxed hand's
        self._prev_raw = raw
        self._tilt_f = self._tilt(f.thumb_tilt_deg, t_s)

        if self._phase is _Phase.PINCH:
            events = self._on_pinch(f, raw, stable, pos, t_ns)
        elif self._phase is _Phase.DRAG:
            events = self._on_drag(raw, pos, t_ns)
        elif self._phase is _Phase.SCROLL:
            events = self._on_scroll(raw, stable, t_ns)
        else:
            events = self._on_move(f, raw, stable, pos, t_ns)

        self._history.append(pos)
        return events

    def _on_move(
        self, f: Features, raw: Pose, stable: Pose, pos: tuple[float, float], t_ns: int
    ) -> list[Event]:
        events: list[Event] = []
        if raw in _PINCH_POSES:
            if not self._need_release:
                return self._start_pinch(raw, pos, t_ns)
        else:
            self._need_release = False
        if stable is Pose.G4_THUMBS_UP:
            self._phase = _Phase.SCROLL  # like pressing the scroll wheel: the tilt now is zero
            self._scroll_anchor = self._tilt_f
            self._scroll_acc = 0.0
            self._scroll_t_ns = t_ns
            self._scroll_settle_until_ns = t_ns + self.cfg.scroll_settle_ms * 1_000_000
            return self._set_cue(CueKind.SCROLL, 0.0, t_ns)
        if t_ns >= self._hold_until_ns and stable in _MOVE_POSES:
            self._last_pos = pos
            events.append(MoveCursor(*pos))
        prog = self._pinch_progress(f)
        if prog is None:
            events += self._set_cue(CueKind.READY, 0.0, t_ns)
        else:
            events += self._set_cue(CueKind.PINCH, prog, t_ns)
        return events

    # pinch ---------------------------------------------------------------------------------

    def _start_pinch(self, raw: Pose, pos: tuple[float, float], t_ns: int) -> list[Event]:
        lookback = self.cfg.pinch_lookback_frames
        if lookback > 0 and self._history:
            idx = min(lookback, len(self._history))
            start = self._history[-idx]
        else:
            start = pos
        if raw is Pose.G2_PINCH_INDEX and self._last_left is not None:
            last_t, last_pos = self._last_left
            within_time = t_ns - last_t <= self.cfg.double_click_ms * 1_000_000
            if within_time and self._dist(start, last_pos) <= self.cfg.double_click_dist:
                start = last_pos  # second tap of a double click lands on the first
        self._phase = _Phase.PINCH
        self._pinch_pose = raw
        self._pinch_pos = start
        self._pinch_t_ns = t_ns
        self._confirmed = False
        self._last_pos = start
        return [MoveCursor(*start), *self._set_cue(CueKind.PINCH, 1.0, t_ns)]

    def _on_pinch(
        self, f: Features, raw: Pose, stable: Pose, pos: tuple[float, float], t_ns: int
    ) -> list[Event]:
        if raw is not self._pinch_pose:
            return self._end_pinch(t_ns)
        if stable is self._pinch_pose:
            self._confirmed = True
        held_ns = t_ns - self._pinch_t_ns
        if (
            self._confirmed
            and self._pinch_pose is Pose.G2_PINCH_INDEX
            and held_ns >= self.cfg.drag_hold_ms * 1_000_000
        ):
            self._phase = _Phase.DRAG
            return [
                MoveCursor(*self._pinch_pos),
                ButtonDown(Button.LEFT),
                *self._set_cue(CueKind.DRAG, 0.0, t_ns),
            ]
        prog = self._pinch_progress(f)
        return self._set_cue(CueKind.PINCH, 1.0 if prog is None else prog, t_ns)

    def _end_pinch(self, t_ns: int) -> list[Event]:
        """The pinch was released before it became a drag."""
        self._phase = _Phase.MOVE
        events: list[Event] = []
        if not self._confirmed:
            return self._set_cue(CueKind.READY, 0.0, t_ns)  # flicker: no action at all
        held_ns = t_ns - self._pinch_t_ns
        self._hold_until_ns = t_ns + self.cfg.click_stabilize_ms * 1_000_000
        if self._pinch_pose is Pose.G2_PINCH_INDEX:
            self._last_left = (t_ns, self._pinch_pos)
            events += [MoveCursor(*self._pinch_pos), Click(Button.LEFT)]
        else:
            cooled = (
                self._last_right_ns is None
                or t_ns - self._last_right_ns >= self.cfg.right_click_cooldown_ms * 1_000_000
            )
            short = held_ns <= self.cfg.right_click_max_hold_ms * 1_000_000
            if not (cooled and short):
                return self._set_cue(CueKind.READY, 0.0, t_ns)
            self._last_right_ns = t_ns
            events += [MoveCursor(*self._pinch_pos), Click(Button.RIGHT)]
        return events + self._set_cue(CueKind.CLICK, 0.0, t_ns)

    # drag ----------------------------------------------------------------------------------

    def _on_drag(self, raw: Pose, pos: tuple[float, float], t_ns: int) -> list[Event]:
        if raw is not Pose.G2_PINCH_INDEX:
            self._phase = _Phase.MOVE
            self._hold_until_ns = t_ns + self.cfg.click_stabilize_ms * 1_000_000
            return [ButtonUp(Button.LEFT), *self._set_cue(CueKind.READY, 0.0, t_ns)]
        self._last_pos = pos
        return [MoveCursor(*pos)]

    # scroll ----------------------------------------------------------------------------------

    def _scroll_rate_for(self, rel_deg: float) -> float:
        """Wheel units/s for a tilt of ``rel_deg`` from the start angle (up = positive)."""
        dz, full = self.cfg.scroll_deadzone_deg, self.cfg.scroll_full_deg
        mag = abs(rel_deg)
        if mag <= dz:
            return 0.0
        x = min((mag - dz) / max(full - dz, 1e-6), 1.0)
        return math.copysign(self.cfg.scroll_max_rate * x**1.5, rel_deg)

    def _on_scroll(self, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        if stable is not Pose.G4_THUMBS_UP:
            self._phase = _Phase.MOVE
            self.scroll_rel_deg = self.scroll_rate = 0.0
            return self._set_cue(CueKind.READY, 0.0, t_ns)
        dt = min((t_ns - self._scroll_t_ns) / 1e9, 0.1)  # a stall must not cause a burst
        self._scroll_t_ns = t_ns
        if raw is not Pose.G4_THUMBS_UP:
            # the pose is ending (stable lags by a few frames): the thumb is moving, so stop now
            self.scroll_rel_deg = self.scroll_rate = 0.0
            return self._set_cue(CueKind.SCROLL, 0.0, t_ns)
        if t_ns < self._scroll_settle_until_ns:
            self._scroll_anchor = self._tilt_f  # still settling into the pose: no scrolling yet
        self.scroll_rel_deg = self._tilt_f - self._scroll_anchor
        self.scroll_rate = self._scroll_rate_for(self.scroll_rel_deg)
        self._scroll_acc += self.scroll_rate * dt
        events: list[Event] = []
        steps = int(self._scroll_acc / self.cfg.scroll_step)
        if steps:
            amount = steps * self.cfg.scroll_step
            self._scroll_acc -= amount
            events.append(Scroll(amount))
        strength = self.scroll_rate / self.cfg.scroll_max_rate
        return events + self._set_cue(CueKind.SCROLL, strength, t_ns)
