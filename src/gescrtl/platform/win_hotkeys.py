"""Global hotkeys on a dedicated thread (plan D12).

The emergency callback runs on this thread and must release held input *itself* before
anything is queued, so a stalled worker or camera can never delay the stop (FR-004).
"""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_ESCAPE = 0x1B
VK_P = 0x50
VK_O = 0x4F
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

EMERGENCY_ID, PAUSE_ID, POWER_ID = 1, 2, 3
_MODS = MOD_CONTROL | MOD_ALT

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]


class WinHotkeys:
    """Ctrl+Alt+Esc emergency stop, Ctrl+Alt+P pause/resume, Ctrl+Alt+O turn off/on."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._emergency_ok = False
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._thread_id = 0
        self.unavailable: list[str] = []  # names of non-critical hotkeys that failed

    def start(
        self,
        on_emergency: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_toggle_power: Callable[[], None],
    ) -> bool:
        self._callbacks = {
            EMERGENCY_ID: on_emergency,
            PAUSE_ID: on_toggle_pause,
            POWER_ID: on_toggle_power,
        }
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(2.0)
        return self._emergency_ok

    def _run(self) -> None:
        # Registration must happen on this thread: WM_HOTKEY is posted to the registering thread.
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        registered: list[int] = []
        wanted = {
            EMERGENCY_ID: ("Ctrl+Alt+Esc", VK_ESCAPE),
            PAUSE_ID: ("Ctrl+Alt+P", VK_P),
            POWER_ID: ("Ctrl+Alt+O", VK_O),
        }
        for hk_id, (name, vk) in wanted.items():
            if user32.RegisterHotKey(None, hk_id, _MODS | MOD_NOREPEAT, vk):
                registered.append(hk_id)
            else:
                self.unavailable.append(name)
        self._emergency_ok = EMERGENCY_ID in registered
        self._ready.set()
        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    cb = self._callbacks.get(int(msg.wParam))
                    if cb is not None:
                        try:
                            cb()
                        except Exception:  # never let a callback kill the hotkey loop
                            import logging

                            logging.getLogger(__name__).exception("hotkey callback failed")
        finally:
            for hk_id in registered:
                user32.UnregisterHotKey(None, hk_id)

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(1.0)
