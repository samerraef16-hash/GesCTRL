"""Per-stage timing for every tracked frame (FR-032, constitution V).

Only numbers are kept: no image data, ever.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrameTiming:
    t_capture_ns: int  # when the frame was grabbed
    wait_ns: int  # grabbed -> tracking started (queueing)
    track_ns: int  # hand tracking
    engine_ns: int  # pure core
    input_ns: int  # dispatching events (SendInput, UI signals)

    @property
    def total_ns(self) -> int:
        """Capture to input dispatched: the 'internal delay' budgeted at p95 <= 80 ms."""
        return self.wait_ns + self.track_ns + self.engine_ns + self.input_ns


def _percentile(sorted_values: list[int], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, round(q * (len(sorted_values) - 1))))
    return float(sorted_values[idx])


class StageStats:
    """Thread-safe ring buffer of the most recent frame timings."""

    def __init__(self, size: int = 1000) -> None:
        self._samples: deque[FrameTiming] = deque(maxlen=size)
        self._lock = threading.Lock()

    def record(self, timing: FrameTiming) -> None:
        with self._lock:
            self._samples.append(timing)

    def summary(self) -> dict[str, float]:
        with self._lock:
            samples = list(self._samples)
        if not samples:
            return {"frames": 0}
        totals = sorted(s.total_ns for s in samples)
        tracks = sorted(s.track_ns for s in samples)
        span_s = (samples[-1].t_capture_ns - samples[0].t_capture_ns) / 1e9
        fps = (len(samples) - 1) / span_s if span_s > 0 else 0.0
        return {
            "frames": float(len(samples)),
            "fps": fps,
            "delay_p50_ms": _percentile(totals, 0.50) / 1e6,
            "delay_p95_ms": _percentile(totals, 0.95) / 1e6,
            "track_p95_ms": _percentile(tracks, 0.95) / 1e6,
        }
