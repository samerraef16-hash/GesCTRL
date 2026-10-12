"""Platform-facing interfaces. Core code never imports this package (constitution VII)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from gescrtl.core.types import Action, Button, Event, Level


class InputBackend(Protocol):
    """Injects OS input. ``release_all`` must be idempotent and safe from any thread."""

    def move(self, nx: float, ny: float) -> None: ...

    def button_down(self, button: Button) -> None: ...

    def button_up(self, button: Button) -> None: ...

    def click(self, button: Button) -> None: ...

    def scroll(self, delta: int) -> None: ...

    def system_action(self, action: Action) -> bool:
        """Send the keys for ``action``. False if it is not supported in the foreground app."""
        ...

    def release_all(self) -> None: ...

    def double_click_ms(self) -> int: ...

    def primary_rect(self) -> tuple[int, int, int, int]:
        """(left, top, width, height) of the primary monitor in pixels."""
        ...


class LevelBackend(Protocol):
    """Changes the system volume and display brightness. Must not block the caller."""

    def step(self, level: Level, delta: int) -> None:
        """Change ``level`` by ``delta`` percentage points (positive = up)."""
        ...

    def read(self, level: Level) -> int | None:
        """The current percentage, or None if that level cannot be controlled here."""
        ...

    def stop(self) -> None: ...


class Overlay(Protocol):
    """Shows state and gesture feedback; must never take focus or intercept clicks."""

    def on_event(self, event: Event) -> None: ...


class Hotkeys(Protocol):
    def start(
        self,
        on_emergency: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_toggle_power: Callable[[], None],
    ) -> bool:
        """Register the shortcuts. Returns False if the emergency shortcut is unavailable."""
        ...

    def stop(self) -> None: ...
