"""Slide-show keys per foreground application (plan D10).

Next/previous slide is Right/Left everywhere (PowerPoint, Google Slides, the Edge PDF viewer).
Starting the show from the current slide and ending it differ per application, so they are only
supported where the shortcut is known; elsewhere ``keys_for`` returns None and the worker shows
"Start/end not supported in this app". Keys always go to the foreground window; this module
never changes focus.
"""

from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from ctypes import wintypes

from gescrtl.core.types import Action

VK_ESCAPE = 0x1B
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_F5 = 0x74
VK_LEFT = 0x25
VK_RIGHT = 0x27

BROWSERS = frozenset({"msedge.exe", "chrome.exe"})

# exe name (lower case) and window title of the foreground window; empty when unknown
Foreground = tuple[str, str]


def keys_for_app(action: Action, exe: str, title: str) -> list[int] | None:
    """The key chord for ``action`` in the application ``exe`` showing ``title``."""
    exe = exe.lower()
    if action is Action.SLIDE_NEXT:
        return [VK_RIGHT]
    if action is Action.SLIDE_PREV:
        return [VK_LEFT]
    if exe == "powerpnt.exe":
        if action is Action.SHOW_START:
            return [VK_SHIFT, VK_F5]  # from the current slide
        if action is Action.SHOW_END:
            return [VK_ESCAPE]
    if exe in BROWSERS and "google slides" in title.lower():
        if action is Action.SHOW_START:
            return [VK_CONTROL, VK_SHIFT, VK_F5]  # present from the current slide
        if action is Action.SHOW_END:
            return [VK_ESCAPE]
    return None


def foreground_window() -> Foreground:
    """Exe file name and title of the foreground window, or ("", "") if it cannot be read."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ("", "")
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    title = buf.value
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    kernel32.OpenProcess.restype = wintypes.HANDLE
    process = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not process:
        return ("", title)
    try:
        size = wintypes.DWORD(len(buf))
        ok = kernel32.QueryFullProcessImageNameW(process, 0, buf, ctypes.byref(size))
        exe = os.path.basename(buf.value).lower() if ok else ""
    finally:
        kernel32.CloseHandle(process)
    return (exe, title)


def make_keys_for(
    lookup: Callable[[], Foreground] = foreground_window,
) -> Callable[[Action], list[int] | None]:
    """A ``keys_for`` for ``WinInput`` that asks the foreground window each time."""

    def keys_for(action: Action) -> list[int] | None:
        exe, title = lookup()
        return keys_for_app(action, exe, title)

    return keys_for
