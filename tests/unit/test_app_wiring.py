"""The composition root runs end to end with fakes: camera, tracker, hotkeys, registry, levels.

This builds every window, wires the callbacks, and drives the tray the way a user would, so a
wrong name or argument in ``main`` fails here instead of on the user's desktop.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gescrtl import app  # noqa: E402
from gescrtl.core.types import HandFrame  # noqa: E402
from gescrtl.settings import custom_store, store  # noqa: E402


class FakeCamera:
    width, height, fps = 640, 480, 30
    running = False
    last_frame_ns = 0

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def latest(self, seq):
        return None


class FakeTracker:
    def detect(self, frame, t_ns):
        return HandFrame(t_ns)

    def close(self):
        pass


class FakeHotkeys:
    unavailable: list[str] = []

    def start(self, *a):
        return True

    def stop(self):
        pass


class FakeLevels:
    def __init__(self, on_level):
        pass

    def stop(self):
        pass


class FakeAutostart:
    def __init__(self):
        self.on = False
        self.calls = []

    def is_enabled(self):
        return self.on

    def set_enabled(self, on):
        self.calls.append(on)
        self.on = on
        return True


@pytest.fixture
def wired(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    qt = QApplication.instance() or QApplication([])
    created = {}
    autostart = FakeAutostart()

    class TestWorker(app.Worker):
        def __init__(self, engine, inp, camera, ui, stats):
            super().__init__(engine, inp, camera, ui, stats, tracker_factory=FakeTracker)
            created["worker"] = self

    class RecTray(app.Tray):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            created["tray"] = self

    class RecSettings(app.SettingsWindow):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            created["window"] = self

    monkeypatch.setattr(app, "Camera", FakeCamera)
    monkeypatch.setattr(app, "Worker", TestWorker)
    monkeypatch.setattr(app, "Tray", RecTray)
    monkeypatch.setattr(app, "SettingsWindow", RecSettings)
    monkeypatch.setattr(app, "WinHotkeys", FakeHotkeys)
    monkeypatch.setattr(app, "WinLevels", FakeLevels)
    monkeypatch.setattr(app, "install_exit_handlers", lambda *_: None)
    monkeypatch.setattr(app, "win_autostart", autostart)
    monkeypatch.setattr(app, "QApplication", lambda argv: qt)
    created["autostart"] = autostart
    created["tmp"] = tmp_path
    return created, monkeypatch


def run_main(wired, drive):
    created, monkeypatch = wired
    monkeypatch.setattr(QApplication, "exec", lambda self: drive(created) or 0)
    assert app.main([]) == 0
    return created


def action(tray, text):
    return next(a for a in tray._menu.actions() if a.text() == text)


def test_main_builds_everything_and_shuts_down_cleanly(wired):
    seen = {}

    def drive(c):
        seen["alive"] = c["worker"].is_alive()

    run_main(wired, drive)
    assert seen["alive"]
    assert not wired[0]["worker"].is_alive()
    assert (wired[0]["tmp"] / "GesCRTL" / "settings.json").exists()


def test_the_settings_window_applies_a_change_saves_it_and_reaches_the_engine(wired):
    def drive(c):
        action(c["tray"], "Settings…").trigger()
        win = c["window"]
        win.fields["dwell_ms"].setValue(1200)
        win.fields["pointer_dwell_click"].setChecked(True)
        win.fields["start_with_windows"].setChecked(True)
        assert win.apply() is True
        import time

        for _ in range(100):  # the worker applies it on its own thread
            if c["worker"].engine.cfg.dwell_ms == 1200:
                break
            time.sleep(0.02)
        c["engine_cfg"] = c["worker"].engine.cfg

    c = run_main(wired, drive)
    saved, warnings = store.load(c["tmp"] / "GesCRTL" / "settings.json")
    assert warnings == [] and saved.dwell_ms == 1200 and saved.pointer_dwell_click is True
    assert c["engine_cfg"].dwell_ms == 1200 and c["engine_cfg"].pointer_dwell_click is True
    assert c["autostart"].calls == [True]


def test_the_custom_gesture_switch_in_the_tray_is_saved(wired):
    def drive(c):
        off = action(c["tray"], "Turn off custom gestures")
        assert off.isChecked()  # custom gestures start off
        off.trigger()  # unchecking turns them on
        assert not off.isChecked()

    c = run_main(wired, drive)
    saved, _ = store.load(c["tmp"] / "GesCRTL" / "settings.json")
    assert saved.custom_gestures_enabled is True


def test_reset_keeps_custom_gestures_but_turns_them_off(wired):
    from gescrtl.core.custom import SHAPE_DIM, CustomGesture

    created, _ = wired
    gesture = CustomGesture("g", "shape", "MUTE", (), True, ((0.0,) * SHAPE_DIM,), 0.3, "")
    custom_store.save((gesture,), created["tmp"] / "GesCRTL" / "custom_gestures.json")
    store.save(store.Settings(dwell_ms=2000), created["tmp"] / "GesCRTL" / "settings.json")

    def drive(c):
        action(c["tray"], "Reset to defaults").trigger()

    c = run_main(wired, drive)
    saved, _ = store.load(c["tmp"] / "GesCRTL" / "settings.json")
    assert saved.dwell_ms == 800
    gestures, warnings = custom_store.load(c["tmp"] / "GesCRTL" / "custom_gestures.json")
    assert [g.name for g in gestures] == ["g"] and not gestures[0].enabled and warnings == []


def test_a_damaged_gesture_file_is_reported_and_the_app_still_starts(wired):
    created, _ = wired
    (created["tmp"] / "GesCRTL").mkdir()
    (created["tmp"] / "GesCRTL" / "custom_gestures.json").write_text("{", encoding="utf-8")
    run_main(wired, lambda c: None)
    text = (created["tmp"] / "GesCRTL" / "custom_gestures.json").read_text(encoding="utf-8")
    assert text == "{"  # never overwritten


def test_the_calibrate_entry_turns_the_app_on_resumes_and_starts_the_setup(wired):
    posted = []

    def drive(c):
        worker = c["worker"]
        original = worker.post
        worker.post = lambda cmd, arg="": (posted.append((cmd.name, arg)), original(cmd, arg))[1]
        action(c["tray"], "Calibrate…").trigger()
        win_open = action(c["tray"], "Settings…")
        win_open.trigger()
        c["window"].calibrate_button.click()
        c["window"]._on_enroll("shape", "peace")

    run_main(wired, drive)
    names = [p for p in posted if p[0] in ("TURN_ON", "RESUME", "START_SETUP")]
    assert names[:3] == [("TURN_ON", ""), ("RESUME", ""), ("START_SETUP", "calibration")]
    assert ("START_SETUP", "enroll:shape:peace") in posted


def test_the_monitor_layout_is_posted_to_the_engine_at_start(wired):
    seen = {}

    def drive(c):
        import time

        for _ in range(100):
            if c["worker"].engine.displays is not None:
                break
            time.sleep(0.02)
        seen["displays"] = c["worker"].engine.displays

    run_main(wired, drive)
    assert seen["displays"] is not None and seen["displays"].w > 0
