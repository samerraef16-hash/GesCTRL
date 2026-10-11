"""Headless smoke test: HUD and tray accept core events without raising."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gescrtl.core.types import (  # noqa: E402
    Command,
    HintsShown,
    State,
    StateChanged,
    Sub,
    Warning,
)
from gescrtl.platform.hud import Hud, style_for  # noqa: E402
from gescrtl.platform.tray import Tray  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_hud_follows_state_events(qapp):
    hud = Hud(hint_ms=50)
    hud.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert hud.pill.isVisible()
    hud.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Pointer"))
    hud.handle(HintsShown(("Pinch: click", "Hold pinch: drag")))
    assert hud.pill.height() > 34  # expanded with hints
    hud.handle(StateChanged(State.TRACKING_LOST, Sub.HAND_MISSING, "Hand not visible"))
    hud.handle(StateChanged(State.INACTIVE, Sub.NONE, ""))
    assert not hud.pill.isVisible()
    hud.close()


def test_cursor_cue_follows_the_cursor_and_hides_when_not_active(qapp):
    from gescrtl.core.types import CueChanged, CueKind, MoveCursor

    hud = Hud()
    hud.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Pointer"))
    hud.handle(MoveCursor(0.5, 0.5))
    cues = [
        (CueKind.READY, 0.0),
        (CueKind.PINCH, 0.6),
        (CueKind.CLICK, 0.0),
        (CueKind.DRAG, 0.0),
        (CueKind.SCROLL, -0.5),
        (CueKind.CLUTCH, 0.0),
    ]
    for kind, prog in cues:
        hud.handle(CueChanged(kind, prog))
        assert hud.cue.isVisible()
        hud.cue.grab()  # paints without raising
    centre = hud.cue.geometry().center()
    hud.handle(MoveCursor(0.25, 0.75))
    assert hud.cue.geometry().center() != centre
    hud.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert not hud.cue.isVisible()
    hud.close()


def test_style_never_relies_on_colour_alone():
    colour, icon = style_for(State.TRACKING_LOST, Sub.CAMERA_UNAVAILABLE, "Camera unavailable")
    assert icon  # a warning icon accompanies the colour; the text is always drawn too


def test_tray_menu_follows_state_and_forwards_commands(qapp):
    sent: list[Command] = []
    tray = Tray(sent.append, lambda: None, lambda: None, lambda: None)
    tray.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Pointer"))
    assert tray._pause_action.text() == "Pause"
    tray.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert tray._pause_action.text() == "Resume"
    tray.handle(StateChanged(State.INACTIVE, Sub.NONE, ""))
    assert tray._power_action.text() == "Turn on" and not tray._pause_action.isEnabled()
    tray._pause_action.trigger()  # disabled: no-op
    tray._power_action.trigger()
    assert sent == [Command.TOGGLE_POWER]
    tray.handle(Warning("hello"))  # must not raise
    tray.close()


def test_preview_window_renders_frame_hand_and_readout(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QKeyEvent
    from support.hands import pose

    from gescrtl.core.engine import Engine
    from gescrtl.core.types import HandFrame, Pose
    from gescrtl.platform.preview import POSE_LABELS, PreviewWindow

    eng = Engine()
    hand = pose(Pose.G4_THUMBS_UP, (0.5, 0.5))
    frame = HandFrame(1, (hand, pose(Pose.G1_RELAXED, (0.2, 0.3))))
    eng.step(frame, 1)
    assert eng.debug is not None and eng.debug.raw is Pose.G4_THUMBS_UP

    win = PreviewWindow(0.6)
    assert set(POSE_LABELS) == set(Pose)  # every pose has a readable label
    win.show()
    win.grab()  # "Waiting for the camera" state paints
    image = QImage(640, 480, QImage.Format.Format_RGB888)
    image.fill(0x203040)
    win.set_frame(image, frame, eng.debug, 29.7)
    assert win.grab().width() > 0  # frame + skeleton + readout paint without raising
    win.set_frame(image, None, None, 0.0)  # no hand
    win.grab()
    for key in (Qt.Key.Key_S, Qt.Key.Key_D):  # clean-view toggles
        win.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
        win.grab()
    win.set_camera_off(True)
    win.grab()
    closed = []
    win.closed.connect(lambda: closed.append(True))
    win.close()
    assert closed
