"""The volume / brightness panel, available in every mode (plan D8, FR-021..FR-024).

Point at a slider and pinch, then move the hand up or down: the level changes *relative* to where
the pinch started, 100 % per slider height, in whole ``level_step`` steps and never faster than
``level_max_rate``, so a level can never jump (FR-022). The core never knows the absolute level;
the platform applies the steps and shows the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.select import DwellSelector, PinchSelector, ScreenPointer
from gescrtl.core.types import (
    Event,
    Level,
    LevelStep,
    OverlayKind,
    OverlayPointer,
    OverlayShown,
    PointerStyle,
    Pose,
)

_MS = 1_000_000
_MAX_DT = 0.1  # a stalled camera must not bank a burst of steps

LEVEL_BY_SLIDER = {"volume": Level.VOLUME, "brightness": Level.BRIGHTNESS}
# the +/- targets under and over each slider, for users who cannot drag (dwell or a pinch)
STEP_TARGETS = {
    "volume_up": (Level.VOLUME, 1),
    "volume_down": (Level.VOLUME, -1),
    "brightness_up": (Level.BRIGHTNESS, 1),
    "brightness_down": (Level.BRIGHTNESS, -1),
}
_ALL_TARGETS = tuple(layout.LEVEL_SLIDERS) + tuple(layout.LEVEL_STEP_TARGETS)


@dataclass(slots=True)
class PanelResult:
    events: list[Event] = field(default_factory=list)
    close: bool = False  # fist, or nothing happened within the timeout


class LevelPanel:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._pointer = ScreenPointer(cfg)
        self._selector = PinchSelector(cfg)
        self._dwell = DwellSelector(cfg)
        self._heights = {ident: rect.h for ident, rect in layout.LEVEL_SLIDERS}
        self._clear()
        self._idle_since_ns = 0

    def _clear(self) -> None:
        self._pointed: str | None = None
        self._slider: str | None = None  # the slider being dragged
        self._start_y = 0.0
        self._sent = 0  # percentage points already emitted for this drag
        self._stepper: str | None = None  # a +/- target being repeated
        self._stepper_by_dwell = False
        self._repeat_at_ns = 0
        self._budget = 0.0
        self._last_ns = 0

    def reset(self) -> list[Event]:
        self._pointer.reset()
        self._selector.reset()
        self._dwell.reset()
        self._clear()
        return []

    def open(self, t_ns: int) -> list[Event]:
        self.reset()
        self._idle_since_ns = t_ns
        return [OverlayShown(OverlayKind.LEVELS, highlight="")]

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> PanelResult:
        result = PanelResult()
        if stable is Pose.G5_FIST:
            result.close = True
            return result
        if raw is Pose.G2_PINCH_INDEX or self._dwell.progress > 0:
            self._idle_since_ns = t_ns  # a pinch or a dwell in progress keeps the panel open
        elif t_ns - self._idle_since_ns >= self.cfg.panel_timeout_ms * _MS:
            result.close = True
            return result

        nx, ny = self._pointer.update(feats.anchor, t_ns)
        pointed = layout.hit(_ALL_TARGETS, nx, ny, self.cfg.target_margin, current=self._pointed)
        if self._slider is not None:
            pointed = self._slider  # the drag owns the highlight
        if pointed != self._pointed:
            self._pointed = pointed
            result.events.append(OverlayShown(OverlayKind.LEVELS, highlight=pointed or ""))
        result.events.append(OverlayPointer(nx, ny, PointerStyle.SELECT))

        chosen = self._selector.update(pointed, raw, stable, t_ns)
        by_dwell = False
        if self.cfg.confirm_method == "dwell":
            dwelled = self._dwell.update(pointed, (nx, ny), t_ns)
            if chosen is None and dwelled in STEP_TARGETS:
                chosen, by_dwell = dwelled, True
        if chosen in STEP_TARGETS:
            level, sign = STEP_TARGETS[chosen]
            result.events.append(LevelStep(level, sign * self.cfg.level_step))
            self._stepper, self._stepper_by_dwell = chosen, by_dwell
            self._repeat_at_ns = t_ns + self.cfg.level_repeat_ms * _MS
            self._idle_since_ns = t_ns
        elif chosen is not None:
            self._slider, self._start_y = chosen, ny
            self._sent, self._budget, self._last_ns = 0, 0.0, t_ns
        elif raw is not Pose.G2_PINCH_INDEX:
            self._slider = None  # released: the change stops
        if self._slider is not None:
            result.events += self._drag(ny, t_ns)
        result.events += self._repeat(raw, pointed, chosen, t_ns)
        return result

    def _repeat(self, raw: Pose, pointed: str | None, chosen: str | None, t_ns: int) -> list[Event]:
        stepper = self._stepper
        if stepper is None:
            return []
        holding = self._stepper_by_dwell or raw is Pose.G2_PINCH_INDEX
        if not holding or pointed != stepper:
            self._stepper = None
            return []
        if chosen is not None or t_ns < self._repeat_at_ns:
            return []
        self._idle_since_ns = t_ns
        interval = self.cfg.level_repeat_ms * _MS
        self._repeat_at_ns += interval
        if self._repeat_at_ns <= t_ns:  # a stalled camera must not cause a burst
            self._repeat_at_ns = t_ns + interval
        level, sign = STEP_TARGETS[stepper]
        return [LevelStep(level, sign * self.cfg.level_step)]

    def _drag(self, ny: float, t_ns: int) -> list[Event]:
        assert self._slider is not None
        cfg = self.cfg
        dt = min((t_ns - self._last_ns) / 1e9, _MAX_DT)
        self._last_ns = t_ns
        cap = cfg.level_max_rate * _MAX_DT
        self._budget = min(self._budget + cfg.level_max_rate * dt, cap)
        wanted = (self._start_y - ny) / self._heights[self._slider] * 100.0 * cfg.level_drag_gain
        pending = wanted - self._sent
        step = cfg.level_step
        n = min(int(abs(pending) / step), int(self._budget / step))
        if n <= 0:
            return []
        direction = 1 if pending > 0 else -1
        self._budget -= n * step
        self._sent += direction * n * step
        level = LEVEL_BY_SLIDER[self._slider]
        return [LevelStep(level, direction * step) for _ in range(n)]
