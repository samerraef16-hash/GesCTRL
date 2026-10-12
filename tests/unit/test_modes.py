from support.hands import pose

from gescrtl.core import features
from gescrtl.core.config import CoreConfig
from gescrtl.core.modes import NullController, PointerController
from gescrtl.core.pointer import Pointer
from gescrtl.core.types import DEFAULT_ASPECT, MoveCursor, Pose


def feats(kind, **kw):
    f = features.compute(pose(kind, **kw), DEFAULT_ASPECT)
    assert f is not None
    return f


def test_pointer_controller_moves_and_is_not_busy_while_pointing():
    ctrl = PointerController(Pointer(CoreConfig()))
    ctrl.reset()
    out = ctrl.update(feats(Pose.G1_RELAXED), Pose.G1_RELAXED, Pose.G1_RELAXED, 1_000_000_000)
    assert any(isinstance(e, MoveCursor) for e in out)
    assert not ctrl.busy


def test_pointer_controller_is_busy_during_a_pinch():
    ctrl = PointerController(Pointer(CoreConfig()))
    ctrl.reset()
    ctrl.pointer._need_release = False
    f = feats(Pose.G2_PINCH_INDEX, pinch_ratio=0.1)
    ctrl.update(f, Pose.G2_PINCH_INDEX, Pose.G1_RELAXED, 1_000_000_000)
    assert ctrl.busy


def test_null_controller_does_nothing():
    ctrl = NullController()
    f = feats(Pose.G1_RELAXED)
    assert ctrl.update(f, Pose.G1_RELAXED, Pose.G1_RELAXED, 1) == []
    assert ctrl.reset() == []
    assert not ctrl.busy
