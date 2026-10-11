"""Primary-hand selection (interaction model: Primary hand; plan D9).

One hand controls at a time. While tracking normally, the primary hand is the hand whose wrist is
nearest the last primary wrist, within ``max_hand_jump``. If none is that close, the primary is
reported missing instead of silently handing control to another hand.
"""

from __future__ import annotations

import math

from gescrtl.core.config import CoreConfig
from gescrtl.core.types import Hand


class PrimaryHand:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._last: tuple[float, float] | None = None

    def forget(self) -> None:
        """Drop the lock entirely (the next hand seen is acquired by confidence)."""
        self._last = None

    def select(self, hands: tuple[Hand, ...], reacquire: bool) -> Hand | None:
        """Pick the primary hand from ``hands``.

        ``reacquire`` accepts the hand nearest the last known position at any distance (used
        while Paused and after tracking loss); otherwise it must be within ``max_hand_jump``.
        """
        if not hands:
            return None
        if self._last is None:
            best = max(hands, key=lambda h: h.score)
        else:
            lx, ly = self._last

            def gap(h: Hand) -> float:
                return math.hypot(h.landmarks[0].x - lx, h.landmarks[0].y - ly)

            best = min(hands, key=gap)
            dist = gap(best)
            if not reacquire and dist > self.cfg.max_hand_jump:
                return None
        w = best.landmarks[0]
        self._last = (w.x, w.y)
        return best
