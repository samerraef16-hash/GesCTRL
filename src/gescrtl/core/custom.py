"""Custom gestures: still hand shapes and hand movements (spec 004 D9, ADR 0008).

A *shape* is matched by nearest neighbour on a scale-, rotation- and handedness-invariant
descriptor of the 20 landmarks around the wrist. A *movement* is the path of the palm centre,
compared with dynamic time warping (DTW, which matches paths drawn at different speeds) and
checked against the hand shape at its start. Both kinds need the usual confidence, stable frames,
hold or completion, and a cooldown, never run while a built-in gesture is in progress, and never
send a click, drag, or scroll. Only numbers are stored, never images (FR-027).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from gescrtl.core import mapping
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.poses import PoseClassifier
from gescrtl.core.setup import SetupStep
from gescrtl.core.types import CustomFired, Event, Hand, Mode, Pose, SetupView

_MS = 1_000_000

# Kinds the release ships. Decided from the measured SC-007/SC-008 results (FR-028, task T045).
CUSTOM_KINDS_AVAILABLE: frozenset[str] = frozenset({"shape", "move"})

PATH_POINTS = 32
SHAPE_DIM = 40
SHAPE_FLOOR = 0.25  # the smallest match threshold for a shape
SHAPE_MAX_SPREAD = 0.8  # takes of one shape may not be further apart than this
SHAPE_NEIGHBOUR_RATIO = 0.8  # a match must be this much closer than any other gesture's samples
MOVE_FLOOR = 0.2
MOVE_MAX_SPREAD = 0.2  # mean DTW distance between takes (hand sizes); tuned in the manual session
MOVE_START_SHAPE_MAX = 0.9
MOVE_DURATION_RATIO = 2.0  # accepted duration: 1/ratio .. ratio of the recorded mean
SEG_START_SPEED = 1.0  # hand sizes per second
SEG_END_SPEED = 0.4
SEG_END_MS = 150
SEG_MAX_MS = 2500
SEG_MIN_MS = 250
SEG_MIN_LEN = 1.0  # hand sizes of path length
TAKES = 5
SHAPE_TAKE_MS = 1000
COUNTDOWN_MS = 2000
MOVE_WAIT_MS = 6000
SWIPE_LOOKALIKE_DX = 1.5  # an open-hand horizontal movement this long counts as a swipe


# --- data ---------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CustomGesture:
    name: str
    kind: str  # "shape" or "move"
    action: str  # an allowed action name (core.mapping)
    modes: tuple[str, ...] = ()  # Mode names where it works; empty means every mode
    enabled: bool = True
    samples: tuple[tuple[float, ...], ...] = ()
    threshold: float = 0.0
    created: str = ""

    def works_in(self, mode: Mode) -> bool:
        return not self.modes or mode.name in self.modes


# --- descriptors ------------------------------------------------------------------------------


def shape_descriptor(hand: Hand, aspect: float) -> tuple[float, ...] | None:
    """40 numbers: the 20 landmarks around the wrist, scaled by hand size, turned so the middle
    knuckle is straight up, and mirrored for a left hand so either hand gives the same numbers."""
    lm = hand.landmarks
    if len(lm) != 21:
        return None
    pts = [(p.x * aspect, p.y) for p in lm]
    wx, wy = pts[0]
    vx, vy = pts[9][0] - wx, pts[9][1] - wy
    size = math.hypot(vx, vy)
    if size < 1e-6:
        return None
    phi = -math.atan2(vx, -vy)
    c, s = math.cos(phi), math.sin(phi)
    mirror = -1.0 if hand.handedness == "Left" else 1.0
    out: list[float] = []
    for x, y in pts[1:]:
        qx, qy = (x - wx) / size, (y - wy) / size
        out.append(mirror * (qx * c - qy * s))
        out.append(qx * s + qy * c)
    return tuple(out)


def _dist(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def resample(
    points: Sequence[tuple[float, float]], n: int = PATH_POINTS
) -> list[tuple[float, float]]:
    """``n`` points spaced equally along the path, starting at the first point."""
    lengths = [math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(lengths)
    if total < 1e-9:
        return [points[0]] * n
    out: list[tuple[float, float]] = []
    seg, travelled = 0, 0.0
    for k in range(n):
        target = total * k / (n - 1)
        while seg < len(lengths) - 1 and travelled + lengths[seg] < target:
            travelled += lengths[seg]
            seg += 1
        f = 0.0 if lengths[seg] == 0 else (target - travelled) / lengths[seg]
        f = min(max(f, 0.0), 1.0)
        a, b = points[seg], points[seg + 1]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def dtw(a: Sequence[tuple[float, float]], b: Sequence[tuple[float, float]]) -> float:
    """DTW distance between two paths, divided by the number of steps (units: hand sizes)."""
    n, m = len(a), len(b)
    inf = float("inf")
    prev = [inf] * (m + 1)
    prev[0] = 0.0
    for i in range(1, n + 1):
        cur = [inf] * (m + 1)
        ax, ay = a[i - 1]
        for j in range(1, m + 1):
            bx, by = b[j - 1]
            cost = math.hypot(ax - bx, ay - by)
            cur[j] = cost + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur
    return prev[m] / (n + m)


def pack_move(
    duration_ms: float, path: Sequence[tuple[float, float]], start: Sequence[float]
) -> tuple[float, ...]:
    flat = [v for p in path for v in p]
    return (duration_ms, *flat, *start)


def unpack_move(
    sample: Sequence[float],
) -> tuple[float, list[tuple[float, float]], tuple[float, ...]]:
    path_end = 1 + 2 * PATH_POINTS
    flat = sample[1:path_end]
    path = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]
    return sample[0], path, tuple(sample[path_end:])


# --- movement segmentation --------------------------------------------------------------------


@dataclass(slots=True)
class Segment:
    points: list[tuple[float, float]]  # relative to the start, in hand sizes
    duration_ms: float
    start_shape: tuple[float, ...]
    discarded: bool = False
    open_hand: bool = True  # four fingers extended on every frame (the swipe pose)


class MoveSegmenter:
    """Cuts the stream of palm positions into movements: fast start, slow end."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._prev: tuple[float, float, int] | None = None
        self._points: list[tuple[float, float]] = []
        self._times: list[int] = []
        self._start_shape: tuple[float, ...] = ()
        self._slow_since: int | None = None
        self._discard = False
        self._open = True
        self._active = False
        self._cooldown_until = 0

    @property
    def moving(self) -> bool:
        return self._active

    def discard(self) -> None:
        """A built-in gesture is in progress: the movement in progress does not count."""
        self._discard = True

    def update(
        self,
        anchor: tuple[float, float],
        size: float,
        aspect: float,
        t_ns: int,
        shape: tuple[float, ...],
        open_hand: bool,
    ) -> Segment | None:
        p = (anchor[0] * aspect / size, anchor[1] / size)  # hand sizes, camera-fixed
        prev = self._prev
        self._prev = (p[0], p[1], t_ns)
        if prev is None:
            return None
        dt = (t_ns - prev[2]) / 1e9
        if dt <= 0:
            return None
        speed = math.dist(p, (prev[0], prev[1])) / dt
        if not self._active:
            if speed >= SEG_START_SPEED and t_ns >= self._cooldown_until:
                self._active = True
                self._points = [(prev[0], prev[1]), p]
                self._times = [prev[2], t_ns]
                self._start_shape = shape
                self._slow_since = None
                self._discard = False
                self._open = open_hand
            return None
        self._points.append(p)
        self._times.append(t_ns)
        self._open = self._open and open_hand
        if (t_ns - self._times[0]) / _MS > SEG_MAX_MS:
            self._finish_state(t_ns)
            return None  # too long to be a gesture
        if speed < SEG_END_SPEED:
            if self._slow_since is None:
                self._slow_since = t_ns
            if (t_ns - self._slow_since) / _MS >= SEG_END_MS:
                return self._complete(t_ns)
        else:
            self._slow_since = None
        return None

    def _finish_state(self, t_ns: int) -> None:
        self._active = False
        self._points, self._times = [], []
        self._cooldown_until = t_ns + 300 * _MS

    def _complete(self, t_ns: int) -> Segment | None:
        points, times = self._points, self._times
        end = len(points) - 1
        slow = self._slow_since
        while end > 1 and slow is not None and times[end] > slow:
            end -= 1  # drop the slow tail
        points, times = points[: end + 1], times[: end + 1]
        discarded, shape, open_hand = self._discard, self._start_shape, self._open
        self._finish_state(t_ns)
        duration = (times[-1] - times[0]) / _MS
        length = sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))
        if discarded or duration < SEG_MIN_MS or length < SEG_MIN_LEN:
            return None
        x0, y0 = points[0]
        rel = [(x - x0, y - y0) for x, y in points]
        return Segment(rel, duration, shape, False, open_hand)


# --- matching -----------------------------------------------------------------------------------


def best_shape(
    desc: Sequence[float], gestures: Sequence[CustomGesture]
) -> tuple[CustomGesture | None, float]:
    """The gesture whose samples are nearest to ``desc`` and clearly nearer than the others."""
    nearest: dict[str, float] = {}
    for g in gestures:
        nearest[g.name] = min((_dist(desc, s) for s in g.samples), default=float("inf"))
    if not nearest:
        return None, float("inf")
    name = min(nearest, key=lambda n: nearest[n])
    best = next(g for g in gestures if g.name == name)
    d = nearest[name]
    others = [v for n, v in nearest.items() if n != name]
    if d > best.threshold or (others and d > SHAPE_NEIGHBOUR_RATIO * min(others)):
        return None, d
    return best, d


def best_move(segment: Segment, gestures: Sequence[CustomGesture]) -> CustomGesture | None:
    path = resample(segment.points)
    scored: list[tuple[float, CustomGesture]] = []
    for g in gestures:
        durations = [unpack_move(s)[0] for s in g.samples]
        mean = sum(durations) / len(durations)
        if not (mean / MOVE_DURATION_RATIO <= segment.duration_ms <= mean * MOVE_DURATION_RATIO):
            continue
        best = float("inf")
        for sample in g.samples:
            _, tpath, tstart = unpack_move(sample)
            if _dist(segment.start_shape, tstart) > MOVE_START_SHAPE_MAX:
                continue
            best = min(best, dtw(path, tpath))
        if best <= g.threshold:
            scored.append((best, g))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    if len(scored) > 1 and scored[0][0] > SHAPE_NEIGHBOUR_RATIO * scored[1][0]:
        return None  # two gestures fit about equally well: do nothing
    return scored[0][1]


# --- recognizer (runs inside the engine) -------------------------------------------------------


@dataclass(slots=True)
class CustomResult:
    events: list[Event] = field(default_factory=list)
    freeze: bool = False  # a shape is recognized: hold the cursor like the fist


class CustomRecognizer:
    def __init__(self, cfg: CoreConfig, gestures: Sequence[CustomGesture] = ()) -> None:
        self.cfg = cfg
        self.gestures: tuple[CustomGesture, ...] = tuple(gestures)
        self._segmenter = MoveSegmenter()
        self._last_fire_ns: int | None = None  # the cooldown outlives a reset
        self.reset()

    def set_gestures(self, gestures: Sequence[CustomGesture]) -> None:
        self.gestures = tuple(gestures)
        self.reset()

    def reset(self) -> None:
        self._segmenter.reset()
        self._cand: str | None = None
        self._cand_frames = 0
        self._cand_since_ns = 0
        self._fired = False

    @property
    def active(self) -> bool:
        return self.cfg.custom_gestures_enabled and any(g.enabled for g in self.gestures)

    def _usable(self, mode: Mode, kind: str) -> list[CustomGesture]:
        return [g for g in self.gestures if g.enabled and g.kind == kind and g.works_in(mode)]

    def update(
        self,
        hand: Hand,
        feats: Features,
        raw: Pose,
        stable: Pose,
        busy: bool,
        mode: Mode,
        t_ns: int,
    ) -> CustomResult:
        result = CustomResult()
        if not self.active:
            return result
        desc = shape_descriptor(hand, feats.aspect)
        if desc is None:
            return result
        if busy:
            self._segmenter.discard()
            self._drop_candidate()
        if "move" in CUSTOM_KINDS_AVAILABLE:
            open_hand = all(feats.extended(i) for i in range(4))
            seg = self._segmenter.update(
                feats.anchor, feats.size, feats.aspect, t_ns, desc, open_hand
            )
            if seg is not None and not busy:
                result.events += self._fire_move(seg, mode, t_ns)
        if "shape" in CUSTOM_KINDS_AVAILABLE and not busy:
            self._shape_frame(desc, raw, stable, mode, t_ns, result)
        return result

    # -- shapes -----------------------------------------------------------------------------

    def _drop_candidate(self) -> None:
        self._cand, self._cand_frames, self._fired = None, 0, False

    def _cooled(self, t_ns: int) -> bool:
        last = self._last_fire_ns
        return last is None or t_ns - last >= self.cfg.custom_cooldown_ms * _MS

    def _shape_frame(
        self,
        desc: tuple[float, ...],
        raw: Pose,
        stable: Pose,
        mode: Mode,
        t_ns: int,
        result: CustomResult,
    ) -> None:
        match: CustomGesture | None = None
        if raw is Pose.G1_RELAXED and stable is Pose.G1_RELAXED:  # built-in poses never match
            match, _ = best_shape(desc, self._usable(mode, "shape"))
        if match is None:
            self._drop_candidate()
            return
        if match.name != self._cand:
            self._cand, self._cand_frames, self._cand_since_ns = match.name, 0, t_ns
            self._fired = False
        self._cand_frames += 1
        if self._cand_frames < self.cfg.stable_frames:
            return
        result.freeze = True
        if self._fired or t_ns - self._cand_since_ns < self.cfg.custom_hold_ms * _MS:
            return
        self._fired = True  # one action per hold, even if the cooldown swallows it
        if self._cooled(t_ns):
            self._last_fire_ns = t_ns
            result.events += self._events(match)

    # -- movements --------------------------------------------------------------------------

    def _fire_move(self, seg: Segment, mode: Mode, t_ns: int) -> list[Event]:
        match = best_move(seg, self._usable(mode, "move"))
        if match is None or not self._cooled(t_ns):
            return []
        self._last_fire_ns = t_ns
        return self._events(match)

    def _events(self, g: CustomGesture) -> list[Event]:
        out: list[Event] = [CustomFired(g.name, g.action)]
        out += mapping.events_for(g.action, self.cfg.level_step)
        return out


# --- enrollment ---------------------------------------------------------------------------------


def _spread(samples: Sequence[object], distance: Callable[[Any, Any], float]) -> list[float]:
    """For every take, its mean distance to the other takes: two clusters of takes show up."""
    out = []
    for i, a in enumerate(samples):
        others = [distance(a, b) for j, b in enumerate(samples) if j != i]
        out.append(sum(others) / len(others))
    return out


class EnrollmentSession:
    """Records ``TAKES`` takes of a shape or a movement, then checks and builds the gesture."""

    kind = "enroll"

    def __init__(
        self,
        cfg: CoreConfig,
        gesture_kind: str,
        name: str,
        existing: Sequence[CustomGesture] = (),
    ) -> None:
        self.cfg = cfg
        self.gesture_kind = gesture_kind
        self.name = name
        self.existing = tuple(g for g in existing if g.name != name)
        self._classifier = PoseClassifier(cfg)
        self._segmenter = MoveSegmenter()
        self._takes: list[tuple[float, ...]] = []
        self._phase_start_ns = -1
        self._recording = False
        self._frames: list[tuple[float, ...]] = []
        self._poses: list[Pose] = []
        self._last_view: tuple[str, str, int] | None = None

    # -- protocol ---------------------------------------------------------------------------

    def start(self, t_ns: int) -> list[Event]:
        return self._view("enroll", f"Recording “{self.name}”. Get ready…", 0.0)

    def bad_frame(self, t_ns: int) -> None:
        self._frames, self._poses = [], []
        self._recording = False
        self._phase_start_ns = -1
        self._segmenter.reset()

    def update(
        self, feats: Features, raw: Pose, stable: Pose, t_ns: int, hand: Hand | None = None
    ) -> SetupStep:
        if hand is None:
            return SetupStep()
        desc = shape_descriptor(hand, feats.aspect)
        if desc is None:
            return SetupStep()
        if self._phase_start_ns < 0:
            self._phase_start_ns = t_ns
            self._recording = False
            self._frames, self._poses = [], []
            self._segmenter.reset()
        elapsed = (t_ns - self._phase_start_ns) / _MS
        n = len(self._takes)
        if elapsed < COUNTDOWN_MS:
            left = math.ceil((COUNTDOWN_MS - elapsed) / 1000)
            text = f"Take {n + 1} of {TAKES}: get ready… {left}"
            return SetupStep(self._view("countdown", text, elapsed / COUNTDOWN_MS))
        if self.gesture_kind == "shape":
            return self._shape_take(feats, desc, raw, t_ns, elapsed, n)
        return self._move_take(feats, desc, t_ns, elapsed, n)

    # -- shape takes ------------------------------------------------------------------------

    def _shape_take(
        self, feats: Features, desc: tuple[float, ...], raw: Pose, t_ns: int, elapsed: float, n: int
    ) -> SetupStep:
        self._frames.append(desc)
        self._poses.append(self._classifier.classify(feats) if raw is Pose.NONE else raw)
        length = elapsed - COUNTDOWN_MS
        if length < SHAPE_TAKE_MS:
            text = f"Take {n + 1} of {TAKES}: hold the shape"
            return SetupStep(self._view("record", text, length / SHAPE_TAKE_MS))
        poses, frames = self._poses, self._frames
        self._next_take()
        builtin = [p for p in poses if p is not Pose.G1_RELAXED]
        if len(builtin) > 0.2 * len(poses):
            common = max(set(builtin), key=builtin.count)
            text = f"That looks like the built-in {common.name} gesture. Try a different shape"
            return SetupStep(self._view("retry", text, 0.0))
        mean = tuple(sum(f[i] for f in frames) / len(frames) for i in range(SHAPE_DIM))
        self._takes.append(mean)
        return self._after_take()

    # -- movement takes ---------------------------------------------------------------------

    def _move_take(
        self, feats: Features, desc: tuple[float, ...], t_ns: int, elapsed: float, n: int
    ) -> SetupStep:
        open_hand = all(feats.extended(i) for i in range(4))
        seg = self._segmenter.update(feats.anchor, feats.size, feats.aspect, t_ns, desc, open_hand)
        waited = elapsed - COUNTDOWN_MS
        if seg is None:
            if waited > MOVE_WAIT_MS:
                self._next_take()
                return SetupStep(self._view("retry", "No movement seen. Try that take again", 0.0))
            return SetupStep(
                self._view("record", f"Take {n + 1} of {TAKES}: make the movement", 0.0)
            )
        self._next_take()
        xs = [p[0] for p in seg.points]
        looks_like_swipe = (
            seg.open_hand
            and (max(xs) - min(xs)) >= SWIPE_LOOKALIKE_DX
            and (max(p[1] for p in seg.points) - min(p[1] for p in seg.points))
            <= 0.5 * (max(xs) - min(xs))
        )
        if looks_like_swipe:
            text = "That looks like the open-hand swipe. Use a different movement"
            return SetupStep(self._view("retry", text, 0.0))
        path = resample(seg.points)
        self._takes.append(pack_move(seg.duration_ms, path, seg.start_shape))
        return self._after_take()

    # -- bookkeeping ------------------------------------------------------------------------

    def _next_take(self) -> None:
        self._phase_start_ns = -1
        self._frames, self._poses = [], []
        self._segmenter.reset()

    def _after_take(self) -> SetupStep:
        if len(self._takes) < TAKES:
            n = len(self._takes)
            return SetupStep(self._view("record", f"Take {n} saved. {TAKES - n} to go", n / TAKES))
        return self._finish()

    def _fail(self, text: str) -> SetupStep:
        return SetupStep(self._view("failed", text, 1.0), done=True, values=None)

    def _finish(self) -> SetupStep:
        takes = self._takes
        if self.gesture_kind == "shape":
            spread = _spread(takes, _dist)
            if max(spread) > SHAPE_MAX_SPREAD:
                return self._fail("The takes were too different from each other. Try again")
            threshold = max(1.5 * max(spread), SHAPE_FLOOR)
            for g in self.existing:
                if g.kind != "shape":
                    continue
                gap = min(_dist(a, b) for a in takes for b in g.samples)
                if gap < max(threshold, g.threshold):
                    return self._fail(f"That is too similar to your gesture “{g.name}”")
        else:
            paths = [unpack_move(t)[1] for t in takes]
            spread = _spread(paths, dtw)
            if max(spread) > MOVE_MAX_SPREAD:
                return self._fail("The takes were too different from each other. Try again")
            threshold = max(1.3 * max(spread), MOVE_FLOOR)
            for g in self.existing:
                if g.kind != "move":
                    continue
                gap = min(dtw(p, unpack_move(s)[1]) for p in paths for s in g.samples)
                if gap < max(threshold, g.threshold):
                    return self._fail(f"That is too similar to your gesture “{g.name}”")
        values: dict[str, object] = {
            "name": self.name,
            "kind": self.gesture_kind,
            "samples": [list(t) for t in takes],
            "threshold": round(threshold, 4),
        }
        done = self._view("done", f"“{self.name}” saved", 1.0)
        return SetupStep(done, done=True, values=values)

    def _view(self, step: str, text: str, progress: float) -> list[Event]:
        key = (step, text, round(progress * 20))
        if key == self._last_view:
            return []
        self._last_view = key
        return [SetupView(step, text, progress, None)]
