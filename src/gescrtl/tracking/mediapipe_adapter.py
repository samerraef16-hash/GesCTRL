"""MediaPipe Hand Landmarker wrapped to produce project-owned HandFrame types (ADR 0001).

Nothing outside this module knows about MediaPipe, so the tracker can be replaced without
touching gesture logic (constitution VII).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2

from gescrtl.core.types import Hand, HandFrame, Landmark

MODEL_RELATIVE = Path("models") / "hand_landmarker.task"


def _find_model() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[3] / MODEL_RELATIVE, Path.cwd() / MODEL_RELATIVE):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Hand Landmarker model not found at models/hand_landmarker.task. "
        "Run: .\\scripts\\fetch_model.ps1"
    )


class MediaPipeTracker:
    def __init__(self, model_path: Path | None = None, num_hands: int = 2) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        path = model_path or _find_model()
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts_ms = -1
        self.last_track_ns = 0  # time spent in the most recent detect() call

    def detect(self, frame_bgr: Any, t_ns: int) -> HandFrame:
        """Mirror the frame, run the tracker, and return landmarks in the user's view."""
        started = time.perf_counter_ns()
        height, width = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(cv2.flip(frame_bgr, 1), cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        ts_ms = t_ns // 1_000_000
        if ts_ms <= self._last_ts_ms:  # VIDEO mode needs strictly increasing timestamps
            ts_ms = self._last_ts_ms + 1
        self._last_ts_ms = ts_ms
        result = self._landmarker.detect_for_video(image, ts_ms)
        hands = []
        for lms, handed in zip(result.hand_landmarks, result.handedness, strict=False):
            cat = handed[0]
            hands.append(
                Hand(
                    landmarks=tuple(Landmark(p.x, p.y, p.z) for p in lms),
                    handedness=cat.category_name,
                    score=float(cat.score),
                )
            )
        self.last_track_ns = time.perf_counter_ns() - started
        return HandFrame(t_ns=t_ns, hands=tuple(hands), aspect=width / height)

    def close(self) -> None:
        self._landmarker.close()
