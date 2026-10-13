"""Setup sessions: calibration and custom gesture enrollment (spec 004 D7, D9).

A session runs while the state machine is in ``Sub.SETUP``. It reads hand features and reports
progress as ``SetupView`` events; it never emits pointer, button, key, or scroll events (FR-017).
The engine owns the state transition and always reports the end with a ``SetupResult``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.types import Event, Hand, Pose


@dataclass(slots=True)
class SetupStep:
    events: list[Event] = field(default_factory=list)
    done: bool = False  # the session finished (successfully or not)
    values: dict[str, object] | None = None  # the result when it succeeded


class SetupSession(Protocol):
    kind: str  # "calibration" or "enroll"

    def start(self, t_ns: int) -> list[Event]:
        """The first progress event."""
        ...

    def update(
        self, feats: Features, raw: Pose, stable: Pose, t_ns: int, hand: Hand | None = None
    ) -> SetupStep: ...

    def bad_frame(self, t_ns: int) -> None:
        """A frame without a usable hand: whatever step is counting must start over."""
        ...


def make_session(
    arg: str, cfg: CoreConfig, existing: tuple[object, ...] = ()
) -> SetupSession | None:
    """Build the session named by a ``START_SETUP`` argument, or None if it is unknown.

    ``calibration`` or ``enroll:<shape|move>:<name>``. ``existing`` are the custom gestures that
    already exist (enrollment refuses a duplicate of one of them).
    """
    if arg == "calibration":
        from gescrtl.core.calibration import CalibrationSession

        return CalibrationSession(cfg)
    if arg.startswith("enroll:"):
        parts = arg.split(":", 2)
        if len(parts) == 3 and parts[1] in ("shape", "move") and parts[2]:
            from gescrtl.core.custom import EnrollmentSession

            return EnrollmentSession(cfg, parts[1], parts[2], existing)  # type: ignore[arg-type]
    return None
