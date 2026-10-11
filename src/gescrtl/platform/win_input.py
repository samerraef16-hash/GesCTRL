"""Win32 input injection via SendInput, plus DPI awareness and monitor geometry (plan D13).

Cursor moves use absolute coordinates normalized over the virtual desktop, computed from the
primary monitor rectangle, so scaling at 100/125/150% does not matter once the process is
per-monitor DPI aware. Elevated windows ignore injected input (UIPI); nothing here crashes then.
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

from gescrtl.core.types import Button

user32 = ctypes.WinDLL("user32", use_last_error=True)
ULONG_PTR = ctypes.c_size_t

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

_DOWN = {Button.LEFT: MOUSEEVENTF_LEFTDOWN, Button.RIGHT: MOUSEEVENTF_RIGHTDOWN}
_UP = {Button.LEFT: MOUSEEVENTF_LEFTUP, Button.RIGHT: MOUSEEVENTF_RIGHTUP}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


assert ctypes.sizeof(INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT


def enable_dpi_awareness() -> str:
    """Call before any window (QApplication) is created. Returns the level reached."""
    try:
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return "per-monitor-v2"
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return "per-monitor"
    except (AttributeError, OSError):
        return "unaware"


def _mouse(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return inp


def _send(*inputs: INPUT) -> bool:
    arr = (INPUT * len(inputs))(*inputs)
    return user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT)) == len(inputs)


class WinInput:
    """InputBackend for Windows. Thread-safe; tracks pressed buttons for ``release_all``."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._down: set[Button] = set()

    # -- geometry ------------------------------------------------------------------------

    def primary_rect(self) -> tuple[int, int, int, int]:
        return (0, 0, user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN))

    @staticmethod
    def _virtual_rect() -> tuple[int, int, int, int]:
        return (
            user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
        )

    def double_click_ms(self) -> int:
        return int(user32.GetDoubleClickTime())

    def cursor_pos(self) -> tuple[int, int]:
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    # -- InputBackend -------------------------------------------------------------------------

    def move(self, nx: float, ny: float) -> None:
        left, top, width, height = self.primary_rect()
        px = left + round(min(max(nx, 0.0), 1.0) * (width - 1))
        py = top + round(min(max(ny, 0.0), 1.0) * (height - 1))
        self.move_px(px, py)

    def move_px(self, px: int, py: int) -> None:
        vx, vy, vw, vh = self._virtual_rect()
        ax = round((px - vx) * 65535 / max(vw - 1, 1))
        ay = round((py - vy) * 65535 / max(vh - 1, 1))
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        with self._lock:
            _send(_mouse(flags, ax, ay))

    def button_down(self, button: Button) -> None:
        with self._lock:
            if button in self._down:
                return
            self._down.add(button)  # mark first: a failed send must still be released later
            _send(_mouse(_DOWN[button]))

    def button_up(self, button: Button) -> None:
        with self._lock:
            if button in self._down:
                self._down.discard(button)
                _send(_mouse(_UP[button]))

    def click(self, button: Button) -> None:
        with self._lock:
            _send(_mouse(_DOWN[button]), _mouse(_UP[button]))

    def scroll(self, delta: int) -> None:
        with self._lock:
            _send(_mouse(MOUSEEVENTF_WHEEL, data=delta))

    def release_all(self) -> None:
        """Idempotent; releases every button this backend still holds down."""
        with self._lock:
            for button in tuple(self._down):
                self._down.discard(button)
                _send(_mouse(_UP[button]))


def _corner_smoke() -> None:
    import time

    print("DPI mode:", enable_dpi_awareness())
    backend = WinInput()
    rect = backend.primary_rect()
    print("Primary monitor rect:", rect)
    for name, (nx, ny) in {
        "top-left": (0.0, 0.0),
        "top-right": (1.0, 0.0),
        "bottom-right": (1.0, 1.0),
        "bottom-left": (0.0, 1.0),
        "center": (0.5, 0.5),
    }.items():
        backend.move(nx, ny)
        time.sleep(0.4)
        print(f"{name:13s} -> cursor at {backend.cursor_pos()}")
        time.sleep(0.6)
    print("Done. The cursor must have touched all four corners.")


if __name__ == "__main__":
    _corner_smoke()
