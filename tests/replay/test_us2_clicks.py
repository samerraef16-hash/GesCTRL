"""US2: a pinch tap clicks where aimed; two taps double-click; thumb-middle right-clicks."""

import math

from support.hands import Script, resume_script, run
from support.registry import scenario

from gescrtl.core.engine import Engine
from gescrtl.core.types import (
    Button,
    ButtonDown,
    Click,
    CueChanged,
    CueKind,
    MoveCursor,
    Pose,
)

G1, G2, G3 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX, Pose.G3_PINCH_MIDDLE
A, B = (0.45, 0.45), (0.55, 0.55)


def active():
    eng = Engine()
    s = resume_script()
    run(eng, s.frames())
    return eng, s.next()


def clicks(events, button=None):
    """(button, cursor position at the click) for every Click."""
    out, pos = [], None
    for e in events:
        if isinstance(e, MoveCursor):
            pos = (e.nx, e.ny)
        elif isinstance(e, Click) and (button is None or e.button is button):
            out.append((e.button, pos))
    return out


def last_move(events):
    return next((e.nx, e.ny) for e in reversed(events) if isinstance(e, MoveCursor))


def tap(s: Script, ms: int = 150, ratio=None, at=None, kind=G2) -> Script:
    return s.hold(kind, ms, at=at, pinch_ratio=ratio).hold(G1, 150)


@scenario("clicks")
def clicks_scenario():
    s = resume_script().hold(G1, 300, at=A)
    tap(s).hold(G1, 250)
    tap(s)
    s.hold(G1, 700, at=B)
    tap(s, kind=G3)
    return s.frames()


def test_tap_clicks_once_where_the_hand_was_before_the_pinch():
    eng, s = active()
    s.hold(G1, 400, at=A)
    before = last_move(run(eng, s.frames()))
    s2 = s.next().move(G2, to=(0.55, 0.52), ms=150).hold(G1, 300)  # hand drifts while pinching
    ev = run(eng, s2.frames())
    found = clicks(ev)
    assert len(found) == 1 and found[0][0] is Button.LEFT
    assert math.dist(found[0][1], before) < 0.03


def test_double_click_second_tap_uses_the_first_position():
    eng, s = active()
    s.hold(G1, 400, at=A)
    tap(s).hold(G1, 100)  # 250 ms between onsets
    s.move(G1, to=(0.455, 0.452), ms=60)  # small drift
    tap(s)
    found = clicks(run(eng, s.frames()), Button.LEFT)
    assert len(found) == 2
    assert math.dist(found[0][1], found[1][1]) < 1e-9


def test_taps_far_apart_in_time_each_use_their_own_position():
    eng, s = active()
    s.hold(G1, 400, at=A)
    tap(s).hold(G1, 700).move(G1, to=(0.46, 0.45), ms=60)
    tap(s)
    found = clicks(run(eng, s.frames()), Button.LEFT)
    assert len(found) == 2
    assert found[0][1] != found[1][1]


def test_right_click_once_and_cooldown_blocks_a_quick_second():
    eng, s = active()
    s.hold(G1, 400, at=A)
    tap(s, ms=150, kind=G3)
    assert len(clicks(run(eng, s.frames()), Button.RIGHT)) == 1
    eng2, s2 = active()
    s2.hold(G1, 400, at=A)
    s2.hold(G3, 120).hold(G1, 60).hold(G3, 120).hold(G1, 100)  # second within 300 ms
    assert len(clicks(run(eng2, s2.frames()), Button.RIGHT)) == 1


def test_hovering_near_the_pinch_threshold_never_clicks():
    eng, s = active()
    s.hold(G1, 400, at=A)
    for r in (0.27, 0.34, 0.28, 0.33, 0.30) * 6:
        s.hold(G2, 34, pinch_ratio=r)
    assert not clicks(run(eng, s.frames()))


def test_low_confidence_pinch_does_not_click():
    eng, s = active()
    s.hold(G1, 400, at=A).hold(G2, 300, score=0.3).hold(G1, 200)
    assert not clicks(run(eng, s.frames()))


def test_cue_goes_pinch_click_ready():
    eng, s = active()
    s.hold(G1, 400, at=A).hold(G2, 150).hold(G1, 400)
    kinds = [e.kind for e in run(eng, s.frames()) if isinstance(e, CueChanged)]
    kinds = [k for i, k in enumerate(kinds) if i == 0 or k is not kinds[i - 1]]
    assert kinds == [CueKind.PINCH, CueKind.CLICK, CueKind.READY]


def test_a_tap_never_becomes_a_drag():
    eng, s = active()
    s.hold(G1, 400, at=A)
    tap(s, ms=200)
    assert not any(isinstance(e, ButtonDown) for e in run(eng, s.frames()))
