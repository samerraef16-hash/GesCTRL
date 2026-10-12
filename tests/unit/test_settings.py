import dataclasses
import json

from gescrtl.core.config import CoreConfig
from gescrtl.settings import store
from gescrtl.settings.store import Settings


def test_missing_file_writes_defaults(tmp_path):
    path = tmp_path / "GesCRTL" / "settings.json"
    s, warnings = store.load(path)
    assert s == Settings() and not warnings
    assert json.loads(path.read_text()) == Settings().model_dump()


def test_valid_change_is_loaded(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"active_region": 0.8, "stable_frames": 4}')
    s, warnings = store.load(path)
    assert s.active_region == 0.8 and s.stable_frames == 4 and not warnings


def test_bad_value_falls_back_with_a_warning_and_others_still_load(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"active_region": -1, "scroll_max_rate": 900, "stable_frames": 2.5}')
    s, warnings = store.load(path)
    assert s.active_region == Settings().active_region
    assert s.scroll_max_rate == 900
    assert s.stable_frames == Settings().stable_frames
    assert any("active_region" in w for w in warnings)
    assert any("stable_frames" in w for w in warnings)


def test_wrong_types_are_rejected(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"active_region": "wide", "min_confidence": true}')
    s, warnings = store.load(path)
    assert s == Settings() and len(warnings) == 2


def test_bad_json_uses_defaults_and_does_not_overwrite(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{ not json")
    s, warnings = store.load(path)
    assert s == Settings() and warnings
    assert path.read_text() == "{ not json"


def test_json_that_is_not_an_object_uses_defaults(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("[1, 2]")
    s, warnings = store.load(path)
    assert s == Settings() and warnings


def test_unknown_keys_are_ignored_with_a_warning(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"nonsense": 1, "active_region": 0.7}')
    s, warnings = store.load(path)
    assert s.active_region == 0.7
    assert any("nonsense" in w for w in warnings)


def test_pinch_enter_must_stay_below_release(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"pinch_enter": 0.45, "pinch_release": 0.2}')
    s, warnings = store.load(path)
    assert (s.pinch_enter, s.pinch_release) == (0.25, 0.35)
    assert any("pinch_enter" in w for w in warnings)


def test_safety_behaviours_cannot_be_configured():
    banned = ("emergency", "hotkey", "release_all", "on_loss", "disable")
    names = set(Settings.model_fields)
    assert not [n for n in names if any(b in n for b in banned)]
    s, warnings = store.parse({"emergency_stop": False, "release_all_on_loss": False})
    assert s == Settings() and len(warnings) == 2


def test_reset_rewrites_the_defaults(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"active_region": 0.9}')
    s, warnings = store.reset(path)
    assert s == Settings() and not warnings
    assert store.load(path)[0] == Settings()


def test_save_is_atomic_and_round_trips(tmp_path):
    path = tmp_path / "s.json"
    custom = Settings(active_region=0.75, scroll_step=60)
    store.save(custom, path)
    assert not list(tmp_path.glob("*.tmp"))
    assert store.load(path)[0] == custom


def test_settings_mirror_core_config_so_they_cannot_drift():
    core = {f.name: getattr(CoreConfig(), f.name) for f in dataclasses.fields(CoreConfig)}
    core.pop("double_click_ms")  # comes from the OS
    assert {n: v for n, v in Settings().model_dump().items()} == core
    assert Settings().to_core_config(double_click_ms=400).double_click_ms == 400
    assert Settings(active_region=0.7).to_core_config().active_region == 0.7


def test_spec_003_defaults_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    s, warnings = store.load(path)
    assert warnings == []
    assert (s.menu_hold_ms, s.panel_hold_ms, s.swipe_min_frames, s.level_step) == (800, 500, 3, 2)
    cfg = s.to_core_config()
    assert cfg.thumb_dir_enter_deg == 50.0 and cfg.thumb_dir_exit_deg == 35.0
    again, warnings = store.load(path)
    assert warnings == [] and again == s


def test_out_of_range_spec_003_value_falls_back_with_warning(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"swipe_min_frames": 99, "level_step": 0}')
    s, warnings = store.load(path)
    assert (s.swipe_min_frames, s.level_step) == (3, 2)
    assert any("swipe_min_frames" in w for w in warnings)
    assert any("level_step" in w for w in warnings)


def test_thumb_direction_enter_must_stay_above_exit(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"thumb_dir_enter_deg": 30, "thumb_dir_exit_deg": 40}')
    s, warnings = store.load(path)
    assert (s.thumb_dir_enter_deg, s.thumb_dir_exit_deg) == (50.0, 35.0)
    assert any("thumb_dir_enter_deg" in w for w in warnings)
