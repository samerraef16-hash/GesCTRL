"""Presentation Mode: laser pointer, slide swipe, and show start/end (plan D6, FR-008..FR-010).

Emits only overlay events and ``SystemAction``; it never moves the real cursor (FR-009).
"""

from __future__ import annotations

from gescrtl.core import mapping
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.select import ScreenPointer
from gescrtl.core.swipe import SwipeDetector
from gescrtl.core.types import (
    Action,
    Event,
    OverlayPointer,
    OverlayPointerHidden,
    PointerStyle,
    Pose,
)

_MS = 1_000_000


class PresentationController:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self.swipe = SwipeDetector(cfg)
        self._laser = ScreenPointer(cfg, cfg.laser_min_cutoff, cfg.laser_beta)
        self._laser_shown = False
        self._laser_last_ns = 0  # last frame with the index finger up
        # show start/end: thumb direction (+1 up, -1 down, 0 neither) with hysteresis
        self._dir = 0
        self._dir_since_ns = 0
        self._show_done = False  # this hold already fired, or was blocked by the cooldown
        self._last_show_ns: int | None = None

    @property
    def busy(self) -> bool:
        return self.swipe.moving or self._dir != 0

    def reset(self) -> list[Event]:
        self.swipe.reset()
        self._laser.reset()
        self._dir = 0
        self._show_done = False
        if self._laser_shown:
            self._laser_shown = False
            return [OverlayPointerHidden()]
        return []

    def bad_frame(self) -> None:
        """A frame without a usable hand: a swipe cannot continue across it."""
        self.swipe.reset()

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        events = self.on_swipe(feats, raw, t_ns)
        events += self._show(feats, stable, t_ns)
        events += self._laser_frame(feats, stable, t_ns)
        return events

    def on_swipe(self, feats: Features, raw: Pose, t_ns: int) -> list[Event]:
        """Swipe only; also fed while the flat hand clutch is on (D2 step 1)."""
        is_open = raw is not Pose.G10_INDEX_POINT and all(feats.extended(i) for i in range(4))
        action = self.swipe.update(t_ns, feats.anchor, feats.size, feats.aspect, is_open)
        if action is None:
            return []
        slot = (
            "presentation.swipe_right" if action is Action.SLIDE_NEXT else "presentation.swipe_left"
        )
        return self._fire(slot)

    def _fire(self, slot: str) -> list[Event]:
        """The events of the action assigned to ``slot`` (the default unless remapped)."""
        return mapping.events_for(mapping.resolve(self.cfg.mappings, slot), self.cfg.level_step)

    # -- show start / end ------------------------------------------------------------------

    def _show(self, feats: Features, stable: Pose, t_ns: int) -> list[Event]:
        cfg = self.cfg
        if stable is not Pose.G4_THUMBS_UP:
            self._dir = 0
            self._show_done = False
            return []
        tilt = feats.thumb_tilt_deg
        direction = self._dir
        if tilt >= cfg.thumb_dir_enter_deg or (direction == 1 and tilt >= cfg.thumb_dir_exit_deg):
            direction = 1
        elif tilt <= -cfg.thumb_dir_enter_deg or (
            direction == -1 and tilt <= -cfg.thumb_dir_exit_deg
        ):
            direction = -1
        else:
            direction = 0
        if direction != self._dir:
            self._dir, self._dir_since_ns = direction, t_ns
            self._show_done = False
        if direction == 0 or self._show_done or t_ns - self._dir_since_ns < cfg.show_hold_ms * _MS:
            return []
        self._show_done = True  # one action per hold, even if the cooldown swallows it
        last = self._last_show_ns
        if last is not None and t_ns - last < cfg.show_cooldown_ms * _MS:
            return []
        self._last_show_ns = t_ns
        return self._fire("presentation.thumb_up" if direction > 0 else "presentation.thumb_down")

    # -- laser ---------------------------------------------------------------------------

    def _laser_frame(self, feats: Features, stable: Pose, t_ns: int) -> list[Event]:
        if stable is Pose.G10_INDEX_POINT:
            self._laser_last_ns = t_ns
            nx, ny = self._laser.update(feats.anchor, t_ns)
            self._laser_shown = True
            return [OverlayPointer(nx, ny, PointerStyle.LASER)]
        grace_over = t_ns - self._laser_last_ns >= self.cfg.laser_grace_ms * _MS
        if self._laser_shown and (stable is Pose.G4_THUMBS_UP or grace_over):
            self._laser_shown = False
            self._laser.reset()
            return [OverlayPointerHidden()]
        return []  # within the grace period the dot stays where it was
