"""Open-hand swipe detection for slide changes (plan D6, FR-008).

Fed with the palm anchor, hand size, and whether the hand is open on every good frame. A swipe is
a fast, mostly horizontal move of an open hand: enough open-hand frames in the window (the stable
frames gate for a motion), far enough in hand sizes, and not diagonal. After a swipe it will not
fire again until the cooldown has passed *and* the hand has slowed down, and the opposite
direction stays blocked for a while so the return stroke is ignored.
"""

from __future__ import annotations

from collections import deque

from gescrtl.core.config import CoreConfig
from gescrtl.core.types import Action

_MS = 1_000_000
_Sample = tuple[int, float, float]  # t_ns, x, y in aspect-corrected image units


class SwipeDetector:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._window: deque[_Sample] = deque()
        self._last_fire_ns: int | None = None
        self._last_dir = 0
        self._armed = True
        self._slow_since_ns: int | None = None
        self._travel = 0.0  # horizontal extent of the window, in hand sizes

    def reset(self) -> None:
        """Forget the motion in progress. A recent swipe still blocks the return stroke."""
        self._window.clear()
        self._slow_since_ns = None
        self._travel = 0.0

    @property
    def moving(self) -> bool:
        """A swipe is in progress: at least two open-hand frames with real horizontal travel."""
        return len(self._window) >= 2 and self._travel >= self.cfg.swipe_min_dist / 2

    def update(
        self,
        t_ns: int,
        anchor: tuple[float, float],
        size: float,
        aspect: float,
        is_open: bool,
    ) -> Action | None:
        cfg = self.cfg
        if not is_open:
            self.reset()
            return None
        x, y = anchor[0] * aspect, anchor[1]
        if self._window:
            t0, x0, y0 = self._window[-1]
            dt = (t_ns - t0) / 1e9
            speed = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5 / size / dt if dt > 0 else 0.0
            if speed < cfg.swipe_rearm_speed:
                if self._slow_since_ns is None:
                    self._slow_since_ns = t_ns
                if t_ns - self._slow_since_ns >= cfg.swipe_rearm_ms * _MS:
                    self._armed = True
            else:
                self._slow_since_ns = None
        self._window.append((t_ns, x, y))
        while t_ns - self._window[0][0] > cfg.swipe_window_ms * _MS:
            self._window.popleft()

        # the sample that gives the longest horizontal run up to the newest one
        best = max(self._window, key=lambda s: abs(x - s[1]))
        dx, dy = (x - best[1]) / size, (y - best[2]) / size
        self._travel = abs(dx)
        if (
            len(self._window) < cfg.swipe_min_frames
            or abs(dx) < cfg.swipe_min_dist
            or abs(dy) > cfg.swipe_max_dy_ratio * abs(dx)
            or not self._armed
        ):
            return None
        last = self._last_fire_ns
        if last is not None and t_ns - last < cfg.swipe_cooldown_ms * _MS:
            return None
        direction = 1 if dx > 0 else -1
        if (
            last is not None
            and direction == -self._last_dir
            and t_ns - last < cfg.swipe_return_block_ms * _MS
        ):
            return None
        self._last_fire_ns, self._last_dir = t_ns, direction
        self._armed = False
        self._slow_since_ns = None
        self._window.clear()
        self._travel = 0.0
        return Action.SLIDE_NEXT if direction > 0 else Action.SLIDE_PREV
