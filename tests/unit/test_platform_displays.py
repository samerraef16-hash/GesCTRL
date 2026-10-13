"""Monitor enumeration, the watcher, and desktop-to-Qt mapping (spec 004 D8)."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gescrtl.core.displays import Displays  # noqa: E402
from gescrtl.platform import displays  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_enumeration_finds_at_least_one_monitor_with_a_primary():
    monitors = displays.enumerate_monitors()
    assert monitors and monitors[0]["primary"] is True
    for m in monitors:
        assert m["w"] > 0 and m["h"] > 0 and m["name"]


def test_the_json_is_understood_by_the_core():
    arg = displays.to_json(displays.enumerate_monitors())
    parsed = Displays.parse(arg)
    assert parsed is not None and parsed.w > 0 and json.loads(arg)[0]["primary"]


def fake(*layouts):
    seq = iter(layouts)
    last = []

    def enumerate_fn():
        nonlocal last
        last = next(seq, last)
        return last

    return enumerate_fn


A = {"x": 0, "y": 0, "w": 1920, "h": 1080, "primary": True, "name": "A"}
B = {"x": 1920, "y": 0, "w": 1280, "h": 1024, "primary": False, "name": "B"}


def test_the_watcher_reports_only_changes(qapp):
    reported = []
    w = displays.DisplayWatcher(reported.append, fake([A], [A], [A, B], [A, B], [A]), 60_000)
    assert w.poll() is True and w.poll() is False and w.poll() is True
    assert w.poll() is False and w.poll() is True
    assert len(reported) == 3
    assert len(json.loads(reported[1])) == 2 and len(json.loads(reported[2])) == 1
    w.stop()


def test_an_empty_answer_keeps_the_previous_layout(qapp):
    reported = []
    w = displays.DisplayWatcher(reported.append, fake([A], []), 60_000)
    assert w.poll() is True and w.poll() is False and len(reported) == 1
    w.stop()


def test_the_overlay_monitor_falls_back_to_the_primary_screen(qapp):
    displays.set_overlay_monitor("\\\\.\\DISPLAY99")
    assert displays.overlay_screen() is qapp.primaryScreen()
    displays.set_overlay_monitor("")
    assert displays.overlay_screen() is qapp.primaryScreen()


def test_desktop_to_qt_is_none_without_a_layout_and_maps_with_one(qapp):
    displays.set_layout([])
    assert displays.desktop_to_qt(0.5, 0.5) is None
    screen = qapp.primaryScreen()
    geo, dpr = screen.geometry(), screen.devicePixelRatio()
    mon = {
        "x": 0,
        "y": 0,
        "w": round(geo.width() * dpr),
        "h": round(geo.height() * dpr),
        "primary": True,
        "name": screen.name(),
    }
    displays.set_layout([mon])
    x, y = displays.desktop_to_qt(0.5, 0.5)
    assert abs(x - (geo.x() + geo.width() / 2)) <= 2 and abs(y - (geo.y() + geo.height() / 2)) <= 2
    displays.set_layout([])
