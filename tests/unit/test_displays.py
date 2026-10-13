"""Monitor layout math: one area over all monitors, gaps clamp to the nearest screen (D8)."""

import json

import pytest

from gescrtl.core.displays import Display, Displays


def two_side_by_side():
    return Displays(
        (Display(0, 0, 1920, 1080, True, "A"), Display(1920, 0, 1280, 1024, False, "B"))
    )


def test_the_box_covers_every_monitor():
    d = two_side_by_side()
    assert (d.x, d.y, d.w, d.h) == (0, 0, 3200, 1080)


def test_a_negative_origin_is_supported():
    d = Displays((Display(-1920, 0, 1920, 1080), Display(0, 0, 2560, 1440, True)))
    assert (d.x, d.y, d.w, d.h) == (-1920, 0, 4480, 1440)


def test_points_on_a_monitor_are_unchanged():
    d = two_side_by_side()
    for p in [(0.0, 0.0), (0.3, 0.5), (0.7, 0.9), (0.999, 0.0)]:
        assert d.clamp(*p) == p


def test_the_corners_of_every_monitor_are_reachable():
    d = two_side_by_side()
    assert d.clamp(0.0, 0.0) == (0.0, 0.0)
    nx, ny = d.clamp(1.0, 0.0)
    assert nx * d.w == pytest.approx(3199, abs=1) and ny == 0.0


def test_below_a_shorter_monitor_clamps_to_its_bottom_edge():
    d = two_side_by_side()
    nx, ny = d.clamp(1.0, 1.0)  # the box corner is below monitor B (1024 high)
    assert nx * d.w == pytest.approx(3199, abs=1) and ny * d.h == pytest.approx(1023, abs=1)


def test_a_gap_between_monitors_goes_to_the_nearest_one():
    d = Displays((Display(0, 0, 1920, 1080, True), Display(2000, 0, 1920, 1080)))
    left = d.clamp(1950 / d.w, 0.5)
    right = d.clamp(1990 / d.w, 0.5)
    assert left[0] * d.w == pytest.approx(1919, abs=1)
    assert right[0] * d.w == pytest.approx(2000, abs=1)


def test_a_staggered_arrangement_never_lands_off_screen():
    d = Displays((Display(0, 0, 1920, 1080, True), Display(1920, -300, 1920, 1080)))
    nx, ny = d.clamp(0.1, 0.0)  # top-left of the box is above monitor A
    px, py = d.x + nx * d.w, d.y + ny * d.h
    assert 0 <= px <= 1919 and 0 <= py <= 1079


def test_the_double_click_distance_scale_keeps_the_pixel_distance():
    assert two_side_by_side().scale_x == pytest.approx(1920 / 3200)
    single = Displays((Display(0, 0, 1920, 1080, True),))
    assert single.scale_x == 1.0 and single.scale_y == 1.0


def test_parse_reads_the_command_argument():
    arg = json.dumps(
        [
            {"x": 0, "y": 0, "w": 100, "h": 50, "primary": True, "name": "A"},
            {"x": 100, "y": 0, "w": 100, "h": 50},
        ]
    )
    d = Displays.parse(arg)
    assert d is not None and len(d.displays) == 2 and d.displays[0].primary


@pytest.mark.parametrize(
    "bad", ["", "nope", "[]", "{}", '[{"x": 0}]', '[{"x":0,"y":0,"w":0,"h":10}]']
)
def test_unusable_layouts_are_rejected(bad):
    assert Displays.parse(bad) is None
