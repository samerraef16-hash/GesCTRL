"""Pinch-on-target selection shared by the mode menu, the media grid, and the level panel (D4).

A target is chosen when a stable thumb-index pinch begins while a target is pointed. The target
is the one pointed at ``pinch_lookback_frames`` before the first raw pinch frame, so the hand
motion of forming the pinch cannot slide the choice onto a neighbour. One choice per pinch, and a
per-target cooldown.
"""

from __future__ import annotations

import math

from gescrtl.core.config import CoreConfig
from gescrtl.core.one_euro import OneEuro
from gescrtl.core.types import Pose

_MS = 1_000_000
_HISTORY = 16


class PinchSelector:
    def __init__(self, cfg: CoreConfig, cooldown_ms: int | None = None) -> None:
        self.cfg = cfg
        self._cooldown_ms = cooldown_ms  # None: the config's ``action_cooldown_ms``
        self._last_fire: dict[str, int] = {}  # survives reset(): the cooldown is wall time
        self._history: list[str | None] = []
        self._raw_count = 0
        self._target: str | None = None
        self._fired = False
        self._blocked = False  # this pinch became stable during a cooldown: it does nothing

    def reset(self) -> None:
        """Forget a pinch in progress (overlay closed, state changed)."""
        self._history.clear()
        self._raw_count = 0
        self._target = None
        self._fired = False
        self._blocked = False

    @property
    def pinching(self) -> bool:
        """True from the first pinch frame until the pinch is released."""
        return self._raw_count > 0

    @property
    def held_id(self) -> str | None:
        """The target chosen by the pinch that is still held, for repeating actions."""
        return self._target if self._fired and self._raw_count > 0 else None

    def update(
        self,
        pointed: str | None,
        raw: Pose,
        stable: Pose,
        t_ns: int,
    ) -> str | None:
        """Return the chosen target id once per pinch, else None."""
        chosen: str | None = None
        if raw is Pose.G2_PINCH_INDEX:
            if self._raw_count == 0:
                lookback = self.cfg.pinch_lookback_frames
                if lookback == 0 or not self._history:
                    self._target = pointed
                else:
                    self._target = self._history[-min(lookback, len(self._history))]
                self._fired = False
                self._blocked = False
            self._raw_count += 1
            if (
                stable is Pose.G2_PINCH_INDEX
                and not self._fired
                and not self._blocked
                and self._target is not None
                and self._raw_count >= self.cfg.stable_frames
            ):
                if self._cooled_down(self._target, t_ns):
                    self._fired = True
                    self._last_fire[self._target] = t_ns
                    chosen = self._target
                else:
                    self._blocked = True  # a pinch that must wait out a cooldown never fires late
        else:
            self._raw_count = 0
            self._target = None
            self._fired = False
            self._blocked = False
        self._history.append(pointed)
        del self._history[:-_HISTORY]
        return chosen

    def _cooled_down(self, target: str, t_ns: int) -> bool:
        last = self._last_fire.get(target)
        wait = self.cfg.action_cooldown_ms if self._cooldown_ms is None else self._cooldown_ms
        return last is None or t_ns - last >= wait * _MS


class DwellSelector:
    """Chooses a target by holding still on it (the accessibility alternative to a pinch).

    A target is chosen once, after ``dwell_ms`` on the same target with the point staying within
    ``dwell_still_dist``. It is armed again only after the target changes or the point moves more
    than twice that distance, so holding still never repeats (spec 004 D4, FR-018).
    """

    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._last_ns = 0
        self.reset()

    def reset(self) -> None:
        self._target: str | None = None
        self._ref: tuple[float, float] = (0.0, 0.0)
        self._since_ns = 0
        self._done = False

    @property
    def progress(self) -> float:
        """0..1 while dwelling on a target that has not been chosen yet."""
        if self._target is None or self._done:
            return 0.0
        elapsed = self._last_ns - self._since_ns
        return min(max(elapsed / (self.cfg.dwell_ms * _MS), 0.0), 1.0)

    def update(self, target: str | None, point: tuple[float, float], t_ns: int) -> str | None:
        self._last_ns = t_ns
        if target is None:
            self.reset()
            return None
        still = self.cfg.dwell_still_dist
        moved = math.dist(point, self._ref)
        if target != self._target:
            self._target, self._ref, self._since_ns, self._done = target, point, t_ns, False
            return None
        if self._done:
            if moved > 2 * still:  # it left and came back: armed again
                self._ref, self._since_ns, self._done = point, t_ns, False
            return None
        if moved > still:
            self._ref, self._since_ns = point, t_ns  # still wandering: start the clock again
            return None
        if t_ns - self._since_ns >= self.cfg.dwell_ms * _MS:
            self._done = True
            return target
        return None


class ScreenPointer:
    """Hand position to a normalized screen position, mapped and smoothed like Pointer Mode.

    Used by every overlay that is pointed at (mode menu, level panel, media grid) and, with
    stronger smoothing, by the presentation laser. It never moves the OS cursor.
    """

    def __init__(
        self, cfg: CoreConfig, min_cutoff: float | None = None, beta: float | None = None
    ) -> None:
        self.cfg = cfg
        cutoff = cfg.one_euro_min_cutoff if min_cutoff is None else min_cutoff
        slope = cfg.one_euro_beta if beta is None else beta
        self._fx = OneEuro(cutoff, slope, cfg.one_euro_d_cutoff)
        self._fy = OneEuro(cutoff, slope, cfg.one_euro_d_cutoff)

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()

    def update(self, anchor: tuple[float, float], t_ns: int) -> tuple[float, float]:
        t_s = t_ns / 1e9
        fx, fy = self._fx(anchor[0], t_s), self._fy(anchor[1], t_s)
        r = self.cfg.active_region
        edge_x = self.cfg.active_center_x - r / 2
        edge_y = self.cfg.active_center_y - r / 2
        return _clamp01((fx - edge_x) / r), _clamp01((fy - edge_y) / r)


def _clamp01(v: float) -> float:
    return min(max(v, 0.0), 1.0)
