"""US4: reloading settings is safe mid-gesture and changes behaviour (FR-024a)."""

import dataclasses

from support.hands import resume_script, run

from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import ButtonDown, MoveCursor, Pose, ReleaseAll

G1, G2 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX


def active(cfg=None):
    eng = Engine(cfg)
    s = resume_script()
    run(eng, s.frames())
    return eng, s.next()


def test_reload_during_a_drag_releases_first_and_keeps_state():
    eng, s = active()
    s.hold(G1, 300, at=(0.4, 0.4)).hold(G2, 500)
    ev = run(eng, s.frames())
    assert any(isinstance(e, ButtonDown) for e in ev)
    state, sub = eng.state, eng.sub
    out = eng.apply_config(dataclasses.replace(CoreConfig(), active_region=0.8))
    assert isinstance(out[0], ReleaseAll)
    assert (eng.state, eng.sub) == (state, sub)
    # the pinch is still held after the reload: no automatic second press
    ev2 = run(eng, s.next().hold(G2, 600).frames())
    assert not any(isinstance(e, ButtonDown) for e in ev2)


def travel(cfg):
    eng, s = active(cfg)
    s.hold(G1, 300, at=(0.4, 0.5)).move(G1, to=(0.6, 0.5), ms=600).hold(G1, 200)
    moves = [e for e in run(eng, s.frames()) if isinstance(e, MoveCursor)]
    return moves[-1].nx - moves[0].nx


def test_a_new_active_region_changes_the_hand_travel_mapping():
    small = travel(dataclasses.replace(CoreConfig(), active_region=0.4))
    large = travel(dataclasses.replace(CoreConfig(), active_region=0.8))
    assert small > large * 1.5  # smaller region = the same hand movement covers more screen


def test_reload_applies_to_a_running_engine():
    eng, s = active()
    s.hold(G1, 300, at=(0.4, 0.5))
    run(eng, s.frames())
    eng.apply_config(dataclasses.replace(CoreConfig(), active_region=0.4))
    s2 = s.next().move(G1, to=(0.6, 0.5), ms=600).hold(G1, 200)
    moves = [e for e in run(eng, s2.frames()) if isinstance(e, MoveCursor)]
    assert moves[-1].nx - moves[0].nx > 0.4  # default region would give about 0.3
