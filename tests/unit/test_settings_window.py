"""The settings window: generated controls, validation before saving, remapping, reset (D5)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
)

from gescrtl.core import mapping  # noqa: E402
from gescrtl.core.custom import SHAPE_DIM, CustomGesture  # noqa: E402
from gescrtl.platform.settings_window import SettingsWindow  # noqa: E402
from gescrtl.settings import store  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class Harness:
    def __init__(self, qapp, gestures=()):
        self.settings = store.Settings()
        self.applied: list[store.Settings] = []
        self.resets = 0
        self.calibrations = 0
        self.enrolled: list[tuple[str, str]] = []
        self.edits: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self.gestures = tuple(gestures)
        self.win = SettingsWindow(
            lambda: self.settings,
            self.applied.append,
            lambda: setattr(self, "resets", self.resets + 1),
            lambda: setattr(self, "calibrations", self.calibrations + 1),
            lambda: self.gestures,
            lambda kind, name: self.enrolled.append((kind, name)),
            lambda name, changes: self.edits.append((name, changes)),
            self.deleted.append,
        )


def gesture(name="peace", **kw):
    base = dict(
        name=name,
        kind="shape",
        action="PLAY_PAUSE",
        modes=(),
        enabled=True,
        samples=((0.0,) * SHAPE_DIM,) * 5,
        threshold=0.3,
        created="",
    )
    base.update(kw)
    return CustomGesture(**base)


def test_every_setting_that_can_be_changed_has_a_control(qapp):
    h = Harness(qapp)
    shown = set(h.win.fields) | {"mappings", "overlay_monitor", "calibrated_at"}
    assert set(store.Settings.model_fields) <= shown
    assert isinstance(h.win.fields["active_region"], QDoubleSpinBox)
    assert isinstance(h.win.fields["stable_frames"], QSpinBox)
    assert isinstance(h.win.fields["pointer_dwell_click"], QCheckBox)
    assert isinstance(h.win.fields["confirm_method"], QComboBox)


def test_controls_show_the_current_values_and_the_allowed_range(qapp):
    h = Harness(qapp)
    f = h.win.fields
    assert f["active_region"].value() == pytest.approx(0.6)
    assert (f["active_region"].minimum(), f["active_region"].maximum()) == (0.2, 1.0)
    assert f["dwell_ms"].value() == 800 and f["dwell_ms"].minimum() == 300
    assert f["confirm_method"].currentText() == "pinch"
    assert f["two_hand_press"].isChecked() and not f["start_with_windows"].isChecked()


def test_apply_saves_a_valid_change(qapp):
    h = Harness(qapp)
    h.win.fields["active_region"].setValue(0.45)
    h.win.fields["confirm_method"].setCurrentText("dwell")
    h.win.fields["pointer_dwell_click"].setChecked(True)
    assert h.win.apply() is True
    new = h.applied[-1]
    assert new.active_region == pytest.approx(0.45) and new.confirm_method == "dwell"
    assert new.pointer_dwell_click is True and new.stable_frames == 3  # the rest is unchanged


def test_an_invalid_combination_names_the_field_and_saves_nothing(qapp):
    h = Harness(qapp)
    h.win.fields["pinch_enter"].setValue(0.45)
    h.win.fields["pinch_release"].setValue(0.2)  # must stay above the enter value
    assert h.win.apply() is False
    assert not h.applied and "pinch_enter" in h.win._status.text()


def test_remapping_a_gesture_is_saved_as_an_override_only(qapp):
    h = Harness(qapp)
    box = h.win.slot_boxes["presentation.swipe_right"]
    box.setCurrentIndex(box.findData("MUTE"))
    assert h.win.apply() is True
    assert h.applied[-1].mappings == {"presentation.swipe_right": "MUTE"}


def test_safety_actions_are_not_offered_for_remapping(qapp):
    h = Harness(qapp)
    box = h.win.slot_boxes["media.t0"]
    offered = {box.itemData(i) for i in range(box.count())}
    assert offered == set(mapping.ALLOWED)
    for banned in ("PAUSE", "RESUME", "EMERGENCY_STOP", "CLICK", "MODE_MENU", "LEVEL_PANEL"):
        assert banned not in offered


def test_existing_mappings_are_shown(qapp):
    h = Harness(qapp)
    h.settings = store.Settings(mappings={"media.t3": "COPY"})
    h.win.refresh()
    box = h.win.slot_boxes["media.t3"]
    assert box.currentData() == "COPY"
    assert h.win.slot_boxes["media.t4"].currentData() == "VOLUME_UP"


def test_reset_asks_first_and_then_resets(qapp):
    h = Harness(qapp)
    h.win.reset_button.click()
    assert h.win.confirm_reset_button.isHidden() is False and h.resets == 0
    h.win.cancel_reset_button.click()
    assert h.resets == 0 and h.win.confirm_reset_button.isHidden()
    h.win.reset_button.click()
    h.win.confirm_reset_button.click()
    assert h.resets == 1


def test_calibrate_button_starts_calibration(qapp):
    h = Harness(qapp)
    h.win.calibrate_button.click()
    assert h.calibrations == 1


def test_the_calibration_date_is_shown(qapp):
    h = Harness(qapp)
    assert "Not calibrated" in h.win._calibrated.text()
    h.settings = store.Settings(calibrated_at="2026-10-13")
    h.win.refresh()
    assert "2026-10-13" in h.win._calibrated.text()


def test_custom_gestures_are_listed_and_edited(qapp):
    h = Harness(qapp, [gesture(), gesture("wave", kind="move", enabled=False)])
    h.win.refresh()
    assert h.win.gesture_list.count() == 2
    h.win.gesture_list.setCurrentRow(0)
    assert h.win.gesture_enabled.isChecked() and h.win.gesture_action.currentData() == "PLAY_PAUSE"
    h.win.gesture_action.setCurrentIndex(h.win.gesture_action.findData("MUTE"))
    h.win.gesture_action.activated.emit(h.win.gesture_action.currentIndex())
    name, changes = h.edits[-1]
    assert name == "peace" and changes["action"] == "MUTE" and changes["modes"] == ()
    h.win.gesture_list.setCurrentRow(1)
    assert not h.win.gesture_enabled.isChecked()
    h.win.gesture_delete.click()
    assert h.deleted == ["wave"]


def test_retraining_starts_an_enrollment_of_the_same_kind(qapp):
    h = Harness(qapp, [gesture("wave", kind="move")])
    h.win.refresh()
    h.win.gesture_list.setCurrentRow(0)
    h.win.gesture_retrain.click()
    assert h.enrolled == [("move", "wave")]


def test_recording_buttons_follow_the_kinds_that_are_available(qapp):
    from gescrtl.core.custom import CUSTOM_KINDS_AVAILABLE

    h = Harness(qapp)
    assert h.win.record_shape.isHidden() == ("shape" not in CUSTOM_KINDS_AVAILABLE)
    assert h.win.record_move.isHidden() == ("move" not in CUSTOM_KINDS_AVAILABLE)


def test_setup_progress_text_is_shown(qapp):
    h = Harness(qapp)
    h.win.set_setup_status("Take 2 of 5: hold the shape")
    assert "Take 2 of 5" in h.win._setup_status.text()
