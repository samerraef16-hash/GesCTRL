from dataclasses import replace

from gescrtl.core.config import CoreConfig
from gescrtl.core.select import PinchSelector
from gescrtl.core.types import Pose

G1, G2 = Pose.G1_RELAXED, Pose.G2_PINCH_INDEX
FRAME_NS = 33_333_333


class Driver:
    """Feeds the selector frame by frame; ``stable`` follows ``raw`` after 3 frames."""

    def __init__(self, cfg: CoreConfig | None = None) -> None:
        self.sel = PinchSelector(cfg or CoreConfig())
        self.t = 1_000_000_000
        self.stable = G1
        self._cand = G1
        self._n = 0
        self.fired: list[str] = []

    def frame(self, pointed: str | None, raw: Pose) -> str | None:
        if raw is self.stable:
            self._n = 0
        elif raw is self._cand:
            self._n += 1
        else:
            self._cand, self._n = raw, 1
        if raw is not self.stable and self._n >= 3:
            self.stable, self._n = raw, 0
        out = self.sel.update(pointed, raw, self.stable, self.t)
        self.t += FRAME_NS
        if out is not None:
            self.fired.append(out)
        return out

    def run(self, pointed: str | None, raw: Pose, frames: int) -> None:
        for _ in range(frames):
            self.frame(pointed, raw)

    def wait(self, ms: int) -> None:
        self.t += ms * 1_000_000


def test_a_stable_pinch_on_a_target_fires_once_per_pinch():
    d = Driver()
    d.run("A", G1, 5)
    d.run("A", G2, 20)  # held a long time
    assert d.fired == ["A"]


def test_a_one_frame_pinch_does_nothing():
    d = Driver()
    d.run("A", G1, 5)
    d.run("A", G2, 1)
    d.run("A", G1, 5)
    assert d.fired == []


def test_pinch_with_no_target_does_nothing_even_if_the_hand_slides_onto_one_later():
    d = Driver()
    d.run(None, G1, 5)
    d.run(None, G2, 2)
    d.run("A", G2, 10)
    assert d.fired == []


def test_the_target_is_the_one_pointed_at_before_the_pinch_motion():
    d = Driver()
    d.run("A", G1, 5)
    d.run("B", G2, 10)  # the hand slid onto B as the pinch formed
    assert d.fired == ["A"]


def test_stale_stable_pinch_after_a_quick_release_cannot_fire_without_enough_raw_frames():
    cfg = replace(CoreConfig(), action_cooldown_ms=100)
    d = Driver(cfg)
    d.run("A", G1, 3)
    d.run("A", G2, 6)
    assert d.fired == ["A"]
    d.wait(200)
    d.sel.update("A", G1, G2, d.t)  # one released frame while stable is still the pinch
    d.t += FRAME_NS
    for _ in range(2):  # re-pinch: stable still G2, but raw is G2 for fewer than 3 frames
        assert d.sel.update("A", G2, G2, d.t) is None
        d.t += FRAME_NS
    assert d.sel.update("A", G2, G2, d.t) == "A"


def test_cooldown_blocks_a_quick_second_pinch_on_the_same_target():
    d = Driver()
    d.run("A", G1, 3)
    d.run("A", G2, 6)
    d.run("A", G1, 5)
    d.run("A", G2, 6)  # about 400 ms after the first fire is not yet over
    assert d.fired == ["A"]
    d.run("A", G1, 5)
    d.wait(500)
    d.run("A", G2, 6)
    assert d.fired == ["A", "A"]


def test_a_pinch_that_starts_during_the_cooldown_never_fires_late_while_held():
    d = Driver()
    d.run("A", G1, 3)
    d.run("A", G2, 6)
    d.run("A", G1, 5)
    d.run("A", G2, 30)  # held well past the end of the cooldown
    assert d.fired == ["A"]


def test_cooldown_is_per_target():
    d = Driver()
    d.run("A", G1, 3)
    d.run("A", G2, 6)
    d.run("B", G1, 5)
    d.run("B", G2, 6)
    assert d.fired == ["A", "B"]


def test_held_id_is_the_fired_target_while_the_pinch_stays_down():
    d = Driver()
    d.run("A", G1, 3)
    assert d.sel.held_id is None
    d.run("A", G2, 6)
    assert d.sel.held_id == "A"
    d.run("A", G1, 1)
    assert d.sel.held_id is None


def test_reset_forgets_a_pinch_in_progress():
    d = Driver()
    d.run("A", G1, 3)
    d.run("A", G2, 2)
    d.sel.reset()
    d.run("A", G2, 6)  # a fresh pinch after the reset is evaluated from its own start
    assert d.fired == ["A"]
