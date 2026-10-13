"""The custom gesture file: round trip, damage handling, and no images (spec 004 FR-027)."""

import json

from gescrtl.core.custom import PATH_POINTS, SHAPE_DIM, CustomGesture
from gescrtl.settings import custom_store as store
from gescrtl.settings import store as settings_store

MOVE_DIM = 1 + 2 * PATH_POINTS + SHAPE_DIM


def shape(name="peace", **kw):
    base = dict(
        name=name,
        kind="shape",
        action="PLAY_PAUSE",
        modes=(),
        enabled=True,
        samples=tuple(tuple(0.01 * i for i in range(SHAPE_DIM)) for _ in range(5)),
        threshold=0.4,
        created="2026-10-13",
    )
    base.update(kw)
    return CustomGesture(**base)


def move(name="circle", **kw):
    return shape(
        name,
        kind="move",
        samples=tuple(tuple(float(i) for i in range(MOVE_DIM)) for _ in range(5)),
        **kw,
    )


def test_round_trip_keeps_everything(tmp_path):
    path = tmp_path / "g.json"
    gestures = (shape(), move(modes=("MEDIA", "POINTER"), enabled=False))
    store.save(gestures, path)
    assert not list(tmp_path.glob("*.tmp"))
    loaded, warnings = store.load(path)
    assert loaded == gestures and warnings == []


def test_a_missing_file_means_no_gestures_and_nothing_is_created(tmp_path):
    path = tmp_path / "none.json"
    assert store.load(path) == ((), [])
    assert not path.exists()


def test_a_damaged_file_turns_custom_gestures_off_and_is_not_overwritten(tmp_path):
    path = tmp_path / "g.json"
    path.write_text("{ not json", encoding="utf-8")
    loaded, warnings = store.load(path)
    assert loaded == () and warnings and "custom gestures are off" in warnings[0]
    assert path.read_text(encoding="utf-8") == "{ not json"


def test_a_wrong_version_is_treated_as_damaged(tmp_path):
    path = tmp_path / "g.json"
    path.write_text(json.dumps({"version": 99, "gestures": []}), encoding="utf-8")
    assert store.load(path)[0] == () and store.load(path)[1]


def test_bad_entries_are_skipped_and_named_but_good_ones_load(tmp_path):
    path = tmp_path / "g.json"
    good = store._to_json(shape("good"))
    bad_action = {**store._to_json(shape("pause_gesture")), "action": "PAUSE"}
    bad_size = {**store._to_json(shape("short")), "samples": [[0.0] * 3]}
    bad_kind = {**store._to_json(shape("odd")), "kind": "blink"}
    bad_mode = {**store._to_json(shape("modes")), "modes": ["NOPE"]}
    twin = store._to_json(shape("good"))
    doc = {"version": 1, "gestures": [good, bad_action, bad_size, bad_kind, bad_mode, twin, 7]}
    path.write_text(json.dumps(doc), encoding="utf-8")
    loaded, warnings = store.load(path)
    assert [g.name for g in loaded] == ["good"] and len(warnings) == 6


def test_a_gesture_cannot_be_assigned_a_safety_action(tmp_path):
    path = tmp_path / "g.json"
    entry = {**store._to_json(shape()), "action": "EMERGENCY_STOP"}
    path.write_text(json.dumps({"version": 1, "gestures": [entry]}), encoding="utf-8")
    assert store.load(path)[0] == ()


def test_only_numbers_and_names_are_stored_never_images(tmp_path):
    path = tmp_path / "g.json"
    store.save((shape(), move()), path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    for entry in doc["gestures"]:
        assert set(entry) == {
            "name",
            "kind",
            "action",
            "modes",
            "enabled",
            "samples",
            "threshold",
            "created",
        }
        assert all(isinstance(v, float) for s in entry["samples"] for v in s)
    assert path.stat().st_size < 60_000


def test_edits_return_new_tuples():
    a, b = shape("a"), shape("b")
    both = store.upsert(store.upsert((), a), b)
    assert [g.name for g in both] == ["a", "b"]
    retrained = store.upsert(both, shape("a", threshold=0.9))
    assert [g.name for g in retrained] == ["b", "a"] and retrained[-1].threshold == 0.9
    assert [g.name for g in store.remove(both, "a")] == ["b"]
    assert [g.enabled for g in store.set_enabled(both, "a", False)] == [False, True]
    assert not any(g.enabled for g in store.disable_all(both))
    assert len(store.disable_all(both)) == 2  # disabled, not deleted


def test_reset_to_defaults_keeps_custom_gestures_but_turns_them_off(tmp_path):
    path = tmp_path / "g.json"
    store.save((shape(), move()), path)
    gestures, _ = store.load(path)
    settings, _ = settings_store.reset(tmp_path / "settings.json")
    assert settings.custom_gestures_enabled is False
    store.save(store.disable_all(gestures), path)
    after, _ = store.load(path)
    assert [g.name for g in after] == ["peace", "circle"] and not any(g.enabled for g in after)
