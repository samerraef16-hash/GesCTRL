"""Worker wiring against a fake camera, tracker and input (no hardware, no Qt event loop)."""

import threading
import time

import pytest
from support.hands import Script

from gescrtl.core.engine import Engine
from gescrtl.core.types import Button, Command, HandFrame, Pose, State
from gescrtl.stats import StageStats
from gescrtl.tracking.camera import CameraError

pytest.importorskip("PySide6")
from gescrtl.app import Worker  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.t = 0

    def __call__(self) -> int:
        return self.t


class FakeInput:
    def __init__(self) -> None:
        self.log: list[tuple] = []
        self.releases = 0
        self.action_supported = True
        self.lock = threading.Lock()

    def move(self, nx: float, ny: float) -> None:
        self.log.append(("move", nx, ny))

    def button_down(self, b: Button) -> None:
        self.log.append(("down", b))

    def button_up(self, b: Button) -> None:
        self.log.append(("up", b))

    def click(self, b: Button) -> None:
        self.log.append(("click", b))

    def scroll(self, d: int) -> None:
        self.log.append(("scroll", d))

    def system_action(self, action) -> bool:
        self.log.append(("action", action))
        return self.action_supported

    def key_stroke(self, key, mods=frozenset()) -> bool:
        if getattr(self, "key_error", False):
            raise OSError("blocked")
        self.log.append(("key", key, mods))
        return True

    def release_all(self) -> None:
        with self.lock:
            self.releases += 1

    def double_click_ms(self) -> int:
        return 500

    def primary_rect(self) -> tuple[int, int, int, int]:
        return (0, 0, 1920, 1080)


class FakeCamera:
    """Serves the script's frames one by one, advancing the shared fake clock."""

    def __init__(self, frames: list[HandFrame], clock: FakeClock, fail_start: str = "") -> None:
        self.frames = frames
        self.clock = clock
        self.running = False
        self.starts = 0
        self.fail_start = fail_start
        self.served = 0
        self.last_frame_ns = 0

    def start(self) -> None:
        if self.fail_start:
            raise CameraError(self.fail_start)
        self.running = True
        self.starts += 1
        self.last_frame_ns = self.clock.t

    def stop(self) -> None:
        self.running = False

    def latest(self, last_seq: int):
        if last_seq >= len(self.frames):
            return None
        self.clock.t = self.frames[last_seq].t_ns
        self.last_frame_ns = self.clock.t
        self.served = last_seq + 1
        return last_seq + 1, self.frames[last_seq], self.frames[last_seq].t_ns

    @property
    def exhausted(self) -> bool:
        return self.served >= len(self.frames)


class FakeTracker:
    def __init__(self, fail_on: int | None = None) -> None:
        self.calls = 0
        self.fail_on = fail_on

    def detect(self, frame: HandFrame, t_ns: int) -> HandFrame:
        self.calls += 1
        if self.fail_on is not None and self.calls == self.fail_on:
            raise RuntimeError("boom")
        return frame

    def close(self) -> None:
        pass


def start_worker(frames, fail_on=None, fail_start=""):
    clock = FakeClock()
    inp = FakeInput()
    cam = FakeCamera(frames, clock, fail_start)
    tracker = FakeTracker(fail_on)
    ui: list = []
    w = Worker(Engine(), inp, cam, ui.append, StageStats(), lambda: tracker, clock)
    w.start()
    return w, inp, cam, ui


def wait_for(pred, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


def resume_and_move_frames():
    s = Script().hold(Pose.G6_OPEN_PALM, 1700, at=(0.5, 0.5))
    s.move(Pose.G1_RELAXED, to=(0.7, 0.6), ms=600)
    return [f for f in s.frames() if isinstance(f, HandFrame)]


def test_worker_resumes_and_moves_the_cursor():
    w, inp, cam, ui = start_worker(resume_and_move_frames())
    try:
        assert wait_for(lambda: cam.exhausted)
        assert wait_for(lambda: any(e[0] == "move" for e in inp.log))
        assert w.engine.state is State.ACTIVE
        assert cam.running
    finally:
        w.stop()
        w.join(3)
    assert inp.releases >= 1  # released on shutdown
    assert not cam.running


def test_emergency_stop_command_pauses_and_releases():
    w, inp, cam, _ui = start_worker(resume_and_move_frames())
    try:
        assert wait_for(lambda: cam.exhausted)
        assert wait_for(lambda: w.engine.state is State.ACTIVE)
        before = inp.releases
        w.post(Command.EMERGENCY_STOP)
        assert wait_for(lambda: w.engine.state is State.PAUSED)
        assert inp.releases > before
    finally:
        w.stop()
        w.join(3)


def test_turn_off_releases_camera_and_turn_on_reopens_it():
    w, _inp, cam, _ui = start_worker(resume_and_move_frames())
    try:
        assert wait_for(lambda: cam.running)
        w.post(Command.TURN_OFF)
        assert wait_for(lambda: not cam.running)
        w.post(Command.TURN_ON)
        assert wait_for(lambda: cam.running and cam.starts == 2)
    finally:
        w.stop()
        w.join(3)


def test_tracker_exception_fails_safe_and_worker_survives():
    w, inp, cam, _ui = start_worker(resume_and_move_frames(), fail_on=40)
    try:
        assert wait_for(lambda: cam.exhausted)
        assert wait_for(lambda: inp.releases >= 1)  # fail-safe released input
        assert wait_for(lambda: w.engine.state is State.PAUSED)
        assert w.is_alive()
    finally:
        w.stop()
        w.join(3)


def test_camera_failure_is_reported_as_camera_unavailable():
    w, _inp, _cam, ui = start_worker([], fail_start="in use by another app")
    try:
        assert wait_for(lambda: any("Camera unavailable" in getattr(e, "hud_text", "") for e in ui))
    finally:
        w.stop()
        w.join(3)


def test_preview_hook_only_fires_when_enabled_and_paused_tracks_every_frame():
    frames = [f for f in Script().hold(Pose.G1_RELAXED, 1000).frames() if isinstance(f, HandFrame)]

    def run_with(preview_on: bool):
        clock = FakeClock()
        tracker = FakeTracker()
        cam = FakeCamera(frames, clock)
        offered: list = []
        w = Worker(Engine(), FakeInput(), cam, lambda e: None, StageStats(), lambda: tracker, clock)
        w.on_preview = lambda frame, hf: offered.append(hf)
        if preview_on:
            w.preview_enabled.set()
        w.start()
        try:
            assert wait_for(lambda: cam.exhausted)
            assert wait_for(lambda: tracker.calls >= 10)
            time.sleep(0.1)
        finally:
            w.stop()
            w.join(3)
        return len(offered), tracker.calls

    off_offered, off_calls = run_with(False)
    on_offered, on_calls = run_with(True)
    assert off_offered == 0
    assert off_calls < len(frames) * 0.5  # Paused: roughly every third frame
    assert on_offered == on_calls == len(frames)  # preview: live, every frame


def test_worker_recording_replays_to_the_same_events(tmp_path):
    from gescrtl.recording import jsonl
    from gescrtl.recording.jsonl import RecordingWriter
    from gescrtl.replay import replay

    frames = resume_and_move_frames()
    clock, inp = FakeClock(), FakeInput()
    cam = FakeCamera(frames, clock)
    path = tmp_path / "rec.jsonl"
    seen: list = []
    w = Worker(Engine(), inp, cam, seen.append, StageStats(), lambda: FakeTracker(), clock)
    w.recorder = RecordingWriter(path)
    w.start()
    try:
        assert wait_for(lambda: cam.exhausted)
        w.post(Command.PAUSE)
        assert wait_for(lambda: w.engine.state is State.PAUSED)
    finally:
        w.stop()
        w.join(3)
    items = list(jsonl.read(path))
    assert 0 < sum(isinstance(i, HandFrame) for i in items) <= len(frames)
    assert any(getattr(i, "cmd", None) is Command.PAUSE for i in items)
    live = [e for e in seen if type(e).__name__ in ("MoveCursor", "Click", "ReleaseAll")]
    replayed = [
        e for _, e in replay(items) if type(e).__name__ in ("MoveCursor", "Click", "ReleaseAll")
    ]
    assert live and [type(e) for e in replayed] == [type(e) for e in live]
    for a, b in zip(live, replayed, strict=True):  # landmarks are stored to 5 decimals
        if hasattr(a, "nx"):
            assert (a.nx, a.ny) == pytest.approx((b.nx, b.ny), abs=1e-3)


def test_worker_applies_new_settings_with_release_first_and_keeps_state():
    import dataclasses

    from gescrtl.core.config import CoreConfig

    w, inp, cam, ui = start_worker(resume_and_move_frames())
    try:
        assert wait_for(lambda: cam.exhausted)
        assert wait_for(lambda: w.engine.state is State.ACTIVE)
        before = inp.releases
        w.apply_config(dataclasses.replace(CoreConfig(), active_region=0.9))
        assert wait_for(lambda: w.engine.cfg.active_region == 0.9)
        assert inp.releases > before
        assert w.engine.state is State.ACTIVE
    finally:
        w.stop()
        w.join(3)


def idle_worker():
    inp = FakeInput()
    ui: list = []
    w = Worker(
        Engine(), inp, FakeCamera([], FakeClock(), ""), ui.append, StageStats(), lambda: None
    )
    return w, inp, ui


def test_system_action_event_reaches_the_input_backend_and_the_hud():
    from gescrtl.core.types import Action, SystemAction

    w, inp, ui = idle_worker()
    w._emit_all([SystemAction(Action.SLIDE_NEXT)])
    assert ("action", Action.SLIDE_NEXT) in inp.log
    assert SystemAction(Action.SLIDE_NEXT) in ui


def test_unsupported_action_shows_a_warning():
    from gescrtl.core.types import Action, SystemAction
    from gescrtl.core.types import Warning as UiWarning

    w, inp, ui = idle_worker()
    inp.action_supported = False
    w._emit_all([SystemAction(Action.SHOW_START)])
    warnings = [e for e in ui if isinstance(e, UiWarning)]
    assert warnings and "not supported" in warnings[0].text


def test_an_exception_in_an_action_is_logged_not_raised_and_later_events_still_run(caplog):
    from gescrtl.core.types import Action, ReleaseAll, SystemAction

    w, inp, ui = idle_worker()

    def boom(action):
        raise OSError("blocked")

    inp.system_action = boom
    with caplog.at_level("ERROR", logger="gescrtl"):
        w._emit_all([SystemAction(Action.MUTE), ReleaseAll("test")])
    assert inp.releases == 1  # the release after the failing action still happened
    assert any("MUTE" in r.getMessage() or "blocked" in r.getMessage() for r in caplog.records)


class FakeLevels:
    def __init__(self, fail: bool = False) -> None:
        self.steps: list[tuple] = []
        self.fail = fail

    def step(self, level, delta) -> None:
        if self.fail:
            raise OSError("no audio device")
        self.steps.append((level, delta))

    def read(self, level):
        return 50

    def stop(self) -> None:
        pass


def test_level_step_event_reaches_the_level_backend_and_the_hud():
    from gescrtl.core.types import Level, LevelStep

    w, inp, ui = idle_worker()
    w.levels = FakeLevels()
    w._emit_all([LevelStep(Level.VOLUME, 2), LevelStep(Level.BRIGHTNESS, -2)])
    assert w.levels.steps == [(Level.VOLUME, 2), (Level.BRIGHTNESS, -2)]
    assert LevelStep(Level.VOLUME, 2) in ui


def test_a_failing_level_backend_is_logged_and_later_events_still_run(caplog):
    from gescrtl.core.types import Level, LevelStep, ReleaseAll

    w, inp, ui = idle_worker()
    w.levels = FakeLevels(fail=True)
    with caplog.at_level("ERROR", logger="gescrtl"):
        w._emit_all([LevelStep(Level.VOLUME, 2), ReleaseAll("x")])
    assert inp.releases == 1 and "level step" in caplog.text


def test_level_steps_without_a_backend_are_ignored():
    from gescrtl.core.types import Level, LevelStep

    w, inp, ui = idle_worker()
    w._emit_all([LevelStep(Level.VOLUME, 2)])
    assert LevelStep(Level.VOLUME, 2) in ui


def typing_frames():
    """Resume, switch to Keyboard Mode with a command, point at a key and pinch it."""
    from support.keyboard import key_cam

    s = Script().hold(Pose.G6_OPEN_PALM, 1500, at=(0.5, 0.5)).hold(Pose.G1_RELAXED, 300)
    x, y = key_cam("k:h")
    s.move(Pose.G1_RELAXED, to=(x, y), ms=500).hold(Pose.G1_RELAXED, 900)
    s.hold(Pose.G2_PINCH_INDEX, 400).hold(Pose.G1_RELAXED, 400)
    return [f for f in s.frames() if isinstance(f, HandFrame)]


def test_typed_keys_reach_the_input_backend():
    w, inp, cam, _ui = start_worker(typing_frames())
    try:
        w.post(Command.SET_MODE, "KEYBOARD")
        assert wait_for(lambda: cam.exhausted)
        assert wait_for(lambda: any(e[0] == "key" for e in inp.log))
        assert [e[1] for e in inp.log if e[0] == "key"] == ["h"]
        assert not [e for e in inp.log if e[0] in ("click", "down", "scroll")]
    finally:
        w.stop()
        w.join(3)


def test_a_failing_key_stroke_never_stops_the_worker():
    w, inp, cam, _ui = start_worker(typing_frames())
    inp.key_error = True
    try:
        w.post(Command.SET_MODE, "KEYBOARD")
        assert wait_for(lambda: cam.exhausted)
        time.sleep(0.2)
        assert w.is_alive() and w.engine.state is State.ACTIVE
    finally:
        w.stop()
        w.join(3)


def test_custom_gestures_and_the_monitor_layout_reach_the_engine():
    import json

    from gescrtl.core.custom import SHAPE_DIM, CustomGesture

    w, _inp, _cam, _ui = start_worker([])
    try:
        gesture = CustomGesture("g", "shape", "MUTE", (), True, ((0.0,) * SHAPE_DIM,), 0.3)
        w.set_custom_gestures((gesture,))
        layout = [{"x": 0, "y": 0, "w": 100, "h": 50, "primary": True, "name": "A"}]
        w.post(Command.DISPLAYS, json.dumps(layout))
        assert wait_for(lambda: w.engine.custom_gestures == (gesture,))
        assert wait_for(lambda: w.engine.displays is not None)
    finally:
        w.stop()
        w.join(3)
