import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gescrtl.tools.targets import TargetWindow, Trial, summarize, summary_lines  # noqa: E402


def test_summary_counts_hits_per_size():
    trials = [
        Trial(1, 24, "left", False, 20, 500),
        Trial(2, 24, "left", True, 3, 500),
        Trial(3, 48, "right", True, 3, 500),
    ]
    assert summarize(trials) == {24: (1, 2), 48: (1, 1)}
    assert any("48 px: 1/1" in line for line in summary_lines(trials))


@pytest.fixture
def window(tmp_path):
    QApplication.instance() or QApplication([])
    w = TargetWindow(trials=2, out_dir=tmp_path, seed=1)
    w.resize(1000, 700)
    w.next_target()
    return w


def press(w, pos, button=Qt.MouseButton.LeftButton, double=False):
    kind = QEvent.Type.MouseButtonDblClick if double else QEvent.Type.MouseButtonPress
    ev = QMouseEvent(kind, pos, pos, button, button, Qt.KeyboardModifier.NoModifier)
    if double:
        w.mouseDoubleClickEvent(ev)
    else:
        w.mousePressEvent(ev)


def test_hit_miss_and_csv(window):
    window._action = "left"
    press(window, QPointF(window._center))  # right action, inside
    assert window.results[0].hit
    window._action = "left"
    press(window, QPointF(window._center.x() + 500, window._center.y() + 400))  # outside
    assert not window.results[1].hit
    assert window.csv_path is not None and window.csv_path.exists()
    assert window.csv_path.read_text().splitlines()[0].startswith("trial,size_px")


def test_wrong_button_is_a_miss(window):
    window._action = "left"
    press(window, QPointF(window._center), Qt.MouseButton.RightButton)
    assert not window.results[0].hit


def test_double_click_needs_the_second_press(window):
    window._action = "double"
    press(window, QPointF(window._center))
    press(window, QPointF(window._center), double=True)
    assert window.results[0].hit
