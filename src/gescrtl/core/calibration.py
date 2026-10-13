"""Guided calibration (spec 004 D7, FR-015..FR-017).

Steps: check the camera speed and the hand distance, record the hand at each screen corner,
record an open hand, then five pinches. The result is a set of settings values; the platform
asks the user to keep or discard it. The session only emits ``SetupView`` events.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.setup import SetupStep
from gescrtl.core.types import Event, Hand, Pose, SetupView

_MS = 1_000_000
CHECK_MS = 2000
MIN_FPS = 15.0
HAND_SIZE_MIN = 0.08  # wrist to middle knuckle, in frame heights
HAND_SIZE_MAX = 0.40
CORNER_HOLD_MS = 1000
CORNER_MOVE_MIN = 0.05  # the hand must travel this far (camera units) between corners
OPEN_MS = 2000
PINCHES_NEEDED = 5
PINCH_MIN_FRAMES = 3
MIN_SPAN = 0.08  # open and closed pinch ratios must differ by at least this
MIN_REACH_SPAN = 0.05  # the corner positions must span at least this much of the camera view

_CORNERS = (
    ("top-left", (0.0, 0.0)),
    ("top-right", (1.0, 0.0)),
    ("bottom-right", (1.0, 1.0)),
    ("bottom-left", (0.0, 1.0)),
)


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[round(p * (len(ordered) - 1))]


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


@dataclass(slots=True)
class _Check:
    first_ns: int = -1
    last_ns: int = 0
    frames: int = 0
    sizes: list[float] | None = None


class CalibrationSession:
    kind = "calibration"

    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._step = "check"
        self._open_values: list[float] = []
        self._pinch_mins: list[float] = []
        self._last_view: tuple[str, str, int] | None = None
        self._restart_check()
        self._corner = 0
        self._anchors: list[tuple[float, float]] = []
        self._ref: tuple[float, float] | None = None
        self._since_ns = 0
        self._origin: tuple[float, float] | None = None  # where the hand was before this corner
        self._restart_pinch()

    # -- protocol -----------------------------------------------------------------------------

    def start(self, t_ns: int) -> list[Event]:
        return self._view("check", "Hold your open hand up to the camera", 0.0, None)

    def bad_frame(self, t_ns: int) -> None:
        """The hand left the view: the step in progress must start over."""
        if self._step == "check":
            self._restart_check()
        elif self._step == "reach":
            self._ref = None
        elif self._step == "open":
            self._open_start_ns = -1
            self._open_values = []
        elif self._step == "pinch":
            self._run = 0
            self._run_min = 9.0

    def update(
        self, feats: Features, raw: Pose, stable: Pose, t_ns: int, hand: Hand | None = None
    ) -> SetupStep:
        if self._step == "check":
            return self._check(feats, t_ns)
        if self._step == "reach":
            return self._reach(feats, t_ns)
        if self._step == "open":
            return self._open(feats, raw, t_ns)
        return self._pinch(feats, raw, t_ns)

    # -- check --------------------------------------------------------------------------------

    def _restart_check(self) -> None:
        self._check_state = _Check(sizes=[])

    def _check(self, feats: Features, t_ns: int) -> SetupStep:
        c = self._check_state
        if c.first_ns < 0:
            c.first_ns = t_ns
        c.last_ns = t_ns
        c.frames += 1
        assert c.sizes is not None
        c.sizes.append(feats.size)
        elapsed = t_ns - c.first_ns
        if elapsed < CHECK_MS * _MS:
            return SetupStep(
                self._view("check", "Checking the camera…", elapsed / (CHECK_MS * _MS))
            )
        fps = (c.frames - 1) / max((c.last_ns - c.first_ns) / 1e9, 1e-6)
        size = sorted(c.sizes)[len(c.sizes) // 2]
        self._restart_check()
        if fps < MIN_FPS:
            text = f"The camera is slow ({fps:.0f} FPS). Add light, then wait…"
            return SetupStep(self._view("check", text, 0.0))
        if size < HAND_SIZE_MIN:
            return SetupStep(self._view("check", "Move your hand closer to the camera", 0.0))
        if size > HAND_SIZE_MAX:
            return SetupStep(self._view("check", "Move your hand back from the camera", 0.0))
        self._step = "reach"
        self._corner = 0
        self._anchors = []
        self._ref = None
        self._origin = feats.anchor
        return SetupStep(self._corner_view(0.0))

    # -- reach --------------------------------------------------------------------------------

    def _corner_view(self, progress: float) -> list[Event]:
        name, target = _CORNERS[self._corner]
        text = f"Point to the {name} corner as far as is comfortable, then hold still"
        return self._view("reach", text, progress, target)

    def _reach(self, feats: Features, t_ns: int) -> SetupStep:
        a = feats.anchor
        if self._ref is None or math.dist(a, self._ref) > self.cfg.pause_still_dist:
            self._ref, self._since_ns = a, t_ns
        held = t_ns - self._since_ns
        assert self._origin is not None
        far_enough = math.dist(a, self._origin) >= CORNER_MOVE_MIN
        if held < CORNER_HOLD_MS * _MS or not far_enough:
            progress = min(held / (CORNER_HOLD_MS * _MS), 1.0) if far_enough else 0.0
            return SetupStep(self._corner_view(progress))
        self._anchors.append(self._ref)
        self._origin = self._ref
        self._ref = None
        self._corner += 1
        if self._corner < len(_CORNERS):
            return SetupStep(self._corner_view(0.0))
        xs = [p[0] for p in self._anchors]
        ys = [p[1] for p in self._anchors]
        if min(max(xs) - min(xs), max(ys) - min(ys)) < MIN_REACH_SPAN:
            self._corner, self._anchors = 0, []
            text = "Those positions were too close together. Reach further for each corner"
            self._origin = a
            return SetupStep(self._view("reach", text, 0.0, _CORNERS[0][1]))
        self._step = "open"
        self._open_start_ns = -1
        self._open_values = []
        return SetupStep(self._view("open", "Show an open hand, fingers apart, and hold it", 0.0))

    # -- open hand and pinches ----------------------------------------------------------------

    def _restart_pinch(self) -> None:
        self._open_start_ns = -1
        self._open_values = []
        self._pinch_mins = []
        self._run = 0
        self._run_min = 9.0

    def _open(self, feats: Features, raw: Pose, t_ns: int) -> SetupStep:
        if self._open_start_ns < 0:
            self._open_start_ns = t_ns
        if raw not in (Pose.G2_PINCH_INDEX, Pose.G3_PINCH_MIDDLE):
            self._open_values.append(feats.pinch_index)
        elapsed = t_ns - self._open_start_ns
        if elapsed < OPEN_MS * _MS:
            progress = elapsed / (OPEN_MS * _MS)
            return SetupStep(self._view("open", "Keep your open hand up", progress))
        self._step = "pinch"
        self._pinch_mins = []
        self._run, self._run_min = 0, 9.0
        return SetupStep(self._pinch_view())

    def _pinch_view(self) -> list[Event]:
        n = len(self._pinch_mins)
        text = f"Pinch thumb and index finger, then open: {n} of {PINCHES_NEEDED}"
        return self._view("pinch", text, n / PINCHES_NEEDED)

    def _pinch(self, feats: Features, raw: Pose, t_ns: int) -> SetupStep:
        if raw is Pose.G2_PINCH_INDEX:
            self._run += 1
            self._run_min = min(self._run_min, feats.pinch_index)
            return SetupStep()
        events: list[Event] = []
        if self._run >= PINCH_MIN_FRAMES:
            self._pinch_mins.append(self._run_min)
            events = self._pinch_view()
        self._run, self._run_min = 0, 9.0
        if len(self._pinch_mins) < PINCHES_NEEDED:
            return SetupStep(events)
        return self._finish()

    # -- result -------------------------------------------------------------------------------

    def _finish(self) -> SetupStep:
        closed = _percentile(self._pinch_mins, 0.9)
        opened = _percentile(self._open_values, 0.1) if self._open_values else 9.0
        if opened - closed < MIN_SPAN:
            self._step = "open"
            self._open_start_ns, self._open_values, self._pinch_mins = -1, [], []
            text = "Pinch and open hand look too alike. Show the open hand again, fingers apart"
            return SetupStep(self._view("open", text, 0.0))
        span = opened - closed
        enter = _clamp(closed + 0.35 * span, 0.05, 0.5)
        release = _clamp(closed + 0.65 * span, 0.1, 0.6)
        if release <= enter + 0.02:
            release = min(enter + 0.05, 0.6)
            enter = min(enter, release - 0.02)
        xs = [p[0] for p in self._anchors]
        ys = [p[1] for p in self._anchors]
        values: dict[str, object] = {
            "active_region": round(_clamp(min(max(xs) - min(xs), max(ys) - min(ys)), 0.2, 1.0), 3),
            "active_center_x": round(_clamp((max(xs) + min(xs)) / 2, 0.2, 0.8), 3),
            "active_center_y": round(_clamp((max(ys) + min(ys)) / 2, 0.2, 0.8), 3),
            "pinch_enter": round(enter, 3),
            "pinch_release": round(release, 3),
        }
        done = self._view("done", "Calibration finished", 1.0)
        return SetupStep(done, done=True, values=values)

    # -- view ---------------------------------------------------------------------------------

    def _view(
        self, step: str, text: str, progress: float, target: tuple[float, float] | None = None
    ) -> list[Event]:
        key = (step, text, round(progress * 20))
        if key == self._last_view:
            return []
        self._last_view = key
        return [SetupView(step, text, progress, target)]
