"""Global emergency-stop hotkey for the Phase 0 spike (THROWAWAY)."""
import ctypes
import threading
import time
from ctypes import wintypes
from typing import Callable

user32 = ctypes.WinDLL("user32", use_last_error=True)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_ESCAPE = 0x1B
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

EMERGENCY_ID = 1
EMERGENCY_HOTKEY = (MOD_CONTROL | MOD_ALT, VK_ESCAPE)

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


class HotkeyListener(threading.Thread):
    """Registers hotkeys on its own thread and calls on_hotkey(id) when one is pressed."""

    def __init__(self, hotkeys: dict[int, tuple[int, int]], on_hotkey: Callable[[int], None]):
        super().__init__(daemon=True)
        self.hotkeys = hotkeys
        self.on_hotkey = on_hotkey
        self.failed: list[int] = []
        self.ready = threading.Event()
        self._registered: list[int] = []

    def run(self) -> None:
        # Registration must happen on this thread: WM_HOTKEY is posted to the registering thread.
        for hk_id, (mods, vk) in self.hotkeys.items():
            if user32.RegisterHotKey(None, hk_id, mods | MOD_NOREPEAT, vk):
                self._registered.append(hk_id)
            else:
                self.failed.append(hk_id)
        self.ready.set()
        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self.on_hotkey(int(msg.wParam))
        finally:
            for hk_id in self._registered:
                user32.UnregisterHotKey(None, hk_id)

    def stop(self) -> None:
        if self.native_id:
            user32.PostThreadMessageW(self.native_id, WM_QUIT, 0, 0)
        self.join(1.0)


if __name__ == "__main__":
    pressed = threading.Event()
    listener = HotkeyListener({EMERGENCY_ID: EMERGENCY_HOTKEY}, lambda _id: pressed.set())
    listener.start()
    listener.ready.wait(2.0)
    if listener.failed:
        print("Registration FAILED for ids:", listener.failed)
    else:
        print("Press Ctrl+Alt+Esc (waiting up to 15 s)...")
        print("Pressed" if pressed.wait(15.0) else "Timed out")
    listener.stop()
