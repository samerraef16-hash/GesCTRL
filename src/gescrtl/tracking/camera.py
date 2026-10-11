"""Camera capture: a grabber thread that keeps only the newest frame ("latest frame wins").

Frames stay in memory; nothing here writes an image anywhere (constitution VI).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import cv2


class CameraError(RuntimeError):
    """The camera could not be opened or stopped delivering frames."""

    def __init__(self, cause: str) -> None:
        super().__init__(cause)
        self.cause = cause


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self.index = index
        self.width, self.height, self.fps = width, height, fps
        self._cap: Any = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._frame: Any = None
        self._t_ns = 0
        self._seq = 0
        self._stop = threading.Event()
        self.last_frame_ns = 0  # when the last good frame arrived (or the camera started)

    @property
    def running(self) -> bool:
        return self._thread is not None

    def start(self) -> None:
        """Open the camera (several backends are tried) and start grabbing. Raises CameraError."""
        if self.running:
            return
        self._cap = self._open()
        self._frame = None
        self._seq = 0
        self.last_frame_ns = time.perf_counter_ns()
        self._stop.clear()
        self._thread = threading.Thread(target=self._grab_loop, name="camera", daemon=True)
        self._thread.start()

    def _open(self) -> Any:
        attempts = [
            (cv2.CAP_DSHOW, True),  # DirectShow + MJPG works on the reference camera
            (cv2.CAP_DSHOW, False),
            (cv2.CAP_MSMF, False),
            (cv2.CAP_MSMF, True),
        ]
        opened_any = False
        for backend, mjpg in attempts:
            cap = cv2.VideoCapture(self.index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            opened_any = True
            if mjpg:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            deadline = time.perf_counter() + 2.0
            while time.perf_counter() < deadline:
                ok, frame = cap.read()
                if ok and frame is not None:
                    return cap
                time.sleep(0.05)
            cap.release()
        # opened but never delivered: typically another app holds the camera
        raise CameraError("in use by another app" if opened_any else "not found")

    def _grab_loop(self) -> None:
        cap = self._cap
        while not self._stop.is_set():
            ok, frame = cap.read()
            t_ns = time.perf_counter_ns()
            if not ok or frame is None:
                time.sleep(0.005)
                continue
            with self._lock:
                self._frame, self._t_ns = frame, t_ns
                self._seq += 1
            self.last_frame_ns = t_ns

    def latest(self, last_seq: int) -> tuple[int, Any, int] | None:
        """Return (seq, frame, capture time) if a frame newer than ``last_seq`` exists."""
        with self._lock:
            if self._frame is None or self._seq == last_seq:
                return None
            return self._seq, self._frame, self._t_ns

    def stop(self) -> None:
        """Release the device (one action away, constitution VI)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(1.0)
        self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._frame = None
