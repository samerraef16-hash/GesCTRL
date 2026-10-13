"""Start GesCRTL when the user signs in to Windows (spec 004 D5, FR-014).

Off by default. When on, one value is written under the current user's ``Run`` key (no
administrator rights, no service). GesCRTL always starts Paused, so signing in never starts
sending input by itself (constitution I).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "GesCRTL"


class Registry(Protocol):
    def get(self) -> str | None: ...

    def set(self, command: str) -> None: ...

    def delete(self) -> None: ...


class WinRegistry:
    """The real ``HKCU\\...\\Run`` value."""

    def get(self) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, VALUE_NAME)
                return str(value)
        except OSError:
            return None

    def set(self, command: str) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)

    def delete(self) -> None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        except OSError:
            pass  # nothing to remove


def command_line(python: str | None = None) -> str:
    """``"<pythonw.exe>" -m gescrtl``: no console window at sign-in when pythonw.exe exists."""
    exe = Path(python or sys.executable)
    windowless = exe.with_name("pythonw.exe")
    if windowless.exists():
        exe = windowless
    return f'"{exe}" -m gescrtl'


def is_enabled(registry: Registry | None = None) -> bool:
    return (registry or WinRegistry()).get() is not None


def set_enabled(on: bool, registry: Registry | None = None, python: str | None = None) -> bool:
    """Turn start-with-Windows on or off. False if Windows refused (the setting is then wrong
    for the user's eyes only, never for safety: the app still starts Paused)."""
    reg = registry or WinRegistry()
    try:
        if on:
            reg.set(command_line(python))
        else:
            reg.delete()
    except OSError:
        return False
    return True
