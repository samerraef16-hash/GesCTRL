"""Phase 0 feasibility spike (THROWAWAY): camera -> track -> smooth -> map -> cursor.

Only moves the cursor. Never clicks. Ctrl+Alt+Esc stops it.
"""
import argparse
import sys
import threading
import time
from dataclasses import dataclass, field

import winput
from hotkey import EMERGENCY_HOTKEY, EMERGENCY_ID, HotkeyListener
from mapping import AbsoluteMapper, RelativeMapper
from one_euro import OneEuro2D
from tracking import (
    Hand,
    HandTracker,
    LatestFrameGrabber,
    PrimaryHandSelector,
    is_fist,
    palm_center,
)


@dataclass
class FrameResult:
    seq: int
    t_capture_ns: int
    t_pickup_ns: int
    t_infer_ns: int
    t_filter_ns: int
    t_inject_ns: int | None
    hands: list = field(default_factory=list)
    primary: Hand | None = None
    cursor: tuple[int, int] | None = None
    clutched: bool = False


class Pipeline:
    def __init__(self, args):
        self.args = args
        self.tracker = HandTracker(args.model)
        self.selector = PrimaryHandSelector()
        self.smoother = OneEuro2D(args.min_cutoff, args.beta, args.d_cutoff)
        rect = winput.primary_screen_rect()
        if args.mapping == "absolute":
            self.mapper = AbsoluteMapper(rect, args.region)
        else:
            self.mapper = RelativeMapper(rect, args.gain)
        self.cursor = winput.get_cursor_pos()

    def step(self, frame, t_capture_ns: int, seq: int) -> FrameResult:
        t_pickup = time.perf_counter_ns()
        hands = self.tracker.detect(frame, t_capture_ns)
        t_infer = time.perf_counter_ns()
        primary = self.selector.select(hands)
        position = None
        clutched = False
        if primary is not None:
            clutched = is_fist(primary.landmarks)
            x, y = palm_center(primary.landmarks)
            sx, sy = self.smoother(x, y, t_capture_ns / 1e9)
            if self.args.mapping == "absolute":
                if not clutched:
                    position = self.mapper.map(sx, sy)
            else:
                position = self.mapper.map(sx, sy, clutched, self.cursor)
        t_filter = time.perf_counter_ns()
        t_inject = None
        if position is not None:
            self.cursor = position
            if not self.args.no_inject:
                winput.move_cursor_abs(*position)
                t_inject = time.perf_counter_ns()
        return FrameResult(seq, t_capture_ns, t_pickup, t_infer, t_filter, t_inject, hands, primary, position, clutched)

    def close(self) -> None:
        self.tracker.close()


def add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--mapping", choices=["absolute", "relative"], default="absolute")
    p.add_argument("--region", type=float, default=0.6)
    p.add_argument("--gain", type=float, default=2.5)
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--min-cutoff", type=float, default=1.0)
    p.add_argument("--beta", type=float, default=0.007)
    p.add_argument("--d-cutoff", type=float, default=1.0)
    p.add_argument("--model", default="models/hand_landmarker.task")
    p.add_argument("--no-inject", action="store_true")
    p.add_argument("--max-rate", type=float, default=0.0, help="max processed frames/s (0 = unlimited)")


def start_safety(stop: threading.Event) -> HotkeyListener:
    """Registers the emergency hotkey. Exits with code 2 if registration fails."""
    listener = HotkeyListener({EMERGENCY_ID: EMERGENCY_HOTKEY}, lambda _id: stop.set())
    listener.start()
    listener.ready.wait(2.0)
    if listener.failed or not listener.ready.is_set():
        print("ERROR: could not register Ctrl+Alt+Esc (taken by another app?). Not starting.")
        sys.exit(2)
    return listener


def run_loop(args, on_result, duration: float | None, stop: threading.Event) -> None:
    """Shared frame loop used by spike.py and measure.py."""
    grabber = LatestFrameGrabber(args.camera, args.width, args.height, args.fps)
    grabber.start()
    pipeline = Pipeline(args)
    run_loop.camera_actual = grabber.actual
    run_loop.pipeline = pipeline
    seq = 0
    last_proc = 0.0
    t_start = time.perf_counter()
    fps_t, fps_n = t_start, 0
    try:
        while not stop.is_set():
            if duration is not None and time.perf_counter() - t_start >= duration:
                break
            item = grabber.latest(seq)
            if item is None:
                time.sleep(0.001)
                continue
            if args.max_rate > 0 and time.perf_counter() - last_proc < 1.0 / args.max_rate:
                seq = item[0]
                time.sleep(0.001)
                continue
            seq, frame, t_cap = item
            last_proc = time.perf_counter()
            result = pipeline.step(frame, t_cap, seq)
            on_result(result)
            fps_n += 1
            now = time.perf_counter()
            if now - fps_t >= 1.0:
                print(f"{fps_n / (now - fps_t):.1f} FPS", end="\r")
                fps_t, fps_n = now, 0
    finally:
        grabber.stop()
        pipeline.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = parser.parse_args()
    print("DPI:", winput.set_dpi_awareness())
    stop = threading.Event()
    listener = start_safety(stop)
    print("Running. Ctrl+Alt+Esc to stop.")
    try:
        run_loop(args, lambda r: None, None, stop)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        print("\nStopped.")


if __name__ == "__main__":
    main()
