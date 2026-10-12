"""Media/System Mode: point at a big on-screen target and pinch to run it (plan D7, FR-012..FR-016).

Nothing is sent unless a *stable* pinch begins on a pointed target (the shared ``PinchSelector``).
Volume and brightness targets repeat in small steps while the pinch stays on the target; the
screenshot and application-switch targets need a second pinch within ``confirm_window_ms``.
The real cursor never moves in this mode (FR-023).
"""

from __future__ import annotations

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.select import PinchSelector, ScreenPointer
from gescrtl.core.types import (
    Action,
    Event,
    Level,
    LevelStep,
    OverlayHidden,
    OverlayKind,
    OverlayPointer,
    OverlayShown,
    PointerStyle,
    Pose,
    SystemAction,
)

_MS = 1_000_000

ACTIONS = {
    "play_pause": Action.PLAY_PAUSE,
    "prev_track": Action.PREV_TRACK,
    "next_track": Action.NEXT_TRACK,
    "mute": Action.MUTE,
}
CONFIRMED_ACTIONS = {"screenshot": Action.SCREENSHOT, "app_switch": Action.APP_SWITCH}
LEVEL_TARGETS = {
    "volume_down": (Level.VOLUME, -1),
    "volume_up": (Level.VOLUME, 1),
    "brightness_down": (Level.BRIGHTNESS, -1),
    "brightness_up": (Level.BRIGHTNESS, 1),
}


class MediaController:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._pointer = ScreenPointer(cfg)
        self._selector = PinchSelector(cfg)
        self._shown = False
        self._pointed: str | None = None
        self._pending: str | None = None
        self._pending_since_ns = 0
        self._repeat_at_ns = 0

    @property
    def busy(self) -> bool:
        return self._pending is not None or self._selector.held_id is not None

    def reset(self) -> list[Event]:
        self._pointer.reset()
        self._selector.reset()
        self._pointed = None
        self._pending = None
        if self._shown:
            self._shown = False
            return [OverlayHidden(OverlayKind.MEDIA)]
        return []

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        events: list[Event] = []
        if not self._shown:
            self._shown = True
            events.append(self._view())
        if self._pending is not None and (
            stable is Pose.G5_FIST
            or t_ns - self._pending_since_ns >= self.cfg.confirm_window_ms * _MS
        ):
            self._pending = None  # fist or timeout cancels the waiting confirmation
            events.append(self._view())

        nx, ny = self._pointer.update(feats.anchor, t_ns)
        pointed = layout.hit(
            layout.MEDIA_TARGETS, nx, ny, self.cfg.target_margin, current=self._pointed
        )
        if pointed != self._pointed:
            self._pointed = pointed
            events.append(self._view())
        events.append(OverlayPointer(nx, ny, PointerStyle.SELECT))

        chosen = self._selector.update(pointed, raw, stable, t_ns)
        if chosen is not None:
            events += self._choose(chosen, t_ns)
        else:
            events += self._repeat(raw, pointed, t_ns)
        return events

    # -- internals -------------------------------------------------------------------------

    def _view(self) -> OverlayShown:
        return OverlayShown(
            OverlayKind.MEDIA, highlight=self._pointed or "", pending=self._pending or ""
        )

    def _choose(self, ident: str, t_ns: int) -> list[Event]:
        events: list[Event] = []
        waiting = self._pending
        confirmed = waiting == ident  # the same target pinched again inside the window
        if waiting is not None and not confirmed:
            self._pending = None  # choosing something else cancels the confirmation
            events.append(self._view())
        if ident in ACTIONS:
            events.append(SystemAction(ACTIONS[ident]))
        elif ident in LEVEL_TARGETS:
            level, sign = LEVEL_TARGETS[ident]
            events.append(LevelStep(level, sign * self.cfg.level_step))
            self._repeat_at_ns = t_ns + self.cfg.level_repeat_ms * _MS
        elif ident in CONFIRMED_ACTIONS:
            if confirmed:
                self._pending = None
                events.append(SystemAction(CONFIRMED_ACTIONS[ident]))
                events.append(self._view())
            else:
                self._pending, self._pending_since_ns = ident, t_ns
                events.append(self._view())
        return events

    def _repeat(self, raw: Pose, pointed: str | None, t_ns: int) -> list[Event]:
        held = self._selector.held_id
        if held not in LEVEL_TARGETS or raw is not Pose.G2_PINCH_INDEX or pointed != held:
            return []
        if t_ns < self._repeat_at_ns:
            return []
        interval = self.cfg.level_repeat_ms * _MS
        self._repeat_at_ns += interval
        if self._repeat_at_ns <= t_ns:  # a stalled camera must not cause a burst
            self._repeat_at_ns = t_ns + interval
        level, sign = LEVEL_TARGETS[held]
        return [LevelStep(level, sign * self.cfg.level_step)]
