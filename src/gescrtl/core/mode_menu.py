"""The mode menu: point at a mode, pinch to choose, fist or timeout to cancel (plan D5).

While it is open nothing is sent to the system (FR-003): it only emits overlay events. The state
machine owns the transition; this class only reports what the user did.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.select import PinchSelector, ScreenPointer
from gescrtl.core.types import (
    Event,
    Mode,
    OverlayKind,
    OverlayPointer,
    OverlayShown,
    PointerStyle,
    Pose,
)

_MS = 1_000_000

# menu item id -> mode; "keyboard" is listed (greyed) but is not a choosable mode yet
MODE_BY_ITEM = {
    "pointer": Mode.POINTER,
    "keyboard": Mode.KEYBOARD,
    "presentation": Mode.PRESENTATION,
    "media": Mode.MEDIA,
}


@dataclass(slots=True)
class MenuResult:
    events: list[Event] = field(default_factory=list)
    chosen: Mode | None = None  # a mode was confirmed with a pinch
    cancelled: bool = False  # fist, or no choice within the timeout


class ModeMenu:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._pointer = ScreenPointer(cfg)
        self._selector = PinchSelector(cfg)
        self._opened_ns = 0
        self._pointed: str | None = None

    def reset(self) -> list[Event]:
        self._pointer.reset()
        self._selector.reset()
        self._pointed = None
        return []

    def open(self, t_ns: int) -> list[Event]:
        self.reset()
        self._opened_ns = t_ns
        return [OverlayShown(OverlayKind.MODE_MENU, highlight="")]

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> MenuResult:
        result = MenuResult()
        if stable is Pose.G5_FIST:
            result.cancelled = True
            return result
        if t_ns - self._opened_ns >= self.cfg.menu_timeout_ms * _MS:
            result.cancelled = True
            return result

        nx, ny = self._pointer.update(feats.anchor, t_ns)
        pointed = layout.hit(
            layout.MODE_MENU_ITEMS, nx, ny, self.cfg.target_margin, current=self._pointed
        )
        if pointed != self._pointed:
            self._pointed = pointed
            result.events.append(OverlayShown(OverlayKind.MODE_MENU, highlight=pointed or ""))
        result.events.append(OverlayPointer(nx, ny, PointerStyle.SELECT))

        chosen = self._selector.update(pointed, raw, stable, t_ns)
        if chosen is not None and MODE_BY_ITEM[chosen] is not Mode.KEYBOARD:
            result.chosen = MODE_BY_ITEM[chosen]
        return result
