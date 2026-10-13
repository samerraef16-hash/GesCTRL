"""Custom gestures: descriptors, nearest neighbour, DTW, and movement segmentation (D9)."""

import math

import pytest
from support.hands import pose

from gescrtl.core import custom
from gescrtl.core.custom import (
    CustomGesture,
    MoveSegmenter,
    best_shape,
    dtw,
    resample,
    shape_descriptor,
)
from gescrtl.core.types import Hand, Landmark, Pose

ASPECT = 640 / 480
MS = 1_000_000


def desc(kind=Pose.G1_RELAXED, at=(0.5, 0.5), scale=0.2, **kw):
    d = shape_descriptor(pose(kind, at, scale=scale, **kw), ASPECT)
    assert d is not None
    return d


def dist(a, b):
    return math.dist(a, b)


def transformed(hand: Hand, angle_deg=0.0, mirror=False) -> Hand:
    """Rotate the hand around its wrist (in aspect-corrected space) and optionally mirror it."""
    wx, wy = hand.landmarks[0].x * ASPECT, hand.landmarks[0].y
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    out = []
    for p in hand.landmarks:
        x, y = p.x * ASPECT - wx, p.y - wy
        x, y = x * c - y * s, x * s + y * c
        if mirror:
            x = -x
        out.append(Landmark((wx + x) / ASPECT, wy + y, p.z))
    return Hand(tuple(out), "Left" if mirror else hand.handedness, hand.score)


def test_the_descriptor_does_not_depend_on_position_or_size():
    a = desc(at=(0.3, 0.4), scale=0.15)
    b = desc(at=(0.7, 0.6), scale=0.3)
    assert dist(a, b) < 0.02


def test_the_descriptor_does_not_depend_on_turning_the_hand_in_the_image():
    base = pose(Pose.G1_RELAXED, (0.5, 0.5))
    a = shape_descriptor(base, ASPECT)
    b = shape_descriptor(transformed(base, 35), ASPECT)
    assert dist(a, b) < 0.02


def test_a_mirrored_left_hand_matches_the_right_hand():
    base = pose(Pose.G1_RELAXED, (0.5, 0.5))
    assert (
        dist(shape_descriptor(base, ASPECT), shape_descriptor(transformed(base, 0, True), ASPECT))
        < 0.02
    )


def test_different_shapes_are_far_apart():
    index_middle = desc(Pose.G1_RELAXED)
    middle_only = desc(Pose.G3_PINCH_MIDDLE, pinch_ratio=0.6)
    fist = desc(Pose.G5_FIST)
    assert dist(index_middle, middle_only) > 0.4
    assert dist(index_middle, fist) > 0.6
    assert len(index_middle) == custom.SHAPE_DIM


def test_a_degenerate_hand_has_no_descriptor():
    flat = Hand(tuple(Landmark(0.5, 0.5) for _ in range(21)))
    assert shape_descriptor(flat, ASPECT) is None
    assert shape_descriptor(Hand(tuple(Landmark(0, 0) for _ in range(5))), ASPECT) is None


def gesture(name, samples, threshold=0.3, kind="shape"):
    return CustomGesture(name, kind, "MUTE", (), True, tuple(samples), threshold, "")


def test_best_shape_needs_to_be_inside_the_threshold():
    a = gesture("a", [desc(Pose.G1_RELAXED)])
    got, d = best_shape(desc(Pose.G1_RELAXED), [a])
    assert got is a and d < 0.05
    none, far = best_shape(desc(Pose.G5_FIST), [a])
    assert none is None and far > 0.3


def test_best_shape_refuses_when_two_gestures_fit_about_equally():
    a = gesture("a", [desc(Pose.G1_RELAXED)], threshold=5.0)
    b = gesture("b", [desc(Pose.G1_RELAXED, pinky_curl=1.0)], threshold=5.0)
    middle = tuple((x + y) / 2 for x, y in zip(a.samples[0], b.samples[0], strict=True))
    got, _ = best_shape(middle, [a, b])
    assert got is None
    got, _ = best_shape(a.samples[0], [a, b])
    assert got is a


def circle(n=60, r=1.0, turns=1.0):
    return [
        (
            r * math.cos(2 * math.pi * turns * i / (n - 1)),
            r * math.sin(2 * math.pi * turns * i / (n - 1)),
        )
        for i in range(n)
    ]


def line(n=60, length=2.0):
    return [(length * i / (n - 1), 0.0) for i in range(n)]


def test_resample_returns_equally_spaced_points_from_start_to_end():
    pts = resample(line(7, 6.0), 4)
    assert len(pts) == 4 and pts[0] == (0.0, 0.0) and pts[-1] == pytest.approx((6.0, 0.0))
    gaps = [math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False)]
    assert max(gaps) - min(gaps) < 1e-9
    assert resample([(1, 1), (1, 1)], 5) == [(1, 1)] * 5


def test_dtw_is_zero_for_the_same_path_and_ignores_speed():
    c = resample(circle(), 32)
    assert dtw(c, c) == pytest.approx(0.0)
    uneven = [circle(80)[min(i * i // 80, 79)] for i in range(80)]  # same circle, uneven speed
    assert dtw(c, resample(uneven, 32)) < 0.15


def test_dtw_is_large_for_different_paths():
    c, ln = resample(circle(), 32), resample(line(), 32)
    assert dtw(c, ln) > 0.3
    assert dtw(c, ln) == pytest.approx(dtw(ln, c))


# -- segmentation ---------------------------------------------------------------------------------


def feed(seg, points, step_ms=33, t0=0, size=0.2, shape=(0.0,) * 40, open_hand=True):
    """Feed palm positions (in hand sizes) and return the segments that completed."""
    done = []
    for i, (x, y) in enumerate(points):
        s = seg.update(
            (x * size / ASPECT, y * size), size, ASPECT, t0 + i * step_ms * MS, shape, open_hand
        )
        if s is not None:
            done.append(s)
    return done


def still(n, at=(0.0, 0.0)):
    return [at] * n


def test_a_fast_movement_followed_by_stillness_is_one_segment():
    pts = (
        still(10) + [(x * 4.0, 0.0) for x in [i / 15 for i in range(1, 16)]] + still(12, (4.0, 0.0))
    )
    done = feed(MoveSegmenter(), pts)
    assert len(done) == 1
    seg = done[0]
    assert seg.points[0] == (0.0, 0.0) and seg.points[-1][0] == pytest.approx(4.0, abs=0.3)
    assert 300 < seg.duration_ms < 700


def test_slow_drift_is_not_a_movement():
    pts = [(i * 0.01, 0.0) for i in range(200)]
    assert feed(MoveSegmenter(), pts) == []


def test_a_tiny_fast_wiggle_is_too_short():
    pts = still(5) + [(0.0, 0.0), (0.1, 0.0), (0.0, 0.0), (0.1, 0.0)] + still(10)
    assert feed(MoveSegmenter(), pts) == []


def test_a_movement_that_never_settles_is_too_long():
    pts = [(math.sin(i / 3.0) * 2, math.cos(i / 3.0) * 2) for i in range(150)]
    assert feed(MoveSegmenter(), pts) == []


def test_a_discarded_segment_does_not_count():
    seg = MoveSegmenter()
    pts = still(5) + [(i * 0.25, 0.0) for i in range(1, 16)] + still(12, (3.75, 0.0))
    done = feed(seg, pts[:12])
    seg.discard()
    done += feed(seg, pts[12:], t0=12 * 33 * MS)
    assert done == []


def test_the_segment_remembers_whether_every_finger_was_extended():
    pts = still(5) + [(i * 0.25, 0.0) for i in range(1, 16)] + still(12, (3.75, 0.0))
    assert feed(MoveSegmenter(), pts, open_hand=True)[0].open_hand is True
    assert feed(MoveSegmenter(), pts, open_hand=False)[0].open_hand is False
