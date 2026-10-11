"""H2: a stalled camera is reported once, retried every 2 s off the worker thread, and recovered."""

import pytest
from test_worker import FakeClock, FakeInput, FakeTracker

from gescrtl.core.engine import Engine
from gescrtl.core.types import Command, State
from gescrtl.stats import StageStats
from gescrtl.tracking.camera import CameraError

pytest.importorskip("PySide6")
from gescrtl.app import Worker  # noqa: E402

S = 1_000_000_000


class RecoverCamera:
    def __init__(self) -> None:
        self.running = True
        self.last_frame_ns = 0
        self.fail_opens = 0
        self.start_calls = 0

    def start(self) -> None:
        self.start_calls += 1
        if self.fail_opens > 0:
            self.fail_opens -= 1
            raise CameraError("not found")
        self.running = True

    def stop(self) -> None:
        self.running = False

    def latest(self, last_seq):
        return None


def make(engine_state=State.ACTIVE):
    clock = FakeClock()
    cam = RecoverCamera()
    w = Worker(Engine(), FakeInput(), cam, lambda e: None, StageStats(), FakeTracker, clock)
    w._tracker = FakeTracker()
    if engine_state is State.INACTIVE:
        w.engine.command(Command.TURN_OFF, 0)
    return w, cam


def posted(w):
    out = []
    while not w._q.empty():
        out.append(w._q.get_nowait())
    return out


def settle(w):
    if w._reopen is not None:
        w._reopen.join(2)


def test_no_stall_before_one_second():
    w, cam = make()
    w._check_camera(int(0.9 * S))
    assert cam.running and not posted(w)


def test_stall_reports_camera_lost_once_and_stops_the_device():
    w, cam = make()
    w._check_camera(int(1.2 * S))
    assert not cam.running
    assert posted(w) == [(Command.CAMERA_LOST, "stopped sending frames")]
    w._check_camera(int(1.5 * S))  # still waiting for the first retry: nothing more
    assert not posted(w)


def test_retries_every_two_seconds_and_reports_camera_back():
    w, cam = make()
    cam.fail_opens = 1
    w._check_camera(int(1.2 * S))
    posted(w)
    w._check_camera(int(3.0 * S))  # too early (retry due at 3.2 s)
    assert cam.start_calls == 0
    w._check_camera(int(3.3 * S))
    settle(w)
    w._check_camera(int(3.4 * S))  # first retry failed: schedule the next one, no new CameraLost
    assert cam.start_calls == 1 and not posted(w) and not cam.running
    w._check_camera(int(5.3 * S))
    settle(w)
    w._check_camera(int(5.4 * S))
    assert cam.start_calls == 2 and cam.running
    assert posted(w) == [(Command.CAMERA_BACK, "")]
    assert not w._camera_failed


def test_never_retries_while_inactive():
    w, cam = make(State.INACTIVE)
    w._camera_failed = True
    w._check_camera(int(10 * S))
    assert cam.start_calls == 0 and not posted(w)
    assert not w._camera_failed  # turning on later starts fresh


def test_a_healthy_stream_is_never_flagged():
    w, cam = make()
    for step in range(1, 100):
        cam.last_frame_ns = step * int(0.1 * S)  # a frame every 100 ms
        w._check_camera(step * int(0.1 * S) + 1)
    assert cam.running and not posted(w)
