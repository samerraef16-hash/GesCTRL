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
    Pose.G9_CALL_ME,
    Pose.G10_INDEX_POINT,
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


def test_call_me_builder_has_the_intended_features():
    f = feats(Pose.G9_CALL_ME)
    assert all(f.curled(i) for i in range(3))
    assert f.extended(3)  # pinky out
    assert f.thumb_extended and f.pinch_index > 0.8


def test_index_point_builder_has_the_intended_features():
    f = feats(Pose.G10_INDEX_POINT)
    assert f.extended(0)
    assert all(f.curled(i) for i in (1, 2, 3))
    assert not f.thumb_extended


def test_call_me_works_with_the_thumb_on_either_side():
    c = PoseClassifier(CoreConfig())
    assert c.classify(feats(Pose.G9_CALL_ME, thumb_right=True)) is Pose.G9_CALL_ME


def test_scroll_pose_with_slightly_loose_pinky_stays_scroll_not_call_me():
    # pinky tip/pip 1.02 is still "curled" (< 1.05): the scroll pose must not become call-me
    f = feats(Pose.G4_THUMBS_UP, pinky_curl=1.02, thumb_tilt_deg=30)
    assert PoseClassifier(CoreConfig()).classify(f) is Pose.G4_THUMBS_UP


def test_thumb_out_with_pinky_in_between_is_never_call_me():
    # 1.10 is neither curled nor extended: ambiguous, so it must not open the level panel
    f = feats(Pose.G4_THUMBS_UP, pinky_curl=1.10)
    assert PoseClassifier(CoreConfig()).classify(f) is not Pose.G9_CALL_ME


def test_index_point_needs_the_thumb_clear_of_the_index_tip():
    # a thumb approaching a pinch must keep the hand "relaxed", not "index point"
    c = PoseClassifier(CoreConfig())
    f = feats(Pose.G2_PINCH_INDEX, pinch_ratio=0.45)
    assert c.classify(f) is Pose.G1_RELAXED


def test_two_fingers_up_is_relaxed_not_index_point():
    assert PoseClassifier(CoreConfig()).classify(feats(Pose.G1_RELAXED)) is Pose.G1_RELAXED
