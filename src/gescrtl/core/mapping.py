"""Gesture slots and the actions a user may assign to them (spec 004 D6, FR-012).

A *slot* is one remappable place: a presentation swipe, a thumb direction, or a position on the
Media grid. The default action of every slot is the spec 003 behaviour. An *allowed action* is a
name from ``Action`` or one of the level steps below. Clicks, pause, resume, emergency stop, the
mode menu, the level panel, and turn off are not in this set, so they cannot be assigned and a
settings file that names them is rejected (constitution I).
"""

from __future__ import annotations

from gescrtl.core.types import Action, Event, Level, LevelStep, SystemAction

# level actions repeat while held on the Media grid; elsewhere they step once
LEVEL_ACTIONS: dict[str, tuple[Level, int]] = {
    "VOLUME_UP": (Level.VOLUME, 1),
    "VOLUME_DOWN": (Level.VOLUME, -1),
    "BRIGHTNESS_UP": (Level.BRIGHTNESS, 1),
    "BRIGHTNESS_DOWN": (Level.BRIGHTNESS, -1),
}
# these need a second confirmation on the Media grid (FR-014)
CONFIRMED_ACTIONS = frozenset({"SCREENSHOT", "APP_SWITCH"})

ALLOWED: tuple[str, ...] = tuple(a.name for a in Action) + tuple(LEVEL_ACTIONS)

# Media grid positions, in the order of ``layout.MEDIA_TARGETS``
MEDIA_TARGET_IDS: tuple[str, ...] = (
    "play_pause",
    "prev_track",
    "next_track",
    "volume_down",
    "volume_up",
    "mute",
    "brightness_down",
    "brightness_up",
    "screenshot",
    "app_switch",
)

DEFAULTS: dict[str, str] = {
    "presentation.swipe_right": "SLIDE_NEXT",
    "presentation.swipe_left": "SLIDE_PREV",
    "presentation.thumb_up": "SHOW_START",
    "presentation.thumb_down": "SHOW_END",
    "media.t0": "PLAY_PAUSE",
    "media.t1": "PREV_TRACK",
    "media.t2": "NEXT_TRACK",
    "media.t3": "VOLUME_DOWN",
    "media.t4": "VOLUME_UP",
    "media.t5": "MUTE",
    "media.t6": "BRIGHTNESS_DOWN",
    "media.t7": "BRIGHTNESS_UP",
    "media.t8": "SCREENSHOT",
    "media.t9": "APP_SWITCH",
}
SLOTS: tuple[str, ...] = tuple(DEFAULTS)

LABELS: dict[str, str] = {
    "SLIDE_NEXT": "Next slide",
    "SLIDE_PREV": "Previous slide",
    "SHOW_START": "Start show",
    "SHOW_END": "End show",
    "PLAY_PAUSE": "Play / pause",
    "NEXT_TRACK": "Next track",
    "PREV_TRACK": "Previous track",
    "MUTE": "Mute",
    "SCREENSHOT": "Screenshot",
    "APP_SWITCH": "Switch app",
    "COPY": "Copy",
    "PASTE": "Paste",
    "CUT": "Cut",
    "UNDO": "Undo",
    "REDO": "Redo",
    "SELECT_ALL": "Select all",
    "WIN": "Windows key",
    "ESC": "Escape",
    "MODE_POINTER": "Pointer mode",
    "MODE_PRESENTATION": "Presentation mode",
    "MODE_MEDIA": "Media mode",
    "MODE_KEYBOARD": "Keyboard mode",
    "VOLUME_UP": "Volume +",
    "VOLUME_DOWN": "Volume −",
    "BRIGHTNESS_UP": "Brightness +",
    "BRIGHTNESS_DOWN": "Brightness −",
}

# a Media-grid position's id plus the default label shown when nothing is remapped
MODE_ACTION_TO_MODE = {
    "MODE_POINTER": "POINTER",
    "MODE_PRESENTATION": "PRESENTATION",
    "MODE_MEDIA": "MEDIA",
    "MODE_KEYBOARD": "KEYBOARD",
}


def is_allowed(action: str) -> bool:
    return action in ALLOWED


def is_slot(slot: str) -> bool:
    return slot in DEFAULTS


def validate(slot: str, action: str) -> str | None:
    """None when ``slot`` accepts ``action``, otherwise a short reason."""
    if not is_slot(slot):
        return f"unknown slot {slot!r}"
    if not is_allowed(action):
        return f"{action!r} is not an allowed action"
    return None


def resolve(mappings: tuple[tuple[str, str], ...], slot: str) -> str:
    """The action name for ``slot``: the user's override if valid, else the default."""
    for key, action in mappings:
        if key == slot and is_allowed(action):
            return action
    return DEFAULTS[slot]


def label(action: str) -> str:
    return LABELS.get(action, action.replace("_", " ").title())


def grid_labels(mappings: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    """(target id, label) for every Media grid position, using the resolved actions."""
    return tuple(
        (ident, label(resolve(mappings, f"media.t{i}"))) for i, ident in enumerate(MEDIA_TARGET_IDS)
    )


def events_for(action: str, level_step: int) -> list[Event]:
    """The events one firing of ``action`` produces (a key action, or one level step)."""
    if action in LEVEL_ACTIONS:
        level, sign = LEVEL_ACTIONS[action]
        return [LevelStep(level, sign * level_step)]
    return [SystemAction(Action[action])]
