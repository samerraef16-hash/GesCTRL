"""Window style helpers: make an overlay never take focus and never intercept clicks."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000

_get = user32.GetWindowLongPtrW
_get.argtypes = [wintypes.HWND, ctypes.c_int]
_get.restype = ctypes.c_ssize_t
_set = user32.SetWindowLongPtrW
_set.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_set.restype = ctypes.c_ssize_t


def make_click_through(hwnd: int) -> None:
    """Add NOACTIVATE | TRANSPARENT | LAYERED | TOOLWINDOW to the window's extended style.

    TOOLWINDOW keeps it out of the taskbar and Alt+Tab (ADR 0003, feedback-hud.md).
    """
    handle = wintypes.HWND(hwnd)
    style = _get(handle, GWL_EXSTYLE)
    style |= WS_EX_NOACTIVATE | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
    _set(handle, GWL_EXSTYLE, style)
