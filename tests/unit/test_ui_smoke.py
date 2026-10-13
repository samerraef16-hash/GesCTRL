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


def test_pointer_markers_show_move_and_hide(qapp):
    from gescrtl.platform.overlays import LaserDot, SelectRing

    for marker in (SelectRing(), LaserDot()):
        marker.show_marker(0.5, 0.5)
        assert marker.isVisible()
        before = marker.pos()
        marker.show_marker(0.2, 0.8)
        assert marker.pos() != before
        marker.hide_marker()
        assert not marker.isVisible()
        marker.close()


def test_hud_routes_overlay_pointers_and_hides_them_when_not_active(qapp):
    from gescrtl.core.types import OverlayPointer, OverlayPointerHidden, PointerStyle

    hud = Hud(hint_ms=50)
    hud.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Presentation"))
    hud.handle(OverlayPointer(0.4, 0.4, PointerStyle.LASER))
    assert hud.laser.isVisible() and not hud.ring.isVisible()
    hud.handle(OverlayPointer(0.5, 0.5, PointerStyle.SELECT))
    assert hud.ring.isVisible() and not hud.laser.isVisible()
    hud.handle(OverlayPointerHidden())
    assert not hud.ring.isVisible() and not hud.laser.isVisible()
    hud.handle(OverlayPointer(0.4, 0.4, PointerStyle.LASER))
    hud.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert not hud.laser.isVisible()
    hud.close()


def test_mode_menu_view_draws_all_four_items_and_the_current_mode(qapp):
    from gescrtl.core.types import Mode
    from gescrtl.platform.overlays import ModeMenuView

    view = ModeMenuView()
    view.show_menu(Mode.MEDIA, "presentation")
    assert view.isVisible() and view.current is Mode.MEDIA and view.highlight == "presentation"
    image = view.grab().toImage()  # runs paintEvent offscreen
    assert not image.isNull()
    view.show_menu(Mode.POINTER, "")
    assert view.current is Mode.POINTER and view.highlight == ""
    view.hide()
    assert not view.isVisible()
    view.close()


def test_hud_shows_and_hides_the_mode_menu_and_tracks_the_mode(qapp):
    from gescrtl.core.types import (
        Mode,
        ModeChanged,
        OverlayHidden,
        OverlayKind,
        OverlayPointer,
        OverlayShown,
        PointerStyle,
    )

    hud = Hud(hint_ms=50)
    hud.handle(StateChanged(State.ACTIVE, Sub.MODE_MENU, "Mode menu"))
    hud.handle(OverlayShown(OverlayKind.MODE_MENU, highlight="media"))
    assert hud.menu_view.isVisible() and hud.menu_view.current is Mode.POINTER
    hud.handle(OverlayPointer(0.8, 0.5, PointerStyle.SELECT))
    assert hud.ring.isVisible()
    hud.handle(ModeChanged(Mode.MEDIA))
    hud.handle(OverlayHidden())
    assert not hud.menu_view.isVisible() and not hud.ring.isVisible()
    hud.handle(OverlayShown(OverlayKind.MODE_MENU))
    assert hud.menu_view.current is Mode.MEDIA
    hud.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert not hud.menu_view.isVisible()
    hud.close()


def test_pill_is_blue_while_the_mode_menu_is_open():
    from gescrtl.platform.hud import BLUE

    color, _ = style_for(State.ACTIVE, Sub.MODE_MENU, "Mode menu")
    assert color == BLUE


def test_tray_mode_submenu_follows_the_engine_and_forwards_picks(qapp):
    from gescrtl.core.types import Mode, ModeChanged

    picked: list[Mode] = []
    tray = Tray(lambda c: None, lambda: None, lambda: None, lambda: None, on_mode=picked.append)
    actions = tray.mode_actions
    assert list(actions) == [Mode.POINTER, Mode.PRESENTATION, Mode.MEDIA, Mode.KEYBOARD]
    assert actions[Mode.POINTER].isChecked() and actions[Mode.KEYBOARD].isEnabled()
    actions[Mode.MEDIA].trigger()
    assert picked == [Mode.MEDIA]
    assert actions[Mode.POINTER].isChecked() and not actions[Mode.MEDIA].isChecked()  # not yet
    tray.handle(ModeChanged(Mode.MEDIA))  # the engine confirmed
    assert actions[Mode.MEDIA].isChecked() and not actions[Mode.POINTER].isChecked()
    tray.handle(StateChanged(State.INACTIVE, Sub.NONE, ""))
    assert not tray._mode_menu.isEnabled()
    tray.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert tray._mode_menu.isEnabled()  # also works while Paused
    tray.close()


def test_level_panel_view_shows_both_values_and_the_unavailable_state(qapp):
    from gescrtl.core.types import Level
    from gescrtl.platform.overlays import LevelPanelView

    view = LevelPanelView()
    try:
        view.set_value(Level.VOLUME, 64)
        view.set_value(Level.BRIGHTNESS, None)
        view.show_panel("volume")
        assert view.isVisible() and view.values == {Level.VOLUME: 64, Level.BRIGHTNESS: None}
        assert view.grab().toImage().width() > 0  # paints without raising
        view.set_value(Level.BRIGHTNESS, 80)
        view.show_panel("")
        view.grab()
    finally:
        view.close()


def test_hud_shows_the_panel_updates_levels_and_hides_it(qapp):
    from gescrtl.core.types import Level, LevelReading, OverlayHidden, OverlayKind, OverlayShown
    from gescrtl.platform.hud import Hud

    hud = Hud()
    try:
        hud.handle(LevelReading(Level.VOLUME, 30))
        hud.handle(OverlayShown(OverlayKind.LEVELS, highlight="brightness"))
        assert hud.panel_view.isVisible() and hud.panel_view.highlight == "brightness"
        assert hud.panel_view.values[Level.VOLUME] == 30
        hud.handle(OverlayHidden())
        assert not hud.panel_view.isVisible()
    finally:
        hud.close()


def test_media_grid_view_draws_all_ten_targets_and_the_pending_confirmation(qapp):
    from gescrtl.platform.overlays import MediaGridView

    view = MediaGridView()
    try:
        view.show_grid("play_pause", "")
        assert view.isVisible() and view.highlight == "play_pause"
        assert view.grab().toImage().width() > 0
        view.show_grid("screenshot", "screenshot")
        view.grab()
        assert view.pending == "screenshot"
    finally:
        view.close()


def test_hud_shows_the_media_grid_and_hides_only_it_on_a_media_hide(qapp):
    from gescrtl.core.types import (
        OverlayHidden,
        OverlayKind,
        OverlayPointer,
        OverlayShown,
        PointerStyle,
    )

    hud = Hud()
    try:
        hud.handle(OverlayShown(OverlayKind.MEDIA, highlight="mute"))
        hud.handle(OverlayPointer(0.5, 0.5, PointerStyle.SELECT))
        assert hud.media_view.isVisible() and hud.media_view.highlight == "mute"
        hud.handle(OverlayShown(OverlayKind.MODE_MENU))
        hud.handle(OverlayHidden(OverlayKind.MEDIA))  # leaving Normal for the mode menu
        assert not hud.media_view.isVisible() and hud.menu_view.isVisible()
        hud.handle(OverlayHidden())
        assert not hud.menu_view.isVisible()
    finally:
        hud.close()
