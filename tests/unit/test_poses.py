import pytest
from support.hands import pose

from gescrtl.core import features
from gescrtl.core.config import CoreConfig
from gescrtl.core.poses import PoseClassifier, PoseTracker
from gescrtl.core.types import DEFAULT_ASPECT, Pose

ALL = [
    Pose.G1_RELAXED,
    Pose.G2_PINCH_INDEX,
    Pose.G3_PINCH_MIDDLE,
    Pose.G4_THUMBS_UP,
    Pose.G5_FIST,
    Pose.G6_OPEN_PALM,
    Pose.G7_THREE_FINGERS,
    Pose.G8_FLAT_HAND,
]


def feats(kind, **kw):
    f = features.compute(pose(kind, **kw), DEFAULT_ASPECT)
    assert f is not None
    return f


@pytest.mark.parametrize("kind", ALL)
def test_each_synthetic_pose_classifies_as_intended(kind):
    assert PoseClassifier(CoreConfig()).classify(feats(kind)) is kind


def test_anchor_is_where_the_hand_was_placed():
    f = feats(Pose.G1_RELAXED, at=(0.3, 0.7))
    assert f.anchor == pytest.approx((0.3, 0.7), abs=1e-6)


def test_ratios_do_not_depend_on_hand_size():
    near = feats(Pose.G2_PINCH_INDEX, scale=0.3)
    far = feats(Pose.G2_PINCH_INDEX, scale=0.1)
    assert near.pinch_index == pytest.approx(far.pinch_index, rel=1e-6)


def test_pinch_hysteresis_keeps_pinch_between_enter_and_release():
    c = PoseClassifier(CoreConfig())
    assert c.classify(feats(Pose.G2_PINCH_INDEX, pinch_ratio=0.1)) is Pose.G2_PINCH_INDEX
    for r in (0.24, 0.30, 0.34, 0.28):  # wobbling inside the hysteresis band
        assert c.classify(feats(Pose.G2_PINCH_INDEX, pinch_ratio=r)) is Pose.G2_PINCH_INDEX
    assert c.classify(feats(Pose.G2_PINCH_INDEX, pinch_ratio=0.40)) is Pose.G1_RELAXED


def test_hovering_above_enter_never_pinches():
    c = PoseClassifier(CoreConfig())
    for r in (0.26, 0.34, 0.27, 0.33, 0.30) * 4:
        assert c.classify(feats(Pose.G2_PINCH_INDEX, pinch_ratio=r)) is Pose.G1_RELAXED


def test_fist_with_thumb_near_curled_fingertips_is_not_a_pinch():
    # the synthetic fist puts the thumb right beside the curled index/middle tips
    f = feats(Pose.G5_FIST)
    assert f.pinch_index < 0.25
    assert PoseClassifier(CoreConfig()).classify(f) is Pose.G5_FIST


def test_stable_frames_delay_and_invalidate():
    cfg = CoreConfig(stable_frames=3)
    t = PoseTracker(cfg)
    assert t.update(Pose.G2_PINCH_INDEX, 1) is Pose.NONE
    assert t.update(Pose.G2_PINCH_INDEX, 2) is Pose.NONE
    assert t.update(Pose.G2_PINCH_INDEX, 3) is Pose.G2_PINCH_INDEX
    assert t.since_ns == 3
    # a bad frame keeps the stable pose but restarts any change
    t.invalidate()
    assert t.update(Pose.G1_RELAXED, 4) is Pose.G2_PINCH_INDEX
    assert t.update(Pose.G1_RELAXED, 5) is Pose.G2_PINCH_INDEX
    assert t.update(Pose.G1_RELAXED, 6) is Pose.G1_RELAXED
    t.reset()
    assert t.stable is Pose.NONE


def test_single_frame_noise_does_not_change_stable_pose():
    t = PoseTracker(CoreConfig())
    for i in range(5):
        t.update(Pose.G1_RELAXED, i)
    for i, raw in enumerate([Pose.G5_FIST, Pose.G1_RELAXED] * 4):
        assert t.update(raw, 10 + i) is Pose.G1_RELAXED


def test_thumbs_up_needs_the_thumb_away_from_the_index_tip():
    """A pinch approach (curled fingers, thumb out but near the index tip) must not scroll."""
    from dataclasses import replace

    up = feats(Pose.G4_THUMBS_UP)
    assert up.thumb_extended and up.pinch_index > 0.8
    near = replace(up, pinch_index=0.5)  # same hand, thumb closer to the index fingertip
    assert PoseClassifier(CoreConfig()).classify(near) is Pose.G5_FIST


def test_flat_hand_and_open_palm_differ_only_by_the_thumb():
    flat, palm = feats(Pose.G8_FLAT_HAND), feats(Pose.G6_OPEN_PALM)
    assert not flat.thumb_extended and palm.thumb_extended
    assert all(flat.extended(i) and palm.extended(i) for i in range(4))


def test_flat_hand_is_the_strict_pose():
    f = feats(Pose.G8_FLAT_HAND)
    assert f.flat_hand and f.upright


def test_thumb_halfway_across_the_palm_is_still_pointing_not_clutch():
    from dataclasses import replace

    between = replace(feats(Pose.G8_FLAT_HAND), thumb_out=0.6)  # past "out", not yet tucked
    assert not between.flat_hand
    assert PoseClassifier(CoreConfig()).classify(between) is Pose.G1_RELAXED


def test_tilted_hand_is_not_a_flat_hand():
    from dataclasses import replace

    f = replace(feats(Pose.G8_FLAT_HAND), upright_deg=45.0)
    assert not f.flat_hand
    assert PoseClassifier(CoreConfig()).classify(f) is Pose.G1_RELAXED


def test_thumb_near_a_fingertip_is_not_a_flat_hand():
    from dataclasses import replace

    f = replace(feats(Pose.G8_FLAT_HAND), pinch_middle=0.3)
    assert not f.flat_hand


def test_pinch_middle_is_ignored_on_an_upright_hand_with_four_straight_fingers():
    from dataclasses import replace

    f = replace(feats(Pose.G8_FLAT_HAND), pinch_middle=0.1, thumb_out=0.9)
    assert f.open_upright
    assert PoseClassifier(CoreConfig()).classify(f) is Pose.G6_OPEN_PALM


def test_real_right_click_pinch_still_works():
    assert (
        PoseClassifier(CoreConfig()).classify(feats(Pose.G3_PINCH_MIDDLE)) is Pose.G3_PINCH_MIDDLE
    )


def test_flat_hand_needs_more_frames_than_other_poses():
    cfg = CoreConfig()
    t = PoseTracker(cfg)
    for k in range(cfg.flat_hand_frames - 1):
        assert t.update(Pose.G8_FLAT_HAND, k) is Pose.NONE
    assert t.update(Pose.G8_FLAT_HAND, 99) is Pose.G8_FLAT_HAND
