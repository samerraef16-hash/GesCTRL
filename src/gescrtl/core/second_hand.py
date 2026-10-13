"""The user's second hand in Keyboard Mode: it points at and presses keys like the first hand.

This is the exception to the one-primary-hand rule (constitution v1.3.0, ADR 0007). A hand is
accepted only if it looks like the other hand of the same person: the opposite handedness label,
enough confidence, close to the primary hand (in hand sizes), not a known bystander, and
continuously seen for ``stable_frames`` frames. It only ever types: it never moves the cursor,
changes the state or mode, or makes any other gesture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gescrtl.core import features
from gescrtl.core.config import CoreConfig
from gescrtl.core.poses import PoseClassifier, PoseTracker
from gescrtl.core.types import Hand, Pose


@dataclass(frozen=True, slots=True)
class SecondInput:
    """An accepted second hand on this frame (what the keyboard needs to point and press)."""

    feats: features.Features
    raw: Pose
    stable: Pose


class SecondHand:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self.classifier = PoseClassifier(cfg)
        self.tracker = PoseTracker(cfg)
        self.status = ""  # why the second hand is (not) accepted, for the preview readout
        self.reset()

    def reset(self) -> None:
        self.classifier.reset()
        self.tracker.reset()
        self._last: tuple[float, float] | None = None
        self._count = 0

    def update(
        self,
        primary: Hand,
        primary_feats: features.Features,
        others: tuple[Hand, ...],
        aspect: float,
        bystander: tuple[float, float] | None,
        t_ns: int,
    ) -> SecondInput | None:
        """The accepted second hand, once it has been stable for ``stable_frames`` frames."""
        cfg = self.cfg
        pw = primary_feats.wrist
        near_limit = cfg.second_hand_max_dist * primary_feats.size

        def gap(h: Hand) -> float:
            w = h.landmarks[0]
            return math.hypot((w.x - pw[0]) * aspect, w.y - pw[1])

        if not others:
            self.status = "no second hand in view"
            self.reset()
            return None
        candidates = []
        for h in sorted(others, key=gap):
            if h.score < cfg.min_confidence:
                self.status = f"second hand ignored: low confidence {h.score:.2f}"
            elif h.handedness == primary.handedness:
                self.status = f"second hand ignored: both labelled {h.handedness or '?'}"
            elif gap(h) > near_limit:
                self.status = (
                    f"second hand ignored: too far ({gap(h) / primary_feats.size:.1f} hand sizes,"
                    f" limit {cfg.second_hand_max_dist:.1f})"
                )
            elif self._is_bystander(h, bystander):
                self.status = "second hand ignored: looks like a bystander"
            else:
                candidates.append(h)
        if not candidates:
            self.reset()
            return None
        hand = candidates[0]
        feats = features.compute(hand, aspect)
        if feats is None:
            self.status = "second hand ignored: landmarks unusable"
            self.reset()
            return None
        w = hand.landmarks[0]
        if self._last is not None and math.dist((w.x, w.y), self._last) > cfg.max_hand_jump:
            self.reset()  # a different hand than before: it has to be accepted again
        self._last = (w.x, w.y)
        self._count += 1
        raw = self.classifier.classify(feats)
        stable = self.tracker.update(raw, t_ns)
        if self._count < cfg.stable_frames:
            self.status = "second hand: settling"
            return None
        pinching = stable is Pose.G2_PINCH_INDEX
        self.status = "second hand: pinching" if pinching else "second hand: ready"
        return SecondInput(feats, raw, stable)

    def _is_bystander(self, hand: Hand, bystander: tuple[float, float] | None) -> bool:
        if bystander is None:
            return False
        w = hand.landmarks[0]
        return math.dist((w.x, w.y), bystander) <= self.cfg.max_hand_jump
