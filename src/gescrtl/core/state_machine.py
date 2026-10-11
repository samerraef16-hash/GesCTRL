"""Application state machine: the only place that decides what a command or gesture means.

Implements the Pointer-Mode subset of ``docs/interaction/interaction-model.md`` (events E2-E11,
E15-E17). The mode menu (E12-E14) is deliberately absent (spec FR-016). Every method returns
the events to emit; ``ReleaseAll`` is part of any transition that leaves Active.
"""

from __future__ import annotations

from gescrtl.core.config import CoreConfig
from gescrtl.core.types import (
    Command,
    CueChanged,
    CueKind,
    Event,
    HintsShown,
    ReleaseAll,
    State,
    StateChanged,
    Sub,
    Warning,
)

POINTER_HINTS = (
    "Pinch: click · hold pinch: drag",
    "Thumb out, tilt: scroll",
    "Flat hand: hold cursor",
    "Keep flat hand 1.5 s: pause",
)
START_HINT = ("Show open palm to start",)


class StateMachine:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self.state = State.PAUSED  # E1: always start Paused
        self.sub = Sub.NONE
        self.hotkey_ok = True
        self.camera_ok = True
        self.camera_cause = ""
        self.armed = True  # the resume gesture only counts after the hand has "re-armed" it
        self.last_toggle_ns: int | None = None
        self._stopped_until_ns: int | None = None

    # -- helpers ---------------------------------------------------------------------------

    def _paused_text(self) -> str:
        return "Paused" if self.camera_ok else "Paused · Camera unavailable"

    def _go(self, state: State, sub: Sub, text: str, reason: str | None = None) -> list[Event]:
        events: list[Event] = []
        if reason is not None:
            events.append(ReleaseAll(reason))
        was_active = self.state is State.ACTIVE
        self.state, self.sub = state, sub
        events.append(StateChanged(state, sub, text))
        if state is not State.ACTIVE and was_active:
            events.append(CueChanged(CueKind.HIDDEN))
        if state is State.ACTIVE and sub is Sub.CLUTCHED:
            events.append(CueChanged(CueKind.CLUTCH))
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
        return [*self._go(State.ACTIVE, Sub.NORMAL, "Pointer"), HintsShown(POINTER_HINTS)]

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
            return self._go(State.ACTIVE, Sub.CLUTCHED, "Pointer · Hold", "clutch")
        return []

    def clutch_end(self) -> list[Event]:
        """E17."""
        if self.state is State.ACTIVE and self.sub is Sub.CLUTCHED:
            return self._go(State.ACTIVE, Sub.NORMAL, "Pointer")
        return []

    def hand_lost(self) -> list[Event]:
        """E8."""
        if self.state is State.ACTIVE:
            return self._go(State.TRACKING_LOST, Sub.HAND_MISSING, "Hand not visible", "hand lost")
        return []

    def hand_back(self) -> list[Event]:
        """E9: automatic return, same mode, no hints."""
        if self.state is State.TRACKING_LOST and self.sub is Sub.HAND_MISSING:
            return self._go(State.ACTIVE, Sub.NORMAL, "Pointer")
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
        if cmd is Command.EXIT:
            was_inactive = self.state is State.INACTIVE
            self.state, self.sub = State.INACTIVE, Sub.NONE
            return (
                [ReleaseAll("exit")]
                if was_inactive
                else [
                    ReleaseAll("exit"),
                    StateChanged(State.INACTIVE, Sub.NONE, ""),
                ]
            )
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
