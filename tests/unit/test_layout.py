import itertools

import pytest

from gescrtl.core import layout

GROUPS = {
    "menu": layout.MODE_MENU_ITEMS,
    "levels": layout.LEVEL_SLIDERS,
    "media": layout.MEDIA_TARGETS,
    "level_steps": layout.LEVEL_STEP_TARGETS,
    "keyboard_bottom": layout.keyboard_keys("bottom"),
    "keyboard_top": layout.keyboard_keys("top"),
}
SCREENS = [(1280, 720), (1920, 1080), (2560, 1440)]


@pytest.mark.parametrize("name", GROUPS)
@pytest.mark.parametrize(("w", "h"), SCREENS)
def test_every_target_is_at_least_48_px(name, w, h):
    for ident, r in GROUPS[name]:
        assert r.w * w >= 48 and r.h * h >= 48, (ident, r.w * w, r.h * h)


@pytest.mark.parametrize("name", GROUPS)
def test_targets_stay_on_screen_and_do_not_overlap(name):
    items = GROUPS[name]
    for ident, r in items:
        assert 0 <= r.x and r.x + r.w <= 1 and 0 <= r.y and r.y + r.h <= 1, ident
    for (a, ra), (b, rb) in itertools.combinations(items, 2):
        apart = (
            ra.x + ra.w <= rb.x or rb.x + rb.w <= ra.x or ra.y + ra.h <= rb.y or rb.y + rb.h <= ra.y
        )
        assert apart, (a, b)


def test_ids_are_unique_and_complete():
    assert [i for i, _ in layout.MODE_MENU_ITEMS] == [
        "pointer",
        "keyboard",
        "presentation",
        "media",
    ]
    assert [i for i, _ in layout.LEVEL_SLIDERS] == ["volume", "brightness"]
    media = [i for i, _ in layout.MEDIA_TARGETS]
    assert len(media) == len(set(media)) == 10


def centre(items, ident):
    r = dict(items)[ident]
    return r.x + r.w / 2, r.y + r.h / 2


def test_hit_returns_target_only_when_inside_by_the_margin():
    items = layout.MODE_MENU_ITEMS
    cx, cy = centre(items, "pointer")
    assert layout.hit(items, cx, cy, 0.01) == "pointer"
    r = dict(items)["pointer"]
    assert layout.hit(items, r.x + 0.005, cy, 0.01) is None  # on the edge band
    assert layout.hit(items, r.x - 0.01, cy, 0.01) is None  # outside
    gap_x = r.x + r.w + 0.01  # in the gap between two items
    assert layout.hit(items, gap_x, cy, 0.01) is None


def test_hit_keeps_the_current_target_until_the_pointer_leaves_it():
    items = layout.MODE_MENU_ITEMS
    r = dict(items)["pointer"]
    cy = r.y + r.h / 2
    edge_x = r.x + 0.002  # inside the rect but within the margin band
    assert layout.hit(items, edge_x, cy, 0.01, current=None) is None
    assert layout.hit(items, edge_x, cy, 0.01, current="pointer") == "pointer"  # no flicker
    assert layout.hit(items, r.x - 0.002, cy, 0.01, current="pointer") is None  # left the rect


def test_hit_switches_to_another_target_only_when_clearly_inside_it():
    items = layout.MODE_MENU_ITEMS
    other = dict(items)["keyboard"]
    cy = other.y + other.h / 2
    assert layout.hit(items, other.x + 0.002, cy, 0.01, current="pointer") is None
    cx, _ = centre(items, "keyboard")
    assert layout.hit(items, cx, cy, 0.01, current="pointer") == "keyboard"


def test_level_step_targets_do_not_touch_the_sliders():
    both = tuple(layout.LEVEL_SLIDERS) + tuple(layout.LEVEL_STEP_TARGETS)
    for (a, ra), (b, rb) in itertools.combinations(both, 2):
        apart = (
            ra.x + ra.w <= rb.x or rb.x + rb.w <= ra.x or ra.y + ra.h <= rb.y or rb.y + rb.h <= ra.y
        )
        assert apart, (a, b)


def test_keyboard_has_every_key_the_spec_lists():
    ids = {i for i, _ in layout.keyboard_keys("bottom")}
    letters = {f"k:{c}" for c in "abcdefghijklmnopqrstuvwxyz"}
    digits = {f"k:{c}" for c in "0123456789"}
    named = {"k:space", "k:backspace", "k:enter", "k:tab", "k:left", "k:right", "k:up", "k:down"}
    mods = {"m:shift", "m:ctrl", "m:alt", "m:win"}
    shortcuts = {
        "s:copy",
        "s:paste",
        "s:cut",
        "s:undo",
        "s:redo",
        "s:select_all",
        "s:alt_tab",
        "s:win",
        "s:esc",
    }
    assert (letters | digits | named | mods | shortcuts | {"move"}) <= ids
    assert len(ids) == len(layout.keyboard_keys("bottom"))


def test_keyboard_rect_holds_all_keys_at_the_bottom_or_the_top():
    for position in ("bottom", "top"):
        rect = layout.keyboard_rect(position)
        for ident, r in layout.keyboard_keys(position):
            assert rect.x <= r.x and r.x + r.w <= rect.x + rect.w + 1e-9, ident
            assert rect.y <= r.y and r.y + r.h <= rect.y + rect.h + 1e-9, ident
    assert layout.keyboard_rect("top").y < 0.1 < 0.5 < layout.keyboard_rect("bottom").y


def test_every_key_can_be_pointed_at_with_the_margin_rule():
    for position in ("bottom", "top"):
        keys = layout.keyboard_keys(position)
        for ident, r in keys:
            cx, cy = r.x + r.w / 2, r.y + r.h / 2
            assert layout.hit(keys, cx, cy, 0.01) == ident
