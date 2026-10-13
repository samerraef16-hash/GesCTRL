"""The settings window (spec 004 D5, D6, D9): change the main values, remap gestures, manage
custom gestures, start calibration, and reset to defaults without editing any file.

The controls are generated from ``store.Settings`` (label from the field title, range from its
``ge``/``le``), so a new setting appears here by being added to the model. Apply validates the
whole form with ``store.parse``; if anything is wrong the field is named and nothing is saved.
Must run on the Qt main thread.
"""

from __future__ import annotations

import typing
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gescrtl.core import mapping
from gescrtl.core.custom import CUSTOM_KINDS_AVAILABLE, CustomGesture
from gescrtl.core.types import Mode
from gescrtl.platform import displays
from gescrtl.settings import store

TABS: dict[str, tuple[str, ...]] = {
    "Pointer": (
        "active_region",
        "active_center_x",
        "active_center_y",
        "one_euro_min_cutoff",
        "one_euro_beta",
        "scroll_max_rate",
        "scroll_deadzone_deg",
        "scroll_full_deg",
        "scroll_step",
        "double_click_dist",
    ),
    "Timing": (
        "min_confidence",
        "stable_frames",
        "loss_frames",
        "pinch_enter",
        "pinch_release",
        "drag_hold_ms",
        "right_click_cooldown_ms",
        "right_click_max_hold_ms",
        "menu_hold_ms",
        "panel_hold_ms",
        "resume_hold_ms",
        "pause_hold_ms",
        "clutch_fist_ms",
    ),
    "Keyboard and access": (
        "confirm_method",
        "dwell_ms",
        "dwell_still_dist",
        "pointer_dwell_click",
        "two_hand_press",
        "second_hand_max_dist",
        "keyboard_position",
        "key_repeat_delay_ms",
        "key_repeat_ms",
        "key_cooldown_ms",
    ),
    "General": ("start_with_windows", "custom_gestures_enabled"),
}
_SHOWN_ELSEWHERE = {"mappings", "overlay_monitor", "calibrated_at"}


def _bounds(name: str) -> tuple[float | None, float | None]:
    lo = hi = None
    for meta in store.Settings.model_fields[name].metadata:
        lo = getattr(meta, "ge", lo)
        hi = getattr(meta, "le", hi)
    return lo, hi


def _decimals(lo: float | None, hi: float | None) -> int:
    span = (hi or 1.0) - (lo or 0.0)
    return 4 if span <= 1.0 else 3 if span <= 10.0 else 1


class SettingsWindow(QWidget):
    """A normal, non-modal window. Callbacks keep it free of any engine or file knowledge."""

    def __init__(
        self,
        current: Callable[[], store.Settings],
        on_apply: Callable[[store.Settings], None],
        on_reset: Callable[[], None],
        on_calibrate: Callable[[], None],
        gestures: Callable[[], tuple[CustomGesture, ...]] = lambda: (),
        on_enroll: Callable[[str, str], None] = lambda kind, name: None,
        on_gesture_edit: Callable[[str, dict[str, Any]], None] = lambda name, changes: None,
        on_gesture_delete: Callable[[str], None] = lambda name: None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("GesCRTL Settings")
        self.resize(560, 640)
        self._current, self._on_apply = current, on_apply
        self._on_reset, self._on_calibrate = on_reset, on_calibrate
        self._gestures = gestures
        self._on_enroll, self._on_gesture_edit = on_enroll, on_gesture_edit
        self._on_gesture_delete = on_gesture_delete
        self.fields: dict[str, QWidget] = {}
        self.slot_boxes: dict[str, QComboBox] = {}
        self._tabs = QTabWidget()
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._setup_status = QLabel("")
        self._setup_status.setWordWrap(True)

        listed = {n for names in TABS.values() for n in names}
        rest = tuple(
            n for n in store.Settings.model_fields if n not in listed and n not in _SHOWN_ELSEWHERE
        )
        for title, names in TABS.items():
            self._tabs.addTab(self._form_page(names), title)
        self._tabs.addTab(self._displays_page(), "Displays")
        self._tabs.addTab(self._gestures_page(), "Gestures")
        self._tabs.addTab(self._custom_page(), "Custom gestures")
        if rest:
            self._tabs.addTab(self._form_page(rest), "Advanced")

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.reset_button = QPushButton("Reset to defaults…")
        self.reset_button.clicked.connect(self._ask_reset)
        self.confirm_reset_button = QPushButton("Yes, reset everything")
        self.confirm_reset_button.clicked.connect(self._do_reset)
        self.cancel_reset_button = QPushButton("Keep my settings")
        self.cancel_reset_button.clicked.connect(self._cancel_reset)
        self.calibrate_button = QPushButton("Calibrate…")
        self.calibrate_button.clicked.connect(lambda: self._on_calibrate())
        self._calibrated = QLabel("")
        self.confirm_reset_button.hide()
        self.cancel_reset_button.hide()

        buttons = QHBoxLayout()
        for b in (self.apply_button, self.calibrate_button, self.reset_button):
            buttons.addWidget(b)
        buttons.addWidget(self.confirm_reset_button)
        buttons.addWidget(self.cancel_reset_button)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._calibrated)
        layout.addWidget(self._setup_status)
        layout.addWidget(self._status)
        layout.addLayout(buttons)
        self.refresh()

    # -- building the pages --------------------------------------------------------------------

    def _form_page(self, names: tuple[str, ...]) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        for name in names:
            widget = self._make_field(name)
            self.fields[name] = widget
            form.addRow(store.Settings.model_fields[name].title or name, widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    @staticmethod
    def _make_field(name: str) -> QWidget:
        field = store.Settings.model_fields[name]
        ann = field.annotation
        if ann is bool:
            return QCheckBox()
        if typing.get_origin(ann) is typing.Literal:
            box = QComboBox()
            box.addItems([str(v) for v in typing.get_args(ann)])
            return box
        lo, hi = _bounds(name)
        if ann is int:
            spin = QSpinBox()
            spin.setRange(int(lo if lo is not None else 0), int(hi if hi is not None else 10**6))
            spin.setToolTip(f"{lo} to {hi}")
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
            return spin
        dspin = QDoubleSpinBox()
        dspin.setDecimals(_decimals(lo, hi))
        dspin.setRange(lo if lo is not None else 0.0, hi if hi is not None else 10**6)
        dspin.setSingleStep(10 ** -(_decimals(lo, hi) - 1))
        dspin.setToolTip(f"{lo} to {hi}")
        return dspin

    def _displays_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.overlay_box = QComboBox()
        form.addRow("Show overlays on", self.overlay_box)
        self.monitor_list = QLabel("")
        self.monitor_list.setWordWrap(True)
        form.addRow("Detected monitors", self.monitor_list)
        return page

    def _gestures_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        note = QLabel(
            "Choose what each gesture does. Clicks, pause, resume, the emergency stop, the mode "
            "menu and the level panel can never be changed."
        )
        note.setWordWrap(True)
        form.addRow(note)
        for slot in mapping.SLOTS:
            box = QComboBox()
            for action in mapping.ALLOWED:
                box.addItem(mapping.label(action), action)
            self.slot_boxes[slot] = box
            form.addRow(self._slot_title(slot), box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    @staticmethod
    def _slot_title(slot: str) -> str:
        kind, _, rest = slot.partition(".")
        if kind == "media":
            ident = mapping.MEDIA_TARGET_IDS[int(rest[1:])]
            return f"Media grid: {ident.replace('_', ' ')}"
        return f"Presentation: {rest.replace('_', ' ')}"

    def _custom_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        note = QLabel(
            "Record a hand shape or a movement and give it an action. Turn the feature on under "
            "General. Custom gestures are off until you do."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.gesture_list = QListWidget()
        self.gesture_list.currentRowChanged.connect(self._sync_gesture_controls)
        layout.addWidget(self.gesture_list)
        row = QHBoxLayout()
        self.record_shape = QPushButton("Record a hand shape…")
        self.record_move = QPushButton("Record a movement…")
        self.record_shape.clicked.connect(lambda: self._record("shape"))
        self.record_move.clicked.connect(lambda: self._record("move"))
        self.record_shape.setVisible("shape" in CUSTOM_KINDS_AVAILABLE)
        self.record_move.setVisible("move" in CUSTOM_KINDS_AVAILABLE)
        row.addWidget(self.record_shape)
        row.addWidget(self.record_move)
        layout.addLayout(row)
        form = QFormLayout()
        self.gesture_action = QComboBox()
        for action in mapping.ALLOWED:
            self.gesture_action.addItem(mapping.label(action), action)
        self.gesture_modes = QComboBox()
        self.gesture_modes.addItem("Every mode", "")
        for mode in Mode:
            self.gesture_modes.addItem(mode.name.title(), mode.name)
        self.gesture_enabled = QCheckBox("Enabled")
        self.gesture_delete = QPushButton("Delete")
        self.gesture_retrain = QPushButton("Record again…")
        form.addRow("Action", self.gesture_action)
        form.addRow("Works in", self.gesture_modes)
        form.addRow(self.gesture_enabled)
        layout.addLayout(form)
        row2 = QHBoxLayout()
        row2.addWidget(self.gesture_retrain)
        row2.addWidget(self.gesture_delete)
        layout.addLayout(row2)
        self.gesture_action.activated.connect(lambda _i: self._edit_gesture())
        self.gesture_modes.activated.connect(lambda _i: self._edit_gesture())
        self.gesture_enabled.clicked.connect(lambda _c: self._edit_gesture())
        self.gesture_delete.clicked.connect(self._delete_gesture)
        self.gesture_retrain.clicked.connect(self._retrain_gesture)
        return page

    # -- values <-> widgets --------------------------------------------------------------------

    def refresh(self) -> None:
        """Show the current settings (after Apply, Reload, Reset, or a kept calibration)."""
        s = self._current()
        for name, widget in self.fields.items():
            value = getattr(s, name)
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
        for slot, box in self.slot_boxes.items():
            box.setCurrentIndex(box.findData(mapping.resolve(tuple(s.mappings.items()), slot)))
        monitors = displays.monitor_names()
        self.overlay_box.clear()
        self.overlay_box.addItem("Primary monitor", "")
        for name in monitors:
            self.overlay_box.addItem(name, name)
        idx = self.overlay_box.findData(s.overlay_monitor)
        self.overlay_box.setCurrentIndex(max(idx, 0))
        self.monitor_list.setText("\n".join(monitors) or "(not detected yet)")
        self._calibrated.setText(
            f"Calibrated on {s.calibrated_at}" if s.calibrated_at else "Not calibrated"
        )
        self.refresh_gestures()

    def _collect(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QCheckBox):
                values[name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentText()
            else:
                values[name] = widget.value()  # type: ignore[attr-defined]
        overrides = {}
        for slot, box in self.slot_boxes.items():
            action = box.currentData()
            if action != mapping.DEFAULTS[slot]:
                overrides[slot] = action
        values["mappings"] = overrides
        values["overlay_monitor"] = self.overlay_box.currentData() or ""
        values["calibrated_at"] = self._current().calibrated_at
        return values

    def apply(self) -> bool:
        """Validate the whole form; save and apply only if every value is acceptable."""
        settings, warnings = store.parse(self._collect())
        if warnings:
            self._status.setText("Not applied:\n" + "\n".join(warnings))
            self._status.setStyleSheet("color: #c0392b;")
            return False
        self._status.setText("Applied.")
        self._status.setStyleSheet("")
        self._on_apply(settings)
        return True

    # -- reset ---------------------------------------------------------------------------------

    def _ask_reset(self) -> None:
        self._status.setText(
            "Reset every setting, mapping and calibration to the defaults? Custom gestures are "
            "kept but turned off."
        )
        self._status.setStyleSheet("")
        self.confirm_reset_button.show()
        self.cancel_reset_button.show()

    def _cancel_reset(self) -> None:
        self.confirm_reset_button.hide()
        self.cancel_reset_button.hide()
        self._status.setText("")

    def _do_reset(self) -> None:
        self._cancel_reset()
        self._on_reset()
        self._status.setText("Everything was reset to the defaults.")

    # -- custom gestures -----------------------------------------------------------------------

    def set_setup_status(self, text: str) -> None:
        """Progress text from calibration or enrollment."""
        self._setup_status.setText(text)

    def refresh_gestures(self) -> None:
        keep = self.gesture_list.currentRow()
        self.gesture_list.blockSignals(True)
        self.gesture_list.clear()
        for g in self._gestures():
            where = "every mode" if not g.modes else ", ".join(m.title() for m in g.modes)
            flag = "" if g.enabled else " (off)"
            item = QListWidgetItem(f"{g.name}: {g.kind}, {mapping.label(g.action)}, {where}{flag}")
            item.setData(Qt.ItemDataRole.UserRole, g.name)
            self.gesture_list.addItem(item)
        self.gesture_list.blockSignals(False)
        if self.gesture_list.count():
            self.gesture_list.setCurrentRow(min(max(keep, 0), self.gesture_list.count() - 1))
        self._sync_gesture_controls(self.gesture_list.currentRow())

    def _selected(self) -> CustomGesture | None:
        item = self.gesture_list.currentItem()
        if item is None:
            return None
        name = item.data(Qt.ItemDataRole.UserRole)
        return next((g for g in self._gestures() if g.name == name), None)

    def _sync_gesture_controls(self, _row: int) -> None:
        g = self._selected()
        for w in (
            self.gesture_action,
            self.gesture_modes,
            self.gesture_enabled,
            self.gesture_delete,
            self.gesture_retrain,
        ):
            w.setEnabled(g is not None)
        if g is None:
            return
        self.gesture_action.setCurrentIndex(self.gesture_action.findData(g.action))
        self.gesture_modes.setCurrentIndex(
            max(self.gesture_modes.findData(g.modes[0] if len(g.modes) == 1 else ""), 0)
        )
        self.gesture_enabled.setChecked(g.enabled)

    def _record(self, kind: str) -> None:
        name, ok = QInputDialog.getText(self, "New custom gesture", "Name for the gesture:")
        name = name.strip()
        if ok and name:
            self._on_enroll(kind, name)

    def _retrain_gesture(self) -> None:
        g = self._selected()
        if g is not None:
            self._on_enroll(g.kind, g.name)

    def _edit_gesture(self) -> None:
        g = self._selected()
        if g is None:
            return
        mode = self.gesture_modes.currentData()
        self._on_gesture_edit(
            g.name,
            {
                "action": self.gesture_action.currentData(),
                "enabled": self.gesture_enabled.isChecked(),
                "modes": (mode,) if mode else (),
            },
        )

    def _delete_gesture(self) -> None:
        g = self._selected()
        if g is not None:
            self._on_gesture_delete(g.name)
