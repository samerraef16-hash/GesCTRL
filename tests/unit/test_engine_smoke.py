from support.hands import Script, run

from gescrtl.core.engine import Engine
from gescrtl.core.types import MoveCursor, Pose, State, StateChanged


def script():
    return (
        Script()
        .hold(Pose.G6_OPEN_PALM, 1300, at=(0.5, 0.5))
        .move(Pose.G1_RELAXED, to=(0.7, 0.6), ms=500)
        .frames()
    )


def test_resume_then_move_is_deterministic():
    a = run(Engine(), script())
    b = run(Engine(), script())
    assert a == b
    assert any(isinstance(e, StateChanged) and e.state is State.ACTIVE for e in a)
    assert any(isinstance(e, MoveCursor) for e in a)
