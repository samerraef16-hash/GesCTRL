"""Mode controllers: what the hand means in each mode (plan D2).

The engine handles the global gestures (pause, clutch, mode menu, level panel) first and then
hands the frame to the controller of the current mode. Controllers only turn poses and features
into events; they never decide state (constitution III).
"""

from __future__ import annotations

from typing import Protocol

from gescrtl.core.features import Features
from gescrtl.core.pointer import Pointer
from gescrtl.core.types import Event, Pose


class ModeController(Protocol):
    @property
    def busy(self) -> bool:
        """True while an action is in progress; global gestures such as G7 are ignored then."""
        ...

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]: ...

    def reset(self) -> list[Event]:
        """Forget everything in progress. May return events (for example to hide a pointer)."""
        ...


class PointerController:
    """Pointer Mode: the spec 002 pointer, unchanged."""

    def __init__(self, pointer: Pointer) -> None:
        self.pointer = pointer

    @property
    def busy(self) -> bool:
        return self.pointer.busy

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        return self.pointer.update(feats, raw, stable, t_ns)

    def reset(self) -> list[Event]:
        self.pointer.reset()
        return []


class NullController:
    """A mode with no gestures (FR-007: a gesture not defined in the mode does nothing)."""

    @property
    def busy(self) -> bool:
        return False

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        return []

    def reset(self) -> list[Event]:
        return []
