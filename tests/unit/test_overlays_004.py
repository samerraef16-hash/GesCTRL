"""Spec 004 overlays: keyboard, setup guide, +/- targets, remapped labels, tray entries."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gescrtl.core.types import (  # noqa: E402
    CueKind,
    CustomFired,
    KeyboardView,
    Level,
    Mode,
    ModeChanged,
    MoveCursor,
    OverlayHidden,
    OverlayKind,
    OverlayShown,
    SetupView,
    State,
    StateChanged,
    Sub,
)
from gescrtl.platform import displays  # noqa: E402
from gescrtl.platform.hud import Hud, style_for  # noqa: E402
from gescrtl.platform.overlays import (  # noqa: E402
    KeyboardOverlay,
    LevelPanelView,
    MediaGridView,
    ModeMenuView,
    SetupOverlay,
    key_label,
)
from gescrtl.platform.tray import Tray  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def painted(widget):
    pixmap = widget.grab()
    assert not pixmap.isNull() and pixmap.width() > 0
    return pixmap


def test_key_labels_follow_shift():
    assert key_label("k:a") == "a" and key_label("k:a", True) == "A"
    assert key_label("k:1", True) == "!" and key_label("k:/", True) == "?"
    assert key_label("k:backspace") == "⌫" and key_label("s:alt_tab") == "Alt+Tab"
    assert key_label("m:shift", True) == "Shift"


def test_the_keyboard_overlay_paints_every_state(qapp):
    view = KeyboardOverlay()
    for v in (
        KeyboardView(),
        KeyboardView(highlight="k:h", recent="hi there", position="bottom"),
        KeyboardView(highlight="k:g", dwell=0.6, position="top"),
        KeyboardView(pressed="k:h", oneshot=frozenset({"ctrl"}), locked=frozenset({"shift"})),
    ):
        view.show_view(v)
        painted(view)
    assert view.isVisible()
    view.close()


def test_the_setup_overlay_paints_guidance_and_the_corner_target(qapp):
    view = SetupOverlay()
    view.show_view(SetupView("reach", "Point to the top-left corner", 0.4, (0.0, 0.0)))
    painted(view)
    view.show_view(SetupView("check", "Checking the camera…", 0.0))
    painted(view)
    view.close()


def test_the_level_panel_draws_the_plus_and_minus_targets(qapp):
    view = LevelPanelView()
    view.set_value(Level.VOLUME, 40)
    view.set_value(Level.BRIGHTNESS, None)
    view.show_panel("volume_up")
    painted(view)
    view.close()


def test_the_media_grid_uses_remapped_labels(qapp):
    view = MediaGridView()
    view.show_grid("play_pause", "", (("play_pause", "Copy"),))
    assert view.labels == {"play_pause": "Copy"}
    painted(view)
    view.show_grid("", "")
    assert view.labels == {}
    view.close()


def test_the_mode_menu_offers_all_four_modes_without_a_later_label(qapp):
    view = ModeMenuView()
    view.show_menu(Mode.KEYBOARD, "keyboard")
    painted(view)
    view.close()


def test_the_hud_routes_keyboard_and_setup_events(qapp):
    hud = Hud(hint_ms=50)
    hud.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Keyboard"))
    hud.handle(KeyboardView(highlight="k:h"))
    assert hud.keyboard_view.isVisible()
    hud.handle(OverlayHidden(OverlayKind.KEYBOARD))
    assert not hud.keyboard_view.isVisible()
    hud.handle(KeyboardView(highlight="k:h"))
    hud.handle(OverlayHidden())  # an overlay opened over it: everything goes
    assert not hud.keyboard_view.isVisible()
    hud.handle(KeyboardView())
    hud.handle(StateChanged(State.PAUSED, Sub.NONE, "Paused"))
    assert not hud.keyboard_view.isVisible()
    hud.handle(StateChanged(State.ACTIVE, Sub.SETUP, "Setup"))
    hud.handle(SetupView("reach", "Point", 0.2, (1.0, 0.0)))
    assert hud.setup_view.isVisible()
    hud.handle(OverlayHidden())
    assert not hud.setup_view.isVisible()
    hud.close()


def test_a_fired_custom_gesture_is_named_on_the_pill(qapp):
    hud = Hud(hint_ms=200)
    hud.handle(StateChanged(State.ACTIVE, Sub.NORMAL, "Pointer"))
    hud.handle(CustomFired("peace", "PLAY_PAUSE"))
    assert hud.pill._hints and "peace" in hud.pill._hints[0] and "Play" in hud.pill._hints[0]
    hud.close()


def test_the_media_grid_event_carries_the_labels_to_the_view(qapp):
    hud = Hud()
    hud.handle(OverlayShown(OverlayKind.MEDIA, highlight="mute", labels=(("mute", "Paste"),)))
    assert hud.media_view.labels["mute"] == "Paste"
    hud.close()


def test_setup_is_blue_and_the_cue_knows_dwell(qapp):
    from gescrtl.platform.hud import BLUE

    assert style_for(State.ACTIVE, Sub.SETUP, "Setup")[0] == BLUE
    hud = Hud()
    hud.handle(MoveCursor(0.5, 0.5))
    hud.cue.set_cue(CueKind.DWELL, 0.5)
    painted(hud.cue)
    hud.close()


def test_the_cue_follows_the_cursor_over_a_multi_monitor_layout(qapp):
    screen = qapp.primaryScreen()
    geo, dpr = screen.geometry(), screen.devicePixelRatio()
    w, h = round(geo.width() * dpr), round(geo.height() * dpr)
    first = {"x": 0, "y": 0, "w": w, "h": h, "primary": True, "name": screen.name()}
    second = {"x": w, "y": 0, "w": 800, "h": 600, "primary": False, "name": "NOT-A-SCREEN"}
    displays.set_layout([first, second])
    try:
        hud = Hud()
        hud.handle(MoveCursor(w / (w + 800) / 2, 0.25))  # the middle of the first monitor
        cx, cy = hud.cue._center
        assert abs(cx - (geo.x() + geo.width() / 2)) <= 3
        assert abs(cy - (geo.y() + 0.25 * h / dpr)) <= 3
        hud.close()
    finally:
        displays.set_layout([])


def test_the_tray_has_settings_calibration_and_the_custom_gesture_switch(qapp):
    calls = []
    tray = Tray(
        lambda c: None,
        lambda: None,
        lambda: None,
        lambda: None,
        on_settings=lambda: calls.append("settings"),
        on_calibrate=lambda: calls.append("calibrate"),
        on_custom_off=lambda off: calls.append(("off", off)),
    )
    labels = {a.text(): a for a in tray._menu.actions()}
    assert "Settings…" in labels and "Calibrate…" in labels
    labels["Settings…"].trigger()
    labels["Calibrate…"].trigger()
    off = labels["Turn off custom gestures"]
    off.trigger()
    assert calls == ["settings", "calibrate", ("off", True)]
    tray.set_custom_off_checked(False)  # follows the settings without calling back
    assert not off.isChecked() and calls[-1] == ("off", True)
    tray.handle(ModeChanged(Mode.KEYBOARD))
    assert (
        tray.mode_actions[Mode.KEYBOARD].isChecked()
        and tray.mode_actions[Mode.KEYBOARD].isEnabled()
    )
    tray.close()
