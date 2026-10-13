"""Monitors on Windows: the layout for the core, and where overlays go (spec 004 D8).

The core wants every monitor as a rectangle in physical pixels (``EnumDisplayMonitors``); Qt
places windows in device-independent pixels. The two are tied together by the device name
(``\\\\.\\DISPLAY1``), which both report. Nothing here runs in the core.
"""

from __future__ import annotations

import ctypes
import json
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

user32 = ctypes.WinDLL("user32", use_last_error=True)

MONITORINFOF_PRIMARY = 1


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


_ENUM_PROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)
user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, _ENUM_PROC, wintypes.LPARAM]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL

Monitor = dict[str, Any]  # {"x", "y", "w", "h", "primary", "name"} in physical pixels


def enumerate_monitors() -> list[Monitor]:
    """Every attached monitor, primary first. Empty if Windows refuses (the caller keeps the
    previous layout)."""
    found: list[Monitor] = []

    def callback(hmon: Any, _hdc: Any, _rect: Any, _lparam: Any) -> bool:
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            found.append(
                {
                    "x": r.left,
                    "y": r.top,
                    "w": r.right - r.left,
                    "h": r.bottom - r.top,
                    "primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                    "name": info.szDevice,
                }
            )
        return True

    user32.EnumDisplayMonitors(None, None, _ENUM_PROC(callback), 0)
    found.sort(key=lambda m: (not m["primary"], m["x"], m["y"]))
    return found


def to_json(monitors: list[Monitor]) -> str:
    return json.dumps(monitors, separators=(",", ":"))


# -- Qt side -------------------------------------------------------------------------------------

_layout: list[Monitor] = []
_overlay_name = ""


def set_layout(monitors: list[Monitor]) -> None:
    global _layout
    _layout = list(monitors)


def layout() -> list[Monitor]:
    return list(_layout)


def set_overlay_monitor(name: str) -> None:
    """The device name of the monitor that shows overlays; empty means the primary monitor."""
    global _overlay_name
    _overlay_name = name


def overlay_monitor() -> str:
    return _overlay_name


def monitor_names() -> list[str]:
    return [m["name"] for m in _layout]


def _screens() -> list[Any]:
    from PySide6.QtGui import QGuiApplication

    return list(QGuiApplication.screens())


def overlay_screen() -> Any:
    """The QScreen overlays are drawn on: the chosen monitor, else the primary one."""
    from PySide6.QtGui import QGuiApplication

    if _overlay_name:
        for screen in _screens():
            if screen.name() == _overlay_name:
                return screen
    return QGuiApplication.primaryScreen()


def desktop_to_qt(nx: float, ny: float) -> tuple[int, int] | None:
    """A cursor position (0..1 over the desktop box) as Qt window coordinates, or None when the
    layout is unknown (the caller then maps over the overlay screen)."""
    if not _layout:
        return None
    left = min(m["x"] for m in _layout)
    top = min(m["y"] for m in _layout)
    width = max(m["x"] + m["w"] for m in _layout) - left
    height = max(m["y"] + m["h"] for m in _layout) - top
    px, py = left + nx * width, top + ny * height
    for m in _layout:
        if m["x"] <= px < m["x"] + m["w"] and m["y"] <= py < m["y"] + m["h"]:
            for screen in _screens():
                if screen.name() == m["name"]:
                    geo = screen.geometry()
                    dpr = screen.devicePixelRatio() or 1.0
                    return round(geo.x() + (px - m["x"]) / dpr), round(
                        geo.y() + (py - m["y"]) / dpr
                    )
    return None


class DisplayWatcher:
    """Tells the core when the monitor layout changes (FR-021): a poll every two seconds, and
    at once when Qt reports a screen being added or removed. Create it on the Qt main thread."""

    def __init__(
        self,
        on_change: Callable[[str], None],
        enumerate_fn: Callable[[], list[Monitor]] = enumerate_monitors,
        interval_ms: int = 2000,
    ) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QGuiApplication

        self._on_change = on_change
        self._enumerate = enumerate_fn
        self._last: list[Monitor] | None = None
        self._timer = QTimer()
        self._timer.timeout.connect(self.poll)
        self._timer.start(interval_ms)
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(lambda _s: self.poll())  # type: ignore[attr-defined]
            app.screenRemoved.connect(lambda _s: self.poll())  # type: ignore[attr-defined]

    def poll(self) -> bool:
        """Report the layout if it changed since the last report. True if it did."""
        monitors = self._enumerate()
        if not monitors or monitors == self._last:
            return False
        self._last = monitors
        set_layout(monitors)
        self._on_change(to_json(monitors))
        return True

    def stop(self) -> None:
        self._timer.stop()
