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
        # a hand that stayed in view when the primary vanished: never promoted to primary
        self._bystander: tuple[float, float] | None = None
        self._others: list[tuple[float, float]] = []  # non-primary wrists seen on the last frame

    def forget(self) -> None:
        """Drop the lock entirely (the next hand seen is acquired by confidence)."""
        self._last = None
        self._bystander = None
        self._others = []

    def select(self, hands: tuple[Hand, ...], reacquire: bool) -> Hand | None:
        """Pick the primary hand from ``hands``.

        ``reacquire`` accepts the hand nearest the last known position at any distance (used
        while Paused and after tracking loss); otherwise it must be within ``max_hand_jump``.
        """
        if not hands:
            self._bystander = None  # everything left the view: the next hand is a fresh start
            return None
        if self._last is not None and self._bystander is not None:
            bx, by = self._bystander
            near = [
                h
                for h in hands
                if math.hypot(h.landmarks[0].x - bx, h.landmarks[0].y - by)
                <= self.cfg.max_hand_jump
            ]
            if near:
                w0 = near[0].landmarks[0]
                self._bystander = (w0.x, w0.y)  # it may drift; keep following it
                hands = tuple(h for h in hands if h not in near)
                if not hands:
                    return None
            else:
                self._bystander = None
        if self._last is None:
            best = max(hands, key=lambda h: h.score)
        else:
            lx, ly = self._last

            def gap(h: Hand) -> float:
                return math.hypot(h.landmarks[0].x - lx, h.landmarks[0].y - ly)

            best = min(hands, key=gap)
            dist = gap(best)
            if not reacquire and dist > self.cfg.max_hand_jump:
                w0 = best.landmarks[0]
                if any(math.dist((w0.x, w0.y), o) <= self.cfg.max_hand_jump for o in self._others):
                    self._bystander = (w0.x, w0.y)  # it was already there: someone else's hand
                return None  # (a hand that just jumped is treated as the primary coming back)
        w = best.landmarks[0]
        self._last = (w.x, w.y)
        self._bystander = None
        self._others = [(h.landmarks[0].x, h.landmarks[0].y) for h in hands if h is not best]
        return best
