"""Application state machine: the only place that decides what a command or gesture means.

Implements ``docs/interaction/interaction-model.md``: pause/resume, loss, clutch (E2-E11,
E15-E17) and, since spec 003, the current mode and the mode menu (E12-E14, FR-001..FR-004) with
the tray fallback ``SET_MODE``. Every method returns the events to emit; ``ReleaseAll`` is part
of any transition that leaves Active, opens the menu, or changes the mode.
"""

from __future__ import annotations

from gescrtl.core.config import CoreConfig
from gescrtl.core.types import (
    Command,
    CueChanged,
    CueKind,
    Event,
    HintsShown,
    Mode,
    ModeChanged,
    OverlayHidden,
    ReleaseAll,
    State,
    StateChanged,
    Sub,
    Warning,
)

# At most four hints, for the mode being entered only (FR-005). Keyboard has none until spec 004.
MODE_HINTS: dict[Mode, tuple[str, ...]] = {
    Mode.POINTER: (
        "Pinch: click · hold: drag",
        "Thumb out, tilt: scroll",
        "Three fingers: modes · call me: volume/brightness",
        "Flat hand 1.5 s: pause",
    ),
    Mode.PRESENTATION: (
        "Index finger: pointer",
        "Open-hand swipe: next / previous",
        "Thumb up 1 s: start show · down: end",
        "Flat hand 1.5 s: pause",
    ),
    Mode.MEDIA: (
        "Point + pinch: run action",
        "Hold pinch on ±: keep changing",
        "Fist: cancel",
        "Flat hand 1.5 s: pause",
    ),
}
MODE_TEXT = {
    Mode.POINTER: "Pointer",
    Mode.PRESENTATION: "Presentation",
    Mode.MEDIA: "Media",  # short form of Media/System
    Mode.KEYBOARD: "Keyboard",
}
START_HINT = ("Show open palm to start",)
MENU_TEXT = "Mode menu"
PANEL_TEXT = "Levels"
_OVERLAY_SUBS = (Sub.MODE_MENU, Sub.LEVEL_PANEL)


class StateMachine:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self.state = State.PAUSED  # E1: always start Paused
        self.sub = Sub.NONE
        self.mode = Mode.POINTER  # every launch starts in Pointer Mode (FR-004)
        self.hotkey_ok = True
        self.camera_ok = True
        self.camera_cause = ""
        self.armed = True  # the resume gesture only counts after the hand has "re-armed" it
        self.last_toggle_ns: int | None = None
        self._stopped_until_ns: int | None = None

    # -- helpers ---------------------------------------------------------------------------

    def mode_text(self) -> str:
        return MODE_TEXT[self.mode]

    def _paused_text(self) -> str:
        return "Paused" if self.camera_ok else "Paused · Camera unavailable"

    def _go(self, state: State, sub: Sub, text: str, reason: str | None = None) -> list[Event]:
        events: list[Event] = []
        if reason is not None:
            events.append(ReleaseAll(reason))
        was_active = self.state is State.ACTIVE
        was_overlay = was_active and self.sub in _OVERLAY_SUBS
        self.state, self.sub = state, sub
        events.append(StateChanged(state, sub, text))
        if was_overlay and not (state is State.ACTIVE and sub in _OVERLAY_SUBS):
            events.append(OverlayHidden())
        if state is not State.ACTIVE and was_active:
            events.append(CueChanged(CueKind.HIDDEN))
        if state is State.ACTIVE and sub is Sub.CLUTCHED and self.mode is Mode.POINTER:
            events.append(CueChanged(CueKind.CLUTCH))  # the cursor cue belongs to Pointer Mode
        if state is not State.PAUSED:
            self._stopped_until_ns = None
        return events

    def _to_paused(self, t_ns: int, reason: str, text: str | None = None) -> list[Event]:
        self.armed = False
        self.last_toggle_ns = t_ns
        return self._go(State.PAUSED, Sub.NONE, text or self._paused_text(), reason)

    # -- time ------------------------------------------------------------------------------

    def tick(self, t_ns: int) -> list[Event]:
        if self._stopped_until_ns is not None and t_ns >= self._stopped_until_ns:
            self._stopped_until_ns = None
            if self.state is State.PAUSED:
                return [StateChanged(State.PAUSED, Sub.NONE, self._paused_text())]
        return []

    # -- startup ---------------------------------------------------------------------------

    def start(self) -> list[Event]:
        return [
            StateChanged(self.state, self.sub, self._paused_text()),
            HintsShown(START_HINT),
        ]

    # -- gestures --------------------------------------------------------------------------

    def resume(self, t_ns: int) -> list[Event]:
        """E2/E3: Paused -> Active · Normal."""
        if self.state is not State.PAUSED:
            return []
        if not self.camera_ok:
            return [Warning("Cannot resume: camera unavailable")]
        if not self.hotkey_ok:
            self.armed = False
            return [
                Warning(
                    "Cannot resume: the emergency shortcut (Ctrl+Alt+Esc) is unavailable. "
                    "Close the app using it, or restart GesCRTL."
                )
            ]
        self.last_toggle_ns = t_ns
        events = self._go(State.ACTIVE, Sub.NORMAL, self.mode_text())
        return [*events, HintsShown(MODE_HINTS[self.mode])]

    def pause(self, t_ns: int, reason: str = "pause") -> list[Event]:
        """E3/E4: Active or Tracking Lost -> Paused; in Paused only ReleaseAll."""
        if self.state is State.INACTIVE:
            return []
        if self.state is State.PAUSED:
            return [ReleaseAll(reason)]
        return self._to_paused(t_ns, reason)

    def clutch_start(self) -> list[Event]:
        """E16."""
        if self.state is State.ACTIVE and self.sub is Sub.NORMAL:
            return self._go(State.ACTIVE, Sub.CLUTCHED, f"{self.mode_text()} · Hold", "clutch")
        return []

    def clutch_end(self) -> list[Event]:
        """E17."""
        if self.state is State.ACTIVE and self.sub is Sub.CLUTCHED:
            return self._go(State.ACTIVE, Sub.NORMAL, self.mode_text())
        return []

    # -- mode menu (E12-E14) and mode changes ----------------------------------------------

    def open_menu(self) -> list[Event]:
        """E12: Active · Normal -> Active · ModeMenuOpen. Releases everything first."""
        if self.state is State.ACTIVE and self.sub is Sub.NORMAL:
            return self._go(State.ACTIVE, Sub.MODE_MENU, MENU_TEXT, "mode menu")
        return []

    def confirm_mode(self, mode: Mode) -> list[Event]:
        """E13: a mode was chosen in the menu. Keyboard is listed but cannot be chosen."""
        if not (self.state is State.ACTIVE and self.sub is Sub.MODE_MENU):
            return []
        if mode is Mode.KEYBOARD:
            return []
        changed = mode is not self.mode
        self.mode = mode
        reason = "mode change" if changed else None
        events = self._go(State.ACTIVE, Sub.NORMAL, self.mode_text(), reason)
        if changed:
            events.append(ModeChanged(mode))
        events.append(HintsShown(MODE_HINTS[mode]))
        return events

    def cancel_menu(self) -> list[Event]:
        """E14: closed with a fist or the timeout; the mode is unchanged."""
        if self.state is State.ACTIVE and self.sub is Sub.MODE_MENU:
            return self._go(State.ACTIVE, Sub.NORMAL, self.mode_text())
        return []

    def open_panel(self) -> list[Event]:
        """Active · Normal -> Active · LevelPanelOpen, from any mode. Releases everything first."""
        if self.state is State.ACTIVE and self.sub is Sub.NORMAL:
            return self._go(State.ACTIVE, Sub.LEVEL_PANEL, PANEL_TEXT, "level panel")
        return []

    def close_panel(self) -> list[Event]:
        """Fist, timeout, or another gesture: back to Normal in the same mode."""
        if self.state is State.ACTIVE and self.sub is Sub.LEVEL_PANEL:
            return self._go(State.ACTIVE, Sub.NORMAL, self.mode_text())
        return []

    def set_mode(self, name: str) -> list[Event]:
        """Tray fallback (FR-025). Active: like a menu choice. Paused / Tracking Lost: the mode
        applies when Active again and the indicator text does not change."""
        try:
            mode = Mode[name]
        except KeyError:
            return []
        if mode is Mode.KEYBOARD or mode is self.mode or self.state is State.INACTIVE:
            return []
        self.mode = mode
        if self.state is State.ACTIVE:
            events = self._go(State.ACTIVE, Sub.NORMAL, self.mode_text(), "mode change")
            return [*events, ModeChanged(mode), HintsShown(MODE_HINTS[mode])]
        return [ModeChanged(mode)]

    def hand_lost(self) -> list[Event]:
        """E8."""
        if self.state is State.ACTIVE:
            return self._go(State.TRACKING_LOST, Sub.HAND_MISSING, "Hand not visible", "hand lost")
        return []

    def hand_back(self) -> list[Event]:
        """E9: automatic return, same mode, no hints."""
        if self.state is State.TRACKING_LOST and self.sub is Sub.HAND_MISSING:
            return self._go(State.ACTIVE, Sub.NORMAL, self.mode_text())
        return []

    # -- commands --------------------------------------------------------------------------

    def on_command(self, cmd: Command, t_ns: int, arg: str = "") -> list[Event]:
        if cmd is Command.TOGGLE_PAUSE:
            cmd = Command.RESUME if self.state is State.PAUSED else Command.PAUSE
        elif cmd is Command.TOGGLE_POWER:
            cmd = Command.TURN_ON if self.state is State.INACTIVE else Command.TURN_OFF

        if cmd is Command.RESUME:
            return self.resume(t_ns)
        if cmd is Command.PAUSE:
            return self.pause(t_ns)
        if cmd is Command.EMERGENCY_STOP:
            return self._emergency_stop(t_ns)
        if cmd is Command.TURN_OFF:
            if self.state is State.INACTIVE:
                return []
            self.camera_ok = True
            return self._go(State.INACTIVE, Sub.NONE, "", "turn off")
        if cmd is Command.TURN_ON:
            if self.state is not State.INACTIVE:
                return []
            self.armed = False
            events = self._go(State.PAUSED, Sub.NONE, "Paused")
            return [*events, HintsShown(START_HINT)]
        if cmd is Command.CAMERA_LOST:
            return self._camera_lost(arg)
        if cmd is Command.CAMERA_BACK:
            return self._camera_back()
        if cmd is Command.HOTKEY_UNAVAILABLE:
            self.hotkey_ok = False
            warn: list[Event] = [
                Warning("Emergency shortcut Ctrl+Alt+Esc could not be registered; staying Paused.")
            ]
            if self.state in (State.ACTIVE, State.TRACKING_LOST):
                warn += self._to_paused(t_ns, "hotkey unavailable")
            return warn
        if cmd is Command.HOTKEY_AVAILABLE:
            self.hotkey_ok = True
            return []
        if cmd is Command.SET_MODE:
            return self.set_mode(arg)
        if cmd is Command.EXIT:
            was_inactive = self.state is State.INACTIVE
            was_overlay = self.state is State.ACTIVE and self.sub in _OVERLAY_SUBS
            self.state, self.sub = State.INACTIVE, Sub.NONE
            if was_inactive:
                return [ReleaseAll("exit")]
            events = [ReleaseAll("exit"), StateChanged(State.INACTIVE, Sub.NONE, "")]
            return [*events, OverlayHidden()] if was_overlay else events
        return []

    def _emergency_stop(self, t_ns: int) -> list[Event]:
        if self.state is State.INACTIVE:
            return []
        if self.state is State.PAUSED:
            return [ReleaseAll("emergency stop")]
        events = self._to_paused(t_ns, "emergency stop", text="Stopped")
        self._stopped_until_ns = t_ns + self.cfg.stopped_display_ms * 1_000_000
        return events

    def _camera_lost(self, cause: str) -> list[Event]:
        text = "Camera unavailable" + (f" · {cause}" if cause else "")
        self.camera_cause = cause
        if self.state is State.INACTIVE:
            return []
        if self.state is State.PAUSED:
            self.camera_ok = False
            return [StateChanged(State.PAUSED, Sub.NONE, self._paused_text())]
        if self.sub is Sub.CAMERA_UNAVAILABLE:
            return []
        return self._go(State.TRACKING_LOST, Sub.CAMERA_UNAVAILABLE, text, "camera lost")

    def _camera_back(self) -> list[Event]:
        if self.state is State.PAUSED and not self.camera_ok:
            self.camera_ok = True
            return [StateChanged(State.PAUSED, Sub.NONE, self._paused_text())]
        if self.state is State.TRACKING_LOST and self.sub is Sub.CAMERA_UNAVAILABLE:
            return self._go(State.TRACKING_LOST, Sub.HAND_MISSING, "Hand not visible")
        return []
