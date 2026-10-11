"""Project-owned types shared by the pure core and its adapters.

Coordinate convention: landmarks are normalized image coordinates in the *user's view*
(already mirrored by the tracking adapter): x grows to the user's right, y grows downward.
All times are integer nanoseconds from an injected, monotonic clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

DEFAULT_ASPECT = 640 / 480  # width / height of the default camera mode


@dataclass(frozen=True, slots=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class Hand:
    """One tracked hand: 21 MediaPipe-ordered landmarks plus a confidence in 0..1."""

    landmarks: tuple[Landmark, ...]
    handedness: str = ""
    score: float = 1.0


@dataclass(frozen=True, slots=True)
class HandFrame:
    t_ns: int
    hands: tuple[Hand, ...] = ()
    aspect: float = DEFAULT_ASPECT


class Button(Enum):
    LEFT = "left"
    RIGHT = "right"


class State(Enum):
    INACTIVE = auto()
    PAUSED = auto()
    ACTIVE = auto()
    TRACKING_LOST = auto()


class Sub(Enum):
    NONE = auto()
    NORMAL = auto()
    CLUTCHED = auto()
    HAND_MISSING = auto()
    CAMERA_UNAVAILABLE = auto()


class Pose(Enum):
    NONE = auto()  # not yet known (no stable reading)
    G1_RELAXED = auto()
    G2_PINCH_INDEX = auto()
    G3_PINCH_MIDDLE = auto()
    G4_THUMBS_UP = auto()
    G5_FIST = auto()
    G6_OPEN_PALM = auto()
    G7_THREE_FINGERS = auto()
    G8_FLAT_HAND = auto()


class CueKind(Enum):
    HIDDEN = auto()
    READY = auto()
    PINCH = auto()
    CLICK = auto()
    DRAG = auto()
    SCROLL = auto()
    CLUTCH = auto()


class Command(Enum):
    RESUME = auto()
    PAUSE = auto()
    TOGGLE_PAUSE = auto()
    EMERGENCY_STOP = auto()
    TURN_OFF = auto()
    TURN_ON = auto()
    TOGGLE_POWER = auto()
    CAMERA_LOST = auto()  # arg: cause text
    CAMERA_BACK = auto()
    HOTKEY_UNAVAILABLE = auto()
    HOTKEY_AVAILABLE = auto()
    EXIT = auto()


@dataclass(frozen=True, slots=True)
class CommandRecord:
    """A command as stored in a recording."""

    t_ns: int
    cmd: Command
    arg: str = ""


# --- events (outputs of the core) -------------------------------------------------------------


class Event:
    """Base class for everything the core emits."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class StateChanged(Event):
    state: State
    sub: Sub
    hud_text: str  # empty means "hide the indicator"


@dataclass(frozen=True, slots=True)
class CueChanged(Event):
    kind: CueKind
    progress: float = 0.0


@dataclass(frozen=True, slots=True)
class MoveCursor(Event):
    nx: float  # 0..1 across the primary monitor
    ny: float


@dataclass(frozen=True, slots=True)
class ButtonDown(Event):
    button: Button


@dataclass(frozen=True, slots=True)
class ButtonUp(Event):
    button: Button


@dataclass(frozen=True, slots=True)
class Click(Event):
    button: Button


@dataclass(frozen=True, slots=True)
class Scroll(Event):
    delta: int  # wheel units; positive scrolls up, negative scrolls down


@dataclass(frozen=True, slots=True)
class ReleaseAll(Event):
    reason: str


@dataclass(frozen=True, slots=True)
class Warning(Event):  # noqa: A001 - deliberate name from the plan
    text: str


@dataclass(frozen=True, slots=True)
class HintsShown(Event):
    items: tuple[str, ...]
