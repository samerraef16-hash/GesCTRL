"""Pose recognition: raw per-frame pose with pinch hysteresis, then a stability gate.

Recognizers only report poses; the state machine decides what a pose means (constitution III).
"""

from __future__ import annotations

from gescrtl.core.config import CoreConfig
from gescrtl.core.features import PINCH_MIN_REACH, Features
from gescrtl.core.types import Pose

_INDEX, _MIDDLE, _RING, _PINKY = 0, 1, 2, 3


class PoseClassifier:
    """Classifies one frame. Keeps only the pinch hysteresis state."""

    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._pinch: Pose | None = None

    def reset(self) -> None:
        self._pinch = None

    def classify(self, f: Features) -> Pose:
        pinch = self._update_pinch(f)
        if pinch is not None:
            return pinch
        if all(f.curled(i) for i in range(4)):
            return Pose.G4_THUMBS_UP if f.thumbs_up else Pose.G5_FIST
        ext = [f.extended(i) for i in range(4)]
        if all(ext):
            if f.thumb_extended:
                return Pose.G6_OPEN_PALM
            # thumb on its way across the palm (or hand not upright): keep pointing, not clutch
            return Pose.G8_FLAT_HAND if f.flat_hand else Pose.G1_RELAXED
        three = ext[_INDEX] and ext[_MIDDLE] and ext[_RING] and f.curled(_PINKY)
        if three and not f.thumb_extended:
            return Pose.G7_THREE_FINGERS
        return Pose.G1_RELAXED

    def _update_pinch(self, f: Features) -> Pose | None:
        cfg = self.cfg
        idx_ok = f.reach[_INDEX] > PINCH_MIN_REACH
        mid_ok = f.reach[_MIDDLE] > PINCH_MIN_REACH
        if self._pinch is Pose.G2_PINCH_INDEX:
            if idx_ok and f.pinch_index < cfg.pinch_release:
                return self._pinch
            self._pinch = None
        elif self._pinch is Pose.G3_PINCH_MIDDLE:
            if mid_ok and f.pinch_middle < cfg.pinch_release:
                return self._pinch
            self._pinch = None

        idx = f.pinch_index if idx_ok and f.pinch_index < cfg.pinch_enter else None
        mid_ok = mid_ok and not f.open_upright  # straight fingers on an upright hand: not a pinch
        mid = f.pinch_middle if mid_ok and f.pinch_middle < cfg.pinch_enter else None
        if idx is not None and (mid is None or idx <= mid):
            self._pinch = Pose.G2_PINCH_INDEX
        elif mid is not None:
            self._pinch = Pose.G3_PINCH_MIDDLE
        return self._pinch


class PoseTracker:
    """Turns raw poses into a stable pose that changes only after ``stable_frames`` agree."""

    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self.stable: Pose = Pose.NONE
        self.since_ns: int = 0
        self._cand: Pose | None = None
        self._count = 0

    def reset(self) -> None:
        """Forget everything (stable pose becomes NONE)."""
        self.stable = Pose.NONE
        self.since_ns = 0
        self.invalidate()

    def invalidate(self) -> None:
        """A bad frame happened: keep the current stable pose, but any change must start over."""
        self._cand = None
        self._count = 0

    def update(self, raw: Pose, t_ns: int) -> Pose:
        if raw is self.stable:
            self.invalidate()
            return self.stable
        if raw is self._cand:
            self._count += 1
        else:
            self._cand = raw
            self._count = 1
        need = self.cfg.flat_hand_frames if raw is Pose.G8_FLAT_HAND else self.cfg.stable_frames
        if self._count >= need:
            self.stable = raw
            self.since_ns = t_ns
            self.invalidate()
        return self.stable
