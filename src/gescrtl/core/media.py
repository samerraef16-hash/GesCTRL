"""Media/System Mode: point at a big on-screen target and pinch to run it (plan D7, FR-012..FR-016).

Nothing is sent unless a *stable* pinch begins on a pointed target (the shared ``PinchSelector``)
or, with dwell confirmation, the point rests on a target. The action of every target is the
default of ``core.mapping`` unless the user remapped it (spec 004 D6). Level targets repeat in
small steps while the pinch (or the dwell) stays on the target; screenshot and application switch
need a second confirmation within ``confirm_window_ms``. The real cursor never moves in this
mode (FR-023).
"""

from __future__ import annotations

from gescrtl.core import layout, mapping
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.select import DwellSelector, PinchSelector, ScreenPointer
from gescrtl.core.types import (
    Event,
    LevelStep,
    OverlayHidden,
    OverlayKind,
    OverlayPointer,
    OverlayShown,
    PointerStyle,
    Pose,
)

_MS = 1_000_000


class MediaController:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._pointer = ScreenPointer(cfg)
        self._selector = PinchSelector(cfg)
        self._dwell = DwellSelector(cfg)
        # target id -> action name, from the mapping (defaults reproduce spec 003)
        self._actions = {
            ident: mapping.resolve(cfg.mappings, f"media.t{i}")
            for i, ident in enumerate(mapping.MEDIA_TARGET_IDS)
        }
        self._labels = mapping.grid_labels(cfg.mappings) if cfg.mappings else ()
        self._shown = False
        self._pointed: str | None = None
        self._pending: str | None = None
        self._pending_since_ns = 0
        self._repeat_at_ns = 0
        self._dwell_held: str | None = None  # a level target chosen by dwell, still pointed

    @property
    def busy(self) -> bool:
        return self._pending is not None or self._selector.held_id is not None

    def reset(self) -> list[Event]:
        self._pointer.reset()
        self._selector.reset()
        self._dwell.reset()
        self._pointed = None
        self._pending = None
        self._dwell_held = None
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
        by_dwell = False
        if self.cfg.confirm_method == "dwell":
            dwelled = self._dwell.update(pointed, (nx, ny), t_ns)
            if chosen is None and dwelled is not None:
                chosen, by_dwell = dwelled, True
        if chosen is not None:
            events += self._choose(chosen, t_ns, by_dwell)
        else:
            events += self._repeat(raw, pointed, t_ns)
        return events

    # -- internals -------------------------------------------------------------------------

    def _view(self) -> OverlayShown:
        return OverlayShown(
            OverlayKind.MEDIA,
            highlight=self._pointed or "",
            pending=self._pending or "",
            labels=self._labels,
        )

    def _choose(self, ident: str, t_ns: int, by_dwell: bool) -> list[Event]:
        events: list[Event] = []
        waiting = self._pending
        confirmed = waiting == ident  # the same target pinched again inside the window
        if waiting is not None and not confirmed:
            self._pending = None  # choosing something else cancels the confirmation
            events.append(self._view())
        action = self._actions[ident]
        if action in mapping.CONFIRMED_ACTIONS:
            if confirmed:
                self._pending = None
                events += mapping.events_for(action, self.cfg.level_step)
                events.append(self._view())
            else:
                self._pending, self._pending_since_ns = ident, t_ns
                events.append(self._view())
            return events
        events += mapping.events_for(action, self.cfg.level_step)
        if action in mapping.LEVEL_ACTIONS:
            self._repeat_at_ns = t_ns + self.cfg.level_repeat_ms * _MS
            self._dwell_held = ident if by_dwell else None
        return events

    def _repeat(self, raw: Pose, pointed: str | None, t_ns: int) -> list[Event]:
        held = self._selector.held_id if raw is Pose.G2_PINCH_INDEX else self._dwell_held
        if held is None or pointed != held:
            self._dwell_held = None
            return []
        action = self._actions[held]
        if action not in mapping.LEVEL_ACTIONS or t_ns < self._repeat_at_ns:
            return []
        interval = self.cfg.level_repeat_ms * _MS
        self._repeat_at_ns += interval
        if self._repeat_at_ns <= t_ns:  # a stalled camera must not cause a burst
            self._repeat_at_ns = t_ns + interval
        level, sign = mapping.LEVEL_ACTIONS[action]
        return [LevelStep(level, sign * self.cfg.level_step)]
