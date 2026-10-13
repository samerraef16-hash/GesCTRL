"""US4: the movement range covers all monitors as one area (spec 004 D8, FR-020, FR-021)."""

import pytest
from support.hands import Script, resume_script, run

from gescrtl.core.engine import Engine
from gescrtl.core.types import Click, Command, MoveCursor, Pose, Warning
from gescrtl.recording import jsonl

TWO = [(0, 0, 1920, 1080), (1920, 0, 1280, 1024)]


def moves(ev):
    return [e for e in ev if isinstance(e, MoveCursor)]


def at(corner, layout=None, settle=1500):
    """Move the hand so the cursor is at ``corner`` of the movement range and return the moves."""
    eng = Engine()
    s = resume_script()
    if layout:
        s.displays(layout)
    s.hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s.move(Pose.G1_RELAXED, to=corner, ms=settle).hold(Pose.G1_RELAXED, 1500)
    return eng, moves(run(eng, s.frames()))


def test_without_a_layout_the_cursor_is_normalized_over_the_primary_monitor_as_before():
    _, ev = at((0.9, 0.9))
    assert (ev[-1].nx, ev[-1].ny) == (1.0, 1.0)


def test_with_a_layout_the_whole_range_spans_all_monitors():
    _, left = at((0.1, 0.5), TWO)
    _, right = at((0.9, 0.5), TWO)
    assert left[-1].nx == 0.0
    assert right[-1].nx == pytest.approx(1.0, abs=2 / 3200)


def test_the_hand_at_the_centre_is_on_the_first_monitor_when_it_is_wider():
    _, ev = at((0.5, 0.5), TWO)
    assert ev[-1].nx * 3200 < 1920


def test_the_far_corner_below_the_shorter_monitor_is_clamped_onto_it():
    _, ev = at((0.9, 0.9), TWO)
    last = ev[-1]
    assert last.nx * 3200 == pytest.approx(3199, abs=1)
    assert last.ny * 1080 == pytest.approx(1023, abs=1)  # the bottom row of monitor B


def test_every_cursor_position_is_on_a_monitor_for_a_staggered_layout():
    staggered = [(0, 0, 1920, 1080), (1920, -300, 1920, 1080)]
    eng = Engine()
    s = resume_script().displays(staggered).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    for corner in [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]:
        s.move(Pose.G1_RELAXED, to=corner, ms=1200).hold(Pose.G1_RELAXED, 500)
    box_x, box_y, box_w, box_h = 0, -300, 3840, 1380
    for m in moves(run(eng, s.frames())):
        px, py = box_x + m.nx * box_w, box_y + m.ny * box_h
        assert any(x <= px <= x + w - 1 and y <= py <= y + h - 1 for x, y, w, h in staggered), (
            px,
            py,
        )


def test_a_new_layout_while_running_takes_effect_at_once():
    eng = Engine()
    s = resume_script().hold(Pose.G1_RELAXED, 500, at=(0.8, 0.5)).hold(Pose.G1_RELAXED, 1000)
    run(eng, s.frames())
    s2 = s.next().displays(TWO).hold(Pose.G1_RELAXED, 1500, at=(0.8, 0.5))
    ev = moves(run(eng, s2.frames()))
    assert ev and ev[-1].nx == pytest.approx(1.0, abs=2 / 3200) and eng.displays is not None
    s3 = s2.next().displays([(0, 0, 1920, 1080)]).hold(Pose.G1_RELAXED, 1500, at=(0.8, 0.5))
    assert moves(run(eng, s3.frames()))[-1].nx == pytest.approx(1.0, abs=2 / 1920)
    assert eng.displays.w == 1920


def test_an_unusable_layout_is_ignored_with_a_warning():
    eng = Engine()
    s = resume_script().displays(TWO)
    run(eng, s.frames())
    ev = eng.command(Command.DISPLAYS, s.t_ns + 1, "garbage")
    assert any(isinstance(e, Warning) for e in ev) and eng.displays.w == 3200


def test_the_double_click_distance_stays_the_same_in_pixels():
    eng = Engine()
    eng.command(Command.DISPLAYS, 0, Script().displays(TWO).frames()[0].arg)
    assert eng.pointer.dist_scale == pytest.approx(1920 / 3200)
    eng.apply_config(eng.cfg)
    assert eng.pointer.dist_scale == pytest.approx(1920 / 3200)  # survives a settings reload


def test_two_taps_on_the_same_spot_still_double_click_with_a_layout():
    eng = Engine()
    s = resume_script().displays(TWO).hold(Pose.G1_RELAXED, 600, at=(0.4, 0.5))
    s.hold(Pose.G2_PINCH_INDEX, 120).hold(Pose.G1_RELAXED, 150)
    s.hold(Pose.G2_PINCH_INDEX, 120).hold(Pose.G1_RELAXED, 400)
    ev = run(eng, s.frames())
    clicks = [i for i, e in enumerate(ev) if isinstance(e, Click)]
    assert len(clicks) == 2
    snap = [e for e in ev[clicks[1] - 2 : clicks[1]] if isinstance(e, MoveCursor)]
    first = [e for e in ev[clicks[0] - 2 : clicks[0]] if isinstance(e, MoveCursor)]
    assert snap and first and (snap[-1].nx, snap[-1].ny) == (first[-1].nx, first[-1].ny)


def test_recorded_layouts_replay_to_the_same_events(tmp_path):
    s = resume_script().displays(TWO).hold(Pose.G1_RELAXED, 300, at=(0.5, 0.5))
    s.move(Pose.G1_RELAXED, to=(0.8, 0.8), ms=800).hold(Pose.G1_RELAXED, 500)
    path = tmp_path / "rec.jsonl"
    with jsonl.RecordingWriter(path) as rec:
        for item in s.frames():
            if hasattr(item, "cmd"):
                rec.command(item.t_ns, item.cmd, item.arg)
            else:
                rec.frame(item)
    live = [(round(m.nx, 3), round(m.ny, 3)) for m in moves(run(Engine(), s.frames()))]
    replayed = [(round(m.nx, 3), round(m.ny, 3)) for m in moves(run(Engine(), jsonl.read(path)))]
    assert live == replayed and live
