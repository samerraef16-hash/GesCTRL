"""US3: hold a pinch to drag, release to drop; every exit path lets go."""

from support.hands import resume_script, run
from support.registry import scenario

from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Button,
    ButtonDown,
    ButtonUp,
    Click,
    Command,
    CueChanged,
    CueKind,
    MoveCursor,
    Pose,
    ReleaseAll,
)

G1, G2 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX
A = (0.4, 0.4)


def active():
    eng = Engine()
    s = resume_script()
    run(eng, s.frames())
    s = s.next().hold(G1, 400, at=A)
    run(eng, s.frames())
    return eng, s.next()


def of(events, kind):
    return [e for e in events if isinstance(e, kind)]


@scenario("drag")
def drag_scenario():
    s = resume_script().hold(G1, 400, at=A).hold(G2, 450).move(G2, to=(0.7, 0.6), ms=500)
    s.hold(G1, 300)
    return s.frames()


def test_long_pinch_then_move_drags_and_drops_without_a_click():
    eng, s = active()
    s.hold(G2, 450).move(G2, to=(0.7, 0.6), ms=500).hold(G1, 300)
    ev = run(eng, s.frames())
    downs, ups = of(ev, ButtonDown), of(ev, ButtonUp)
    assert len(downs) == 1 and downs[0].button is Button.LEFT
    assert len(ups) == 1 and ev.index(downs[0]) < ev.index(ups[0])
    assert not of(ev, Click)
    moved = [e for e in ev[ev.index(downs[0]) : ev.index(ups[0])] if isinstance(e, MoveCursor)]
    assert moved and moved[-1].nx > moved[0].nx + 0.1  # the cursor followed the hand


def test_losing_the_hand_releases_and_never_re_presses():
    eng, s = active()
    s.hold(G2, 450).none(6).hold(G2, 600)  # returns still pinching
    ev = run(eng, s.frames())
    assert len(of(ev, ButtonDown)) == 1
    assert any(isinstance(e, ReleaseAll) for e in ev)
    s2 = s.next().hold(G1, 200).hold(G2, 450)  # let go, pinch again: a new drag is allowed
    assert len(of(run(eng, s2.frames()), ButtonDown)) == 1


def test_short_gap_does_not_end_the_drag():
    eng, s = active()
    s.hold(G2, 450).none(2).hold(G2, 300)
    ev = run(eng, s.frames())
    assert len(of(ev, ButtonDown)) == 1 and not of(ev, ButtonUp)


def test_pause_and_emergency_stop_and_turn_off_release_the_button():
    for command in (Command.PAUSE, Command.EMERGENCY_STOP, Command.TURN_OFF):
        eng, s = active()
        s.hold(G2, 450)
        run(eng, s.frames())
        ev = run(eng, s.next().cmd(command).hold(G2, 200).frames())
        assert any(isinstance(e, ReleaseAll) for e in ev), command
        assert not of(ev, ButtonDown), command


def test_cue_is_drag_while_dragging():
    eng, s = active()
    s.hold(G2, 450)
    cues = [e.kind for e in run(eng, s.frames()) if isinstance(e, CueChanged)]
    assert cues[-1] is CueKind.DRAG
