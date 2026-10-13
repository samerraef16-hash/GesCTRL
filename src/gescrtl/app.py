"""Composition root: wires camera, tracker, core engine, input, HUD, tray and hotkeys (plan D12).

Threads: Qt main (HUD, tray) / worker (capture -> track -> engine -> input) / hotkeys.
Commands reach the worker through a queue; the worker waits at most a few ms for it, so
commands are handled even if the camera stalls.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import queue
import sys
import threading
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import cv2
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from gescrtl.core import mapping
from gescrtl.core.config import CoreConfig
from gescrtl.core.custom import CustomGesture
from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    ButtonDown,
    ButtonUp,
    Click,
    Command,
    Event,
    HandFrame,
    KeyStroke,
    LevelReading,
    LevelStep,
    MoveCursor,
    ReleaseAll,
    Scroll,
    SetupResult,
    SetupView,
    State,
    StateChanged,
    SystemAction,
    Warning,
)
from gescrtl.platform import displays, win_autostart
from gescrtl.platform.displays import DisplayWatcher
from gescrtl.platform.hud import Hud
from gescrtl.platform.interfaces import InputBackend, LevelBackend
from gescrtl.platform.levels import WinLevels
from gescrtl.platform.presenter_keys import make_keys_for
from gescrtl.platform.preview import PreviewWindow
from gescrtl.platform.settings_window import SettingsWindow
from gescrtl.platform.tray import Tray
from gescrtl.platform.win_exit import install_exit_handlers
from gescrtl.platform.win_hotkeys import WinHotkeys
from gescrtl.platform.win_input import WinInput, enable_dpi_awareness
from gescrtl.recording.jsonl import RecordingWriter
from gescrtl.settings import custom_store, store
from gescrtl.stats import FrameTiming, StageStats
from gescrtl.tracking.camera import Camera, CameraError
from gescrtl.tracking.mediapipe_adapter import MediaPipeTracker

log = logging.getLogger("gescrtl")

_PAUSED_EVERY_NTH = 3  # Paused processes every 3rd frame: ~10 FPS at a 30 FPS camera
_MAX_CONSECUTIVE_FAILURES = 5
_CAMERA_STALL_NS = 1_000_000_000  # no frame for 1 s: the camera is lost
_CAMERA_RETRY_NS = 2_000_000_000  # try to open it again every 2 s


class Tracker(Protocol):
    def detect(self, frame_bgr: Any, t_ns: int) -> HandFrame: ...

    def close(self) -> None: ...


class UiBridge(QObject):
    """Carries events from the worker thread to the Qt main thread."""

    event = Signal(object)
    preview = Signal(object, object, object, float)  # QImage, HandFrame, DebugInfo, fps


class Worker(threading.Thread):
    def __init__(
        self,
        engine: Engine,
        input_backend: InputBackend,
        camera: Camera,
        ui: Callable[[Event], None],
        stats: StageStats,
        tracker_factory: Callable[[], Tracker] = MediaPipeTracker,
        clock: Callable[[], int] = time.perf_counter_ns,
    ) -> None:
        super().__init__(name="worker", daemon=True)
        self._tracker_factory = tracker_factory
        self._clock = clock
        self.engine = engine
        self.input = input_backend
        self.camera = camera
        self.ui = ui
        self.stats = stats
        self.on_fatal: Callable[[], None] = lambda: None
        self.levels: LevelBackend | None = None  # volume / brightness, set by main
        # opt-in camera preview: while set, Paused tracks every frame so the view is live
        self.preview_enabled = threading.Event()
        self.on_preview: Callable[[Any, HandFrame], None] | None = None
        self._q: queue.Queue[tuple[Command, str] | Callable[[], None] | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._tracker: Tracker | None = None
        self.recorder: RecordingWriter | None = None  # landmarks and commands only, never images
        self._last_t = 0
        self._camera_failed = False
        self._next_camera_try_ns = 0
        self._reopen: threading.Thread | None = None
        self._reopen_ok: bool | None = None

    # -- thread-safe API -----------------------------------------------------------------

    def post(self, cmd: Command, arg: str = "") -> None:
        self._q.put((cmd, arg))

    def apply_config(self, cfg: CoreConfig) -> None:
        """Reload settings on the worker thread: ReleaseAll first, state and mode are kept."""
        self._q.put(lambda: self._emit_all(self.engine.apply_config(cfg)))

    def set_custom_gestures(self, gestures: tuple[CustomGesture, ...]) -> None:
        """Give the engine the user's custom gestures (on the worker thread)."""
        self._q.put(lambda: self.engine.set_custom_gestures(tuple(gestures)))

    def stop(self) -> None:
        self._stop_event.set()
        self._q.put(None)

    # -- loop --------------------------------------------------------------------------------

    def _now(self) -> int:
        self._last_t = max(self._last_t, self._clock())
        return self._last_t

    def run(self) -> None:
        try:
            try:
                self._tracker = self._tracker_factory()
            except Exception as exc:
                log.error("tracker unavailable: %s", exc)
                self.ui(Warning(f"Hand tracking unavailable: {exc}"))
            self._emit_all(self.engine.start())
            self._sync_camera()
            self._loop()
        finally:
            self.input.release_all()
            self.camera.stop()
            if self._tracker is not None:
                self._tracker.close()
            if self.recorder is not None:
                self.recorder.close()

    def _loop(self) -> None:
        seq = 0
        paused_counter = 0
        failures = 0
        while not self._stop_event.is_set():
            try:
                self._drain_commands()
                self._emit_all(self.engine.tick(self._now()))
                self._check_camera(self._now())
                item = self.camera.latest(seq) if self.camera.running else None
                if item is not None and self._tracker is not None:
                    seq, frame, t_capture = item
                    if self.engine.state is State.PAUSED and not self.preview_enabled.is_set():
                        paused_counter += 1
                        if paused_counter % _PAUSED_EVERY_NTH:
                            continue
                    self._process(frame, t_capture)
                failures = 0
            except Exception:
                failures += 1
                log.exception("worker iteration failed")
                self._fail_safe()
                if failures >= _MAX_CONSECUTIVE_FAILURES:
                    log.error("too many consecutive failures; shutting down")
                    self.on_fatal()
                    return
                time.sleep(0.05)

    def _drain_commands(self) -> None:
        try:
            item = self._q.get(timeout=0.002)
        except queue.Empty:
            return
        while True:
            if item is None:
                return
            if callable(item):
                item()
            else:
                self._run_command(*item)
            self._sync_camera()
            try:
                item = self._q.get_nowait()
            except queue.Empty:
                return

    def _run_command(self, cmd: Command, arg: str = "") -> None:
        t = self._now()
        if self.recorder is not None:
            self.recorder.command(t, cmd, arg)
        self._emit_all(self.engine.command(cmd, t, arg))

    def _process(self, frame: Any, t_capture: int) -> None:
        tracker = self._tracker
        assert tracker is not None
        t0 = time.perf_counter_ns()
        hand_frame = tracker.detect(frame, t_capture)
        t1 = time.perf_counter_ns()
        t_engine = max(t_capture, self._last_t)
        self._last_t = t_engine
        if self.recorder is not None:
            self.recorder.frame(dataclasses.replace(hand_frame, t_ns=t_engine))
        events = self.engine.step(hand_frame, t_engine)
        t2 = time.perf_counter_ns()
        self._emit_all(events)
        t3 = time.perf_counter_ns()
        if self.on_preview is not None and self.preview_enabled.is_set():
            self.on_preview(frame, hand_frame)
        self.stats.record(
            FrameTiming(
                t_capture_ns=t_capture,
                wait_ns=max(0, t0 - t_capture),
                track_ns=t1 - t0,
                engine_ns=t2 - t1,
                input_ns=t3 - t2,
            )
        )

    # -- helpers ---------------------------------------------------------------------------

    def _emit_all(self, events: list[Event]) -> None:
        for e in events:
            if isinstance(e, MoveCursor):
                self.input.move(e.nx, e.ny)
            elif isinstance(e, ButtonDown):
                self.input.button_down(e.button)
            elif isinstance(e, ButtonUp):
                self.input.button_up(e.button)
            elif isinstance(e, Click):
                self.input.click(e.button)
            elif isinstance(e, Scroll):
                self.input.scroll(e.delta)
            elif isinstance(e, ReleaseAll):
                self.input.release_all()
            elif isinstance(e, KeyStroke):
                self._key_stroke(e)
            elif isinstance(e, SystemAction):
                self._system_action(e)
            elif isinstance(e, LevelStep):
                self._level_step(e)
            self.ui(e)

    def _key_stroke(self, e: KeyStroke) -> None:
        """Typed keys never raise into the worker loop either."""
        try:
            self.input.key_stroke(e.key, e.mods)
        except Exception:
            log.exception("key stroke %r failed", e.key)

    def _level_step(self, e: LevelStep) -> None:
        """Volume / brightness never raise into the worker loop either."""
        if self.levels is None:
            return
        try:
            self.levels.step(e.level, e.delta)
        except Exception:
            log.exception("level step %s %+d failed", e.level.name, e.delta)

    def _system_action(self, e: SystemAction) -> None:
        """Keys never raise into the worker loop: a failure is logged, the rest still runs."""
        try:
            supported = self.input.system_action(e.action)
        except Exception:
            log.exception("system action %s failed", e.action.name)
            return
        if not supported:
            self.ui(Warning("Start/end not supported in this app"))

    def _sync_camera(self) -> None:
        """Camera runs unless Inactive; releasing it is one action away (constitution VI)."""
        if self.engine.state is State.INACTIVE:
            self._camera_failed = False
            if self.camera.running:
                self.camera.stop()
            return
        if self.camera.running or self._camera_failed or self._tracker is None:
            return
        try:
            self.camera.start()
        except CameraError as exc:
            self._camera_failed = True
            log.warning("camera unavailable: %s", exc.cause)
            self._next_camera_try_ns = self._now() + _CAMERA_RETRY_NS
            self.post(Command.CAMERA_LOST, exc.cause)

    def _check_camera(self, now: int) -> None:
        """Camera recovery (H2): detect a stall, then retry the open off the worker thread.

        Opening can block for seconds, and commands (emergency stop) must stay responsive.
        """
        if self.engine.state is State.INACTIVE or self._tracker is None:
            self._camera_failed = False
            return
        if not self._camera_failed:
            if self.camera.running and now - self.camera.last_frame_ns > _CAMERA_STALL_NS:
                self.camera.stop()
                self._camera_failed = True
                self._next_camera_try_ns = now + _CAMERA_RETRY_NS
                log.warning("camera stopped sending frames")
                self.post(Command.CAMERA_LOST, "stopped sending frames")
            return
        if self._reopen is not None:
            if self._reopen.is_alive():
                return
            self._reopen = None
            if self._reopen_ok:
                self._camera_failed = False
                self.post(Command.CAMERA_BACK)
            return
        if now >= self._next_camera_try_ns:
            self._next_camera_try_ns = (
                now + _CAMERA_RETRY_NS
            )  # a try every 2 s, however long it takes
            self._reopen_ok = None
            self._reopen = threading.Thread(target=self._try_reopen, name="camera-retry")
            self._reopen.daemon = True
            self._reopen.start()

    def _try_reopen(self) -> None:
        try:
            self.camera.start()
            self._reopen_ok = True
        except CameraError as exc:
            log.info("camera still unavailable: %s", exc.cause)
            self._reopen_ok = False

    def _fail_safe(self) -> None:
        self.input.release_all()
        try:
            self._run_command(Command.PAUSE)
            self.ui(Warning("Internal error: GesCRTL paused. See the console for details."))
        except Exception:
            log.exception("fail-safe pause failed")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gescrtl", description="Webcam hand-gesture control.")
    parser.add_argument("--preview", action="store_true", help="open the camera preview at start")
    parser.add_argument("--region", type=float, help="active region size, 0.2-1.0 (default 0.6)")
    parser.add_argument("--min-cutoff", type=float, help="One Euro min cutoff (default 1.0)")
    parser.add_argument(
        "--scroll-rate", type=float, help="max scroll speed, units/s (default 1800)"
    )
    parser.add_argument(
        "--scroll-deadzone", type=float, help="thumb tilt ignored, degrees (default 8)"
    )
    parser.add_argument(
        "--record",
        metavar="NAME",
        help="record landmarks and commands (no images) to recordings/<time>_NAME.jsonl",
    )
    parser.add_argument(
        "--beta", type=float, help="One Euro beta; higher = less lag (default 0.007)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    log.info("DPI awareness: %s", enable_dpi_awareness())  # before any window exists

    input_backend = WinInput(keys_for=make_keys_for())
    install_exit_handlers(input_backend.release_all)

    qt = QApplication(sys.argv[:1])
    qt.setQuitOnLastWindowClosed(False)

    overrides = {
        "active_region": args.region,
        "one_euro_min_cutoff": args.min_cutoff,
        "one_euro_beta": args.beta,
        "scroll_max_rate": args.scroll_rate,
        "scroll_deadzone_deg": args.scroll_deadzone,
    }

    def build_config(settings: store.Settings) -> CoreConfig:
        """Settings file first, then command-line flags on top (flags win)."""
        base = settings.to_core_config(double_click_ms=input_backend.double_click_ms())
        return dataclasses.replace(base, **{k: v for k, v in overrides.items() if v is not None})

    settings, settings_warnings = store.load()
    current = [settings]  # the settings in force, shared by the callbacks below
    cfg = build_config(settings)
    displays.set_overlay_monitor(settings.overlay_monitor)
    gestures, gesture_warnings = custom_store.load()
    gesture_state = [gestures]
    engine = Engine(cfg)
    camera = Camera()
    stats = StageStats()
    hud = Hud(cfg.hint_display_ms)
    bridge = UiBridge()
    worker = Worker(engine, input_backend, camera, bridge.event.emit, stats)
    levels = WinLevels(on_level=lambda level, value: bridge.event.emit(LevelReading(level, value)))
    worker.levels = levels
    worker.set_custom_gestures(gestures)
    preview = PreviewWindow(cfg.active_region)
    if args.record:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.record)
        path = Path("recordings") / f"{stamp}_{safe}.jsonl"
        worker.recorder = RecordingWriter(
            path, scenario=args.record, width=camera.width, height=camera.height, fps=camera.fps
        )
        hud.set_recording(True)
        log.info("recording landmarks (no images) to %s", path)

    # -- camera preview: frames are shown on screen only, never saved ------------------------
    in_flight = threading.Event()  # at most one preview frame waits for the Qt thread
    fps_cache = [0.0, 0]

    def offer_preview(frame_bgr: Any, hand_frame: HandFrame) -> None:  # worker thread
        if in_flight.is_set():
            return
        fps_cache[1] += 1
        if fps_cache[1] % 15 == 1:
            fps_cache[0] = float(stats.summary().get("fps", 0.0))
        rgb = cv2.cvtColor(cv2.flip(frame_bgr, 1), cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        in_flight.set()
        bridge.preview.emit(image, hand_frame, engine.debug, fps_cache[0])

    def show_preview_frame(image: Any, hand_frame: Any, debug: Any, fps: float) -> None:
        preview.set_frame(image, hand_frame, debug, fps)
        in_flight.clear()

    def set_preview(on: bool) -> None:
        if on:
            worker.preview_enabled.set()
            preview.show()
            preview.raise_()
        else:
            worker.preview_enabled.clear()
            preview.hide()
        tray.set_preview_checked(on)

    worker.on_preview = offer_preview
    bridge.preview.connect(show_preview_frame)
    preview.closed.connect(lambda: set_preview(False))

    def quit_app() -> None:
        worker.preview_enabled.clear()
        preview.hide()
        worker.stop()
        worker.join(3.0)
        watcher.stop()
        levels.stop()
        hotkeys.stop()
        tray.close()
        hud.close()
        input_backend.release_all()
        qt.quit()

    settings_window: list[SettingsWindow | None] = [None]

    def apply_settings(loaded: tuple[store.Settings, list[str]], what: str) -> None:
        new_settings, warnings = loaded
        current[0] = new_settings
        new_cfg = build_config(new_settings)
        worker.apply_config(new_cfg)
        preview.set_region(new_cfg.active_region)
        displays.set_overlay_monitor(new_settings.overlay_monitor)
        hud.pill._relayout()
        if win_autostart.is_enabled() != new_settings.start_with_windows:
            if not win_autostart.set_enabled(new_settings.start_with_windows):
                warnings = [*warnings, "start with Windows could not be changed"]
        tray.set_custom_off_checked(not new_settings.custom_gestures_enabled)
        if settings_window[0] is not None:
            settings_window[0].refresh()
        note = f"{what}." if not warnings else f"{what}, but: " + "; ".join(warnings[:3])
        more = f" (+{len(warnings) - 3} more)" if len(warnings) > 3 else ""
        tray.notify(note + more, warning=bool(warnings))
        for w in warnings:
            log.warning("settings: %s", w)

    def reload_settings() -> None:
        apply_settings(store.load(), "Settings reloaded")

    def save_gestures(new: tuple[CustomGesture, ...]) -> None:
        gesture_state[0] = new
        try:
            custom_store.write(new)
        except OSError as exc:
            tray.notify(f"Could not save custom gestures: {exc}")
        worker.set_custom_gestures(new)
        if settings_window[0] is not None:
            settings_window[0].refresh_gestures()

    def reset_settings() -> None:
        save_gestures(custom_store.disable_all(gesture_state[0]))  # kept, but turned off
        apply_settings(store.reset(), "Settings reset to defaults")

    def apply_from_window(new_settings: store.Settings) -> None:
        try:
            store.write(new_settings)
        except OSError as exc:
            tray.notify(f"Could not save settings: {exc}")
        apply_settings((new_settings, []), "Settings applied")

    def begin_setup(arg: str) -> None:
        """Calibration and enrollment need the app running: turn on and resume first."""
        for cmd in (Command.TURN_ON, Command.RESUME):
            worker.post(cmd)
        worker.post(Command.START_SETUP, arg)

    def start_calibration() -> None:
        begin_setup("calibration")

    def start_enroll(kind: str, name: str) -> None:
        begin_setup(f"enroll:{kind}:{name}")

    def edit_gesture(name: str, changes: dict[str, Any]) -> None:
        save_gestures(
            tuple(
                dataclasses.replace(g, **changes) if g.name == name else g for g in gesture_state[0]
            )
        )

    def delete_gesture(name: str) -> None:
        save_gestures(custom_store.remove(gesture_state[0], name))

    def open_settings() -> None:
        if settings_window[0] is None:
            settings_window[0] = SettingsWindow(
                lambda: current[0],
                apply_from_window,
                reset_settings,
                start_calibration,
                lambda: gesture_state[0],
                start_enroll,
                edit_gesture,
                delete_gesture,
            )
        win = settings_window[0]
        win.refresh()
        win.show()
        win.raise_()
        win.activateWindow()

    def custom_off(off: bool) -> None:
        changed = current[0].model_copy(update={"custom_gestures_enabled": not off})
        apply_from_window(changed)

    last_setup_text = [""]

    def finish_calibration(values: dict[str, Any] | None) -> None:
        if values is None:
            tray.notify(last_setup_text[0] or "Calibration cancelled. Nothing changed.", False)
            return
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Calibration finished",
            f"Movement range {float(values['active_region']) * 100:.0f}% of the camera view, "
            f"pinch thresholds {values['pinch_enter']} and {values['pinch_release']}.\n\n"
            "Keep these settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        box.button(QMessageBox.StandardButton.Yes).setText("Keep")
        box.button(QMessageBox.StandardButton.No).setText("Discard")
        if box.exec() != QMessageBox.StandardButton.Yes:
            tray.notify("Calibration discarded. Nothing changed.", False)
            return
        merged = {**current[0].model_dump(), **values, "calibrated_at": date.today().isoformat()}
        new_settings, warnings = store.parse(merged)
        apply_from_window(new_settings)
        if warnings:
            tray.notify("Calibration kept, but: " + "; ".join(warnings[:2]))

    def finish_enrollment(values: dict[str, Any] | None) -> None:
        if values is None:
            tray.notify(last_setup_text[0] or "Recording cancelled.", False)
            return
        name = str(values["name"])
        existing = next((g for g in gesture_state[0] if g.name == name), None)
        action = existing.action if existing is not None else "PLAY_PAUSE"
        if existing is None:
            labels = [mapping.label(a) for a in mapping.ALLOWED]
            picked, ok = QInputDialog.getItem(
                settings_window[0], "Choose an action", f"What should “{name}” do?", labels, 0
            )
            if not ok:
                tray.notify("Recording discarded.", False)
                return
            action = mapping.ALLOWED[labels.index(picked)]
        gesture = CustomGesture(
            name=name,
            kind=str(values["kind"]),
            action=action,
            modes=existing.modes if existing is not None else (),
            enabled=True,
            samples=tuple(tuple(float(v) for v in t) for t in values["samples"]),  # type: ignore[attr-defined]
            threshold=float(values["threshold"]),  # type: ignore[arg-type]
            created=date.today().isoformat(),
        )
        save_gestures(custom_store.upsert(gesture_state[0], gesture))
        hint = (
            ""
            if current[0].custom_gestures_enabled
            else " Turn on custom gestures under General in Settings to use it."
        )
        tray.notify(f"Saved “{name}”.{hint}", False)

    tray = Tray(
        worker.post,
        reload_settings,
        reset_settings,
        quit_app,
        set_preview,
        lambda mode: worker.post(Command.SET_MODE, mode.name),
        open_settings,
        start_calibration,
        custom_off,
    )
    tray.set_custom_off_checked(not settings.custom_gestures_enabled)
    for w in gesture_warnings:
        log.warning("custom gestures: %s", w)
    if gesture_warnings:
        tray.notify("Custom gestures: " + "; ".join(gesture_warnings[:2]))
    if settings_warnings:
        for w in settings_warnings:
            log.warning("settings: %s", w)
        tray.notify("Settings problem, defaults used: " + "; ".join(settings_warnings[:3]))

    def route(event: Event) -> None:
        hud.handle(event)
        tray.handle(event)
        if isinstance(event, SetupView):
            last_setup_text[0] = event.text
            if settings_window[0] is not None:
                settings_window[0].set_setup_status(event.text)
        elif isinstance(event, SetupResult):
            if settings_window[0] is not None:
                settings_window[0].set_setup_status("")
            if event.kind == "calibration":
                finish_calibration(event.values)
            else:
                finish_enrollment(event.values)
        if isinstance(event, StateChanged):
            preview.set_status(event.hud_text or "Off")
            preview.set_camera_off(event.state is State.INACTIVE)

    bridge.event.connect(route)
    worker.on_fatal = lambda: bridge.event.emit(Warning("GesCRTL stopped after repeated errors."))

    def emergency() -> None:
        input_backend.release_all()  # directly, on the hotkey thread: no worker dependency
        worker.post(Command.EMERGENCY_STOP)

    hotkeys = WinHotkeys()
    if not hotkeys.start(
        emergency,
        lambda: worker.post(Command.TOGGLE_PAUSE),
        lambda: worker.post(Command.TOGGLE_POWER),
    ):
        worker.post(Command.HOTKEY_UNAVAILABLE)
    if hotkeys.unavailable:
        log.warning("hotkeys unavailable: %s", ", ".join(hotkeys.unavailable))

    def layout_changed(arg: str) -> None:
        input_backend.desktop_mode = True  # cursor positions are now over the whole desktop
        worker.post(Command.DISPLAYS, arg)

    watcher = DisplayWatcher(layout_changed)
    watcher.poll()
    if args.preview:
        set_preview(True)
    worker.start()
    try:
        return qt.exec()
    finally:
        worker.stop()
        worker.join(2.0)  # lets the worker close the recording
        input_backend.release_all()
