"""User settings: a JSON file, validated field by field (plan D15, FR-024..FR-027).

Every field mirrors a ``CoreConfig`` field of the same name. A bad value falls back to its
default and produces a warning naming the field; the rest of the file still loads. There are no
fields for the emergency stop, pause or release-on-loss: those cannot be configured (FR-020).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from gescrtl.core.config import CoreConfig

Frac = Annotated[float, Field(ge=0.0, le=1.0)]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Mapping and smoothing
    active_region: float = Field(0.6, ge=0.2, le=1.0)
    one_euro_min_cutoff: float = Field(1.0, ge=0.05, le=10.0)
    one_euro_beta: float = Field(0.007, ge=0.0, le=50.0)
    one_euro_d_cutoff: float = Field(1.0, ge=0.1, le=10.0)

    # Confidence and stability
    min_confidence: float = Field(0.5, ge=0.1, le=0.95)
    stable_frames: int = Field(3, ge=1, le=10)
    loss_frames: int = Field(3, ge=1, le=10)

    # Pinch (ratio of fingertip distance to hand size); enter must stay below release
    pinch_enter: float = Field(0.25, ge=0.05, le=0.5)
    pinch_release: float = Field(0.35, ge=0.1, le=0.6)

    # Hold times and cooldowns (ms)
    resume_hold_ms: int = Field(1000, ge=100, le=5000)
    pause_hold_ms: int = Field(1500, ge=100, le=5000)
    drag_hold_ms: int = Field(300, ge=100, le=5000)
    right_click_cooldown_ms: int = Field(300, ge=100, le=5000)
    right_click_max_hold_ms: int = Field(1000, ge=100, le=5000)
    pause_resume_cooldown_ms: int = Field(1000, ge=100, le=5000)
    click_stabilize_ms: int = Field(100, ge=0, le=1000)
    pinch_lookback_frames: int = Field(2, ge=0, le=10)
    flat_hand_frames: int = Field(5, ge=1, le=15)
    pause_still_dist: float = Field(0.04, ge=0.005, le=0.3)

    # Scrolling by thumb tilt
    scroll_max_rate: float = Field(1800.0, ge=100.0, le=6000.0)
    scroll_deadzone_deg: float = Field(8.0, ge=1.0, le=30.0)
    scroll_full_deg: float = Field(45.0, ge=10.0, le=90.0)
    scroll_settle_ms: int = Field(250, ge=0, le=2000)
    scroll_step: int = Field(30, ge=1, le=240)

    # Bad-frame rejection (camera-normalized units per frame)
    max_hand_jump: float = Field(0.15, ge=0.02, le=1.0)
    max_anchor_jump: float = Field(0.12, ge=0.02, le=1.0)

    # Feedback timing (ms)
    stopped_display_ms: int = Field(600, ge=100, le=5000)
    hint_display_ms: int = Field(3000, ge=500, le=10000)
    click_flash_ms: int = Field(150, ge=50, le=1000)

    # Double click snapping distance (normalized screen distance)
    double_click_dist: float = Field(0.02, ge=0.0, le=0.2)

    # Mode menu and level panel
    menu_hold_ms: int = Field(800, ge=300, le=3000)
    menu_timeout_ms: int = Field(5000, ge=1000, le=30000)
    panel_hold_ms: int = Field(500, ge=200, le=3000)
    panel_timeout_ms: int = Field(5000, ge=1000, le=30000)

    # Presentation swipe (distances in hand sizes, speeds in hand sizes per second)
    swipe_window_ms: int = Field(350, ge=100, le=1000)
    swipe_min_frames: int = Field(3, ge=2, le=10)
    swipe_min_dist: float = Field(1.5, ge=0.3, le=5.0)
    swipe_max_dy_ratio: float = Field(0.5, ge=0.1, le=1.5)
    swipe_cooldown_ms: int = Field(600, ge=100, le=5000)
    swipe_return_block_ms: int = Field(1000, ge=0, le=5000)
    swipe_rearm_speed: float = Field(1.0, ge=0.1, le=5.0)
    swipe_rearm_ms: int = Field(100, ge=0, le=1000)

    # Presentation slide show start/end (thumb direction; enter must stay above exit)
    show_hold_ms: int = Field(1000, ge=300, le=5000)
    show_cooldown_ms: int = Field(2000, ge=500, le=10000)
    thumb_dir_enter_deg: float = Field(50.0, ge=20.0, le=80.0)
    thumb_dir_exit_deg: float = Field(35.0, ge=10.0, le=75.0)

    # Presentation laser pointer
    laser_min_cutoff: float = Field(0.3, ge=0.05, le=10.0)
    laser_beta: float = Field(0.002, ge=0.0, le=50.0)
    laser_grace_ms: int = Field(300, ge=0, le=2000)

    # Level control (volume / brightness)
    level_step: int = Field(2, ge=1, le=10)
    level_max_rate: float = Field(40.0, ge=5.0, le=200.0)
    level_drag_gain: float = Field(1.0, ge=0.2, le=5.0)
    level_repeat_ms: int = Field(150, ge=50, le=1000)

    # Pointing at on-screen targets
    action_cooldown_ms: int = Field(400, ge=100, le=5000)
    confirm_window_ms: int = Field(3000, ge=1000, le=10000)
    target_margin: float = Field(0.01, ge=0.0, le=0.05)

    def to_core_config(self, double_click_ms: int | None = None) -> CoreConfig:
        """The engine config. The double-click time comes from the OS, not from settings."""
        values: dict[str, Any] = self.model_dump()
        if double_click_ms is not None:
            values["double_click_ms"] = double_click_ms
        return CoreConfig(**values)


def default_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "GesCRTL" / "settings.json"


def _validators() -> dict[str, TypeAdapter[Any]]:
    return {
        name: TypeAdapter(Annotated[field.annotation, *field.metadata])
        for name, field in Settings.model_fields.items()
    }


_VALIDATORS = _validators()


def parse(data: Any) -> tuple[Settings, list[str]]:
    """Validate a decoded JSON object field by field. Returns (settings, warnings)."""
    if not isinstance(data, dict):
        return Settings(), ["settings file is not a JSON object: using defaults"]
    warnings: list[str] = []
    good: dict[str, Any] = {}
    for key, value in data.items():
        if key not in _VALIDATORS:
            warnings.append(f"{key}: unknown setting ignored")
            continue
        default = Settings.model_fields[key].default
        try:
            if isinstance(value, bool):
                raise ValueError("a number is required")
            good[key] = _VALIDATORS[key].validate_python(value)
        except (ValidationError, ValueError):
            warnings.append(f"{key}: invalid value {value!r}, using the default {default!r}")
    settings = Settings(**good)
    if settings.pinch_enter >= settings.pinch_release:
        warnings.append("pinch_enter must be below pinch_release: both reset to their defaults")
        defaults = Settings()
        settings = settings.model_copy(
            update={"pinch_enter": defaults.pinch_enter, "pinch_release": defaults.pinch_release}
        )
    if settings.thumb_dir_enter_deg <= settings.thumb_dir_exit_deg:
        warnings.append(
            "thumb_dir_enter_deg must be above thumb_dir_exit_deg: both reset to their defaults"
        )
        defaults = Settings()
        settings = settings.model_copy(
            update={
                "thumb_dir_enter_deg": defaults.thumb_dir_enter_deg,
                "thumb_dir_exit_deg": defaults.thumb_dir_exit_deg,
            }
        )
    return settings, warnings


def save(settings: Settings, path: Path | None = None) -> Path:
    """Write the full settings file atomically (a crash never leaves half a file)."""
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(settings.model_dump(), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def load(path: Path | None = None) -> tuple[Settings, list[str]]:
    """Load settings. A missing file is created with the defaults. A broken file is never
    overwritten (the user may want to fix it), and defaults are used with a warning."""
    path = path or default_path()
    if not path.exists():
        settings = Settings()
        try:
            save(settings, path)
        except OSError as exc:
            return settings, [f"could not create {path}: {exc}"]
        return settings, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Settings(), [f"could not read {path.name} ({exc}): using defaults"]
    return parse(data)


def reset(path: Path | None = None) -> tuple[Settings, list[str]]:
    """Rewrite the file with the defaults."""
    settings = Settings()
    try:
        save(settings, path)
    except OSError as exc:
        return settings, [f"could not write settings: {exc}"]
    return settings, []
