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
    MODE_MENU = auto()  # Active, the mode menu is open (E12)
    LEVEL_PANEL = auto()  # Active, the volume/brightness panel is open


class Mode(Enum):
    POINTER = auto()
    PRESENTATION = auto()
    MEDIA = auto()  # Media/System; "Media" is the short form used in the indicator and menu
    KEYBOARD = auto()  # listed in the menu, not available until spec 004


class OverlayKind(Enum):
    MODE_MENU = auto()
    LEVELS = auto()
    MEDIA = auto()


class PointerStyle(Enum):
    SELECT = auto()  # ring used to point at menu items and action targets
    LASER = auto()  # presentation laser dot


class Action(Enum):
    """Something the platform does for the user (keys), never a pointer or button event."""

    SLIDE_NEXT = auto()
    SLIDE_PREV = auto()
    SHOW_START = auto()
    SHOW_END = auto()
    PLAY_PAUSE = auto()
    NEXT_TRACK = auto()
    PREV_TRACK = auto()
    MUTE = auto()
    SCREENSHOT = auto()
    APP_SWITCH = auto()


class Level(Enum):
    VOLUME = auto()
    BRIGHTNESS = auto()


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
    G9_CALL_ME = auto()  # thumb and pinky out, other fingers curled: opens the level panel
    G10_INDEX_POINT = auto()  # index finger alone: the presentation laser pointer


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
    SET_MODE = auto()  # arg: Mode name (tray fallback for the mode menu)


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


@dataclass(frozen=True, slots=True)
class ModeChanged(Event):
    mode: Mode


@dataclass(frozen=True, slots=True)
class OverlayShown(Event):
    kind: OverlayKind
    highlight: str = ""  # id of the pointed target, "" for none
    pending: str = ""  # id of a target waiting for its second confirmation


@dataclass(frozen=True, slots=True)
class OverlayHidden(Event):
    kind: OverlayKind | None = None  # None hides every overlay, a kind only that one


@dataclass(frozen=True, slots=True)
class OverlayPointer(Event):
    nx: float  # 0..1 across the primary monitor
    ny: float
    style: PointerStyle


@dataclass(frozen=True, slots=True)
class OverlayPointerHidden(Event):
    pass


@dataclass(frozen=True, slots=True)
class SystemAction(Event):
    action: Action


@dataclass(frozen=True, slots=True)
class LevelStep(Event):
    level: Level
    delta: int  # percentage points, positive = up


@dataclass(frozen=True, slots=True)
class LevelReading(Event):
    """The level the system reports after a step (platform to HUD; the core never emits it)."""

    level: Level
    value: int | None  # percent, or None when that level cannot be controlled
