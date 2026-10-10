"""Camera grabber, hand tracker, and hand geometry for the Phase 0 spike (THROWAWAY).

Frames are kept in memory only. Nothing here ever writes an image anywhere.
"""
import math
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np


class LatestFrameGrabber(threading.Thread):
    """Reads the camera continuously and keeps only the newest frame ("latest frame wins")."""

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        super().__init__(daemon=True)
        cap = self._open_working_camera(camera_index, width, height, fps)
        self._cap = cap
        self.actual = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        }
        self._lock = threading.Lock()
        self._frame = None
        self._t_capture_ns = 0
        self._seq = 0
        self._stop_event = threading.Event()

    @staticmethod
    def _open_working_camera(camera_index, width, height, fps):
        """Tries several backends and settings; returns a capture that really delivers a frame."""
        attempts = [
            (cv2.CAP_DSHOW, True),   # DirectShow with MJPG
            (cv2.CAP_DSHOW, False),  # DirectShow, camera defaults
            (cv2.CAP_MSMF, False),   # Media Foundation, camera defaults
            (cv2.CAP_MSMF, True),    # Media Foundation with MJPG
        ]
        for backend, force_mjpg in attempts:
            cap = cv2.VideoCapture(camera_index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            if force_mjpg:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            deadline = time.perf_counter() + 2.0
            while time.perf_counter() < deadline:
                ok, frame = cap.read()
                if ok and frame is not None:
                    print(f"Camera OK (backend={backend}, mjpg={force_mjpg}, "
                          f"{frame.shape[1]}x{frame.shape[0]})")
                    return cap
                time.sleep(0.05)
            cap.release()
        raise RuntimeError(
            "Camera unavailable: no backend delivered frames. Close other apps using the camera "
            "and check Windows Settings > Privacy & security > Camera."
        )

    def run(self) -> None:
        while not self._stop_event.is_set():
            ok, frame = self._cap.read()
            t = time.perf_counter_ns()
            if not ok:
                time.sleep(0.005)
                continue
            with self._lock:
                self._frame = frame
                self._t_capture_ns = t
                self._seq += 1

    def latest(self, last_seq: int):
        """Returns (seq, frame, t_capture_ns) if there is a newer frame, else None."""
        with self._lock:
            if self._frame is None or self._seq == last_seq:
                return None
            return (self._seq, self._frame, self._t_capture_ns)

    def stop(self) -> None:
        self._stop_event.set()
        self.join(1.0)
        self._cap.release()


@dataclass
class Hand:
    landmarks: list  # 21 (x, y, z) tuples, x/y normalized to the mirrored image
    world_landmarks: list | None
    handedness: str
    handedness_score: float


class HandTracker:
    def __init__(self, model_path: str = "models/hand_landmarker.task", num_hands: int = 2):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts_ms = -1

    def detect(self, frame_bgr, t_ns: int) -> list:
        frame = cv2.flip(frame_bgr, 1)  # mirror
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        ts_ms = t_ns // 1_000_000
        if ts_ms <= self._last_ts_ms:
            ts_ms = self._last_ts_ms + 1
        self._last_ts_ms = ts_ms
        result = self._landmarker.detect_for_video(image, ts_ms)
        hands = []
        for i, lms in enumerate(result.hand_landmarks):
            world = None
            if result.hand_world_landmarks and i < len(result.hand_world_landmarks):
                world = [(p.x, p.y, p.z) for p in result.hand_world_landmarks[i]]
            cat = result.handedness[i][0]
            hands.append(
                Hand(
                    landmarks=[(p.x, p.y, p.z) for p in lms],
                    world_landmarks=world,
                    handedness=cat.category_name,
                    handedness_score=float(cat.score),
                )
            )
        return hands

    def close(self) -> None:
        self._landmarker.close()


# ---------------------------------------------------------------- geometry (2D, x/y only)

def _dist(lms, a: int, b: int) -> float:
    return math.hypot(lms[a][0] - lms[b][0], lms[a][1] - lms[b][1])


def palm_center(lms) -> tuple[float, float]:
    idx = (0, 5, 9, 13, 17)
    return (sum(lms[i][0] for i in idx) / 5.0, sum(lms[i][1] for i in idx) / 5.0)


def hand_size(lms) -> float:
    return _dist(lms, 0, 9)


def pinch_ratio(lms, tip: int = 8) -> float:
    return _dist(lms, 4, tip) / max(hand_size(lms), 1e-6)


def is_fist(lms) -> bool:
    return all(_dist(lms, tip, 0) < _dist(lms, pip, 0) for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)))


class PrimaryHandSelector:
    """Keeps following one hand: highest score first, then nearest palm center."""

    def __init__(self):
        self.last: tuple[float, float] | None = None

    def reset(self) -> None:
        self.last = None

    def select(self, hands):
        if not hands:
            return None
        if self.last is None:
            chosen = max(hands, key=lambda h: h.handedness_score)
        else:
            lx, ly = self.last
            chosen = min(
                hands,
                key=lambda h: math.hypot(palm_center(h.landmarks)[0] - lx, palm_center(h.landmarks)[1] - ly),
            )
        self.last = palm_center(chosen.landmarks)
        return chosen


if __name__ == "__main__":
    grabber = LatestFrameGrabber()
    grabber.start()
    tracker = HandTracker()
    seq, processed, with_hand = 0, 0, 0
    t0 = time.perf_counter()
    while processed < 150:
        item = grabber.latest(seq)
        if item is None:
            time.sleep(0.001)
            continue
        seq, frame, t_ns = item
        hands = tracker.detect(frame, t_ns)
        processed += 1
        with_hand += 1 if hands else 0
    elapsed = time.perf_counter() - t0
    print(f"FPS: {processed / elapsed:.1f}; frames with a hand: {with_hand}/{processed}")
    tracker.close()
    grabber.stop()
