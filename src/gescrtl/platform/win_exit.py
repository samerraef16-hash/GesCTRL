"""Make sure held mouse buttons are released however the process ends (constitution I)."""

from __future__ import annotations

import atexit
import ctypes
import logging
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes
from types import TracebackType

log = logging.getLogger(__name__)

_HANDLER_TYPE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
_keep_alive: list[object] = []


def install_exit_handlers(release_all: Callable[[], None]) -> None:
    """Call ``release_all`` on normal exit, unhandled exceptions (any thread), and console
    close/Ctrl+C/shutdown events."""

    def safe_release() -> None:
        try:
            release_all()
        except Exception:
            log.exception("release_all failed during exit")

    atexit.register(safe_release)

    previous_hook = sys.excepthook

    def excepthook(
        exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
    ) -> None:
        safe_release()
        previous_hook(exc_type, exc, tb)

    sys.excepthook = excepthook

    previous_thread_hook = threading.excepthook

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        safe_release()
        previous_thread_hook(args)

    threading.excepthook = thread_hook

    def console_handler(_ctrl_type: int) -> bool:
        safe_release()
        return False  # let the default handler end the process

    handler = _HANDLER_TYPE(console_handler)
    _keep_alive.append(handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)
