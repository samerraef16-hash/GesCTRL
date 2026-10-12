"""US1: open the mode menu, choose or cancel (spec 003 FR-001..FR-003, scenarios 1-6)."""

from dataclasses import replace

from support.hands import run
from support.menu import INPUT_EVENTS, open_menu, pinch, point_at, resumed

from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.modes import NullController
from gescrtl.core.state_machine import MODE_HINTS
from gescrtl.core.types import (
    Command,
    Mode,
    ModeChanged,
    MoveCursor,
    OverlayHidden,
    OverlayKind,
    OverlayShown,
    Pose,
    ReleaseAll,
    State,
    StateChanged,
    Sub,
)
from gescrtl.core.types import HintsShown as Hints


def first(events, kind, start=0):
    for i in range(start, len(events)):
        if isinstance(events[i], kind):
            return i
    return -1


def states(events):
    return [(e.state, e.sub, e.hud_text) for e in events if isinstance(e, StateChanged)]


def menu_shown(events):
    return [e for e in events if isinstance(e, OverlayShown) and e.kind is OverlayKind.MODE_MENU]


# -- opening -----------------------------------------------------------------------------------


def test_three_fingers_held_opens_the_menu_and_releases_everything():
    eng = Engine()
    ev = run(eng, open_menu().frames())
    assert eng.sub is Sub.MODE_MENU
    shown = first(ev, OverlayShown)
    assert shown >= 0 and menu_shown(ev)
    assert ReleaseAll("mode menu") in ev
    assert ev.index(ReleaseAll("mode menu")) < shown
    assert (State.ACTIVE, Sub.MODE_MENU, "Mode menu") in states(ev)


def test_three_fingers_held_too_short_does_not_open():
    eng = Engine()
    ev = run(eng, resumed().hold(Pose.G7_THREE_FINGERS, 600).hold(Pose.G1_RELAXED, 300).frames())
    assert eng.sub is Sub.NORMAL
    assert not menu_shown(ev)


def test_cursor_stops_when_three_fingers_are_shown_and_nothing_moves_while_the_menu_is_open():
    eng = Engine()
    ev = run(eng, open_menu(extra_ms=1500).frames())
    opened = first(ev, OverlayShown)
    assert not [e for e in ev[opened:] if isinstance(e, INPUT_EVENTS)]
    assert any(isinstance(e, MoveCursor) for e in ev[:opened])  # pointing worked before


# -- choosing ----------------------------------------------------------------------------------


def choose(ident):
    return pinch(point_at(open_menu(), ident))


def test_pointing_highlights_an_item():
    ev = run(Engine(), point_at(open_menu(), "presentation").frames())
    assert "presentation" in [e.highlight for e in menu_shown(ev)]


def test_pinch_on_presentation_switches_the_mode_and_shows_its_hints():
    eng = Engine()
    ev = run(eng, choose("presentation").frames())
    assert eng.sm.mode is Mode.PRESENTATION
    assert ModeChanged(Mode.PRESENTATION) in ev
    assert (State.ACTIVE, Sub.NORMAL, "Presentation") in states(ev)
    assert Hints(MODE_HINTS[Mode.PRESENTATION]) in ev
    assert first(ev, OverlayHidden) >= 0
    assert eng.sub is Sub.NORMAL


def test_pinch_on_media_switches_to_media():
    eng = Engine()
    run(eng, choose("media").frames())
    assert eng.sm.mode is Mode.MEDIA


def test_choosing_the_current_mode_closes_the_menu_without_a_mode_change():
    eng = Engine()
    ev = run(eng, choose("pointer").frames())
    assert eng.sub is Sub.NORMAL and eng.sm.mode is Mode.POINTER
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_nothing_is_sent_to_the_system_between_opening_and_choosing():
    ev = run(Engine(), choose("presentation").frames())
    opened, changed = first(ev, OverlayShown), first(ev, ModeChanged)
    assert opened < changed
    assert not [e for e in ev[opened:changed] if isinstance(e, INPUT_EVENTS)]


def test_the_pinch_that_chose_a_mode_does_not_click_afterwards():
    ev = run(Engine(), choose("presentation").frames())
    changed = first(ev, ModeChanged)
    assert not [e for e in ev[changed:] if isinstance(e, INPUT_EVENTS)]


def test_keyboard_is_listed_but_cannot_be_chosen():
    eng = Engine()
    ev = run(eng, choose("keyboard").frames())
    assert eng.sub is Sub.MODE_MENU and eng.sm.mode is Mode.POINTER
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_pinch_in_the_gap_between_items_does_nothing():
    # the gap between "keyboard" and "presentation" is 0.03 wide, centred at x = 0.5
    s = open_menu()
    s = point_at(s, "keyboard", dx=0.0)
    s.move(Pose.G1_RELAXED, to=(0.2 + 0.6 * 0.5, 0.5), ms=500).hold(Pose.G1_RELAXED, 500)
    eng = Engine()
    ev = run(eng, pinch(s).frames())
    assert eng.sub is Sub.MODE_MENU
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_a_one_frame_pinch_or_fist_does_nothing():
    s = point_at(open_menu(), "presentation")
    s.hold(Pose.G2_PINCH_INDEX, 33).hold(Pose.G1_RELAXED, 400)
    s.hold(Pose.G5_FIST, 33).hold(Pose.G1_RELAXED, 400)
    eng = Engine()
    ev = run(eng, s.frames())
    assert eng.sub is Sub.MODE_MENU
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_a_second_hand_cannot_choose_or_cancel():
    s = open_menu()
    to = point_at(s, "presentation")
    # the primary hand keeps pointing at Presentation while another hand pinches and makes a fist
    to.hold(Pose.G1_RELAXED, 800, others=[(Pose.G2_PINCH_INDEX, (0.9, 0.9))])
    to.hold(Pose.G1_RELAXED, 800, others=[(Pose.G5_FIST, (0.9, 0.9))])
    eng = Engine()
    ev = run(eng, to.frames())
    assert eng.sub is Sub.MODE_MENU
    assert not [e for e in ev if isinstance(e, ModeChanged)]


# -- cancelling and closing --------------------------------------------------------------------


def test_fist_cancels_and_leaves_the_mode_unchanged():
    eng = Engine()
    ev = run(eng, point_at(open_menu(), "presentation").hold(Pose.G5_FIST, 500).frames())
    assert eng.sub is Sub.NORMAL and eng.sm.mode is Mode.POINTER
    assert first(ev, OverlayHidden) >= 0
    assert not [e for e in ev if isinstance(e, ModeChanged)]


def test_menu_closes_after_five_seconds_without_a_choice():
    eng = Engine()
    s = open_menu().hold(Pose.G1_RELAXED, 4000)
    run(eng, s.frames())
    assert eng.sub is Sub.MODE_MENU  # about 4.4 s after opening
    run(eng, s.next().hold(Pose.G1_RELAXED, 1500).frames())
    assert eng.sub is Sub.NORMAL and eng.sm.mode is Mode.POINTER


def test_a_timed_out_menu_does_not_reopen_while_three_fingers_stay_up():
    eng = Engine()
    ev = run(eng, open_menu(extra_ms=6500).frames())
    assert len(menu_shown(ev)) >= 1
    assert eng.sub is Sub.NORMAL
    assert len([e for e in ev if isinstance(e, OverlayShown) and e.highlight == ""]) == 1


def test_hand_loss_closes_the_menu_and_keeps_the_mode():
    eng = Engine()
    s = point_at(open_menu(), "presentation").none(ms=300)
    ev = run(eng, s.frames())
    assert eng.state is State.TRACKING_LOST
    assert first(ev, OverlayHidden) >= 0
    assert eng.sm.mode is Mode.POINTER
    ev2 = run(eng, s.next().hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5)).frames())
    assert (State.ACTIVE, Sub.NORMAL, "Pointer") in states(ev2)


def test_pause_command_closes_the_menu():
    eng = Engine()
    ev = run(eng, open_menu().cmd(Command.PAUSE).frames())
    assert eng.state is State.PAUSED
    assert first(ev, OverlayHidden) >= 0


def test_emergency_stop_closes_the_menu():
    eng = Engine()
    ev = run(eng, open_menu().cmd(Command.EMERGENCY_STOP).frames())
    assert eng.state is State.PAUSED
    assert first(ev, OverlayHidden) >= 0
    assert ReleaseAll("emergency stop") in ev


def test_camera_loss_closes_the_menu():
    eng = Engine()
    ev = run(eng, open_menu().cmd(Command.CAMERA_LOST, "test").frames())
    assert eng.state is State.TRACKING_LOST and eng.sub is Sub.CAMERA_UNAVAILABLE
    assert first(ev, OverlayHidden) >= 0


def test_turn_off_closes_the_menu():
    eng = Engine()
    ev = run(eng, open_menu().cmd(Command.TURN_OFF).frames())
    assert eng.state is State.INACTIVE
    assert first(ev, OverlayHidden) >= 0


# -- busy gesture ------------------------------------------------------------------------------


class BusyController(NullController):
    def __init__(self):
        self.is_busy = True

    @property
    def busy(self):
        return self.is_busy


def test_three_fingers_are_ignored_while_an_action_is_in_progress_until_the_hand_relaxes():
    eng = Engine()
    s0 = resumed()
    run(eng, s0.frames())
    busy = BusyController()
    eng._controllers[Mode.POINTER] = busy
    s = s0.next().hold(Pose.G7_THREE_FINGERS, 2000, at=(0.5, 0.5))
    run(eng, s.frames())
    assert eng.sub is Sub.NORMAL  # busy the whole time: no menu
    busy.is_busy = False
    s2 = s.next().hold(Pose.G7_THREE_FINGERS, 1500)
    run(eng, s2.frames())
    assert eng.sub is Sub.NORMAL  # still the same three-finger hold: needs a relaxed hand first
    s3 = s2.next().hold(Pose.G1_RELAXED, 400).hold(Pose.G7_THREE_FINGERS, 1500)
    run(eng, s3.frames())
    assert eng.sub is Sub.MODE_MENU


def test_menu_hold_time_is_configurable():
    eng = Engine(replace(CoreConfig(), menu_hold_ms=2000))
    run(eng, resumed().hold(Pose.G7_THREE_FINGERS, 1200).frames())
    assert eng.sub is Sub.NORMAL


# -- determinism -------------------------------------------------------------------------------


def test_replaying_the_same_session_twice_gives_identical_events():
    script = choose("presentation").frames()
    assert run(Engine(), script) == run(Engine(), script)
