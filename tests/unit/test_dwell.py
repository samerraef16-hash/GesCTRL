"""DwellSelector: fire once after the dwell time, re-arm only after leaving (spec 004 D4)."""

from gescrtl.core.config import CoreConfig
from gescrtl.core.select import DwellSelector

MS = 1_000_000
CFG = CoreConfig(dwell_ms=500, dwell_still_dist=0.02)


def feed(sel, target, point, start_ms, end_ms, step=33):
    out = []
    for ms in range(start_ms, end_ms + 1, step):
        r = sel.update(target, point, ms * MS)
        if r:
            out.append((ms, r))
    return out


def test_fires_once_after_dwell_time():
    sel = DwellSelector(CFG)
    fired = feed(sel, "a", (0.5, 0.5), 0, 2000)
    assert [t for _, t in fired] == ["a"]
    assert 500 <= fired[0][0] <= 540


def test_progress_rises_and_resets():
    sel = DwellSelector(CFG)
    sel.update("a", (0.5, 0.5), 0)
    sel.update("a", (0.5, 0.5), 250 * MS)
    assert 0.45 < sel.progress < 0.55
    sel.update(None, (0.5, 0.5), 300 * MS)
    assert sel.progress == 0.0


def test_wandering_restarts_the_clock():
    sel = DwellSelector(CFG)
    fired = feed(sel, "a", (0.5, 0.5), 0, 400)
    sel.update("a", (0.55, 0.5), 450 * MS)  # moved more than the still distance
    assert not fired and sel.progress < 0.1


def test_rearms_only_after_leaving_and_returning():
    sel = DwellSelector(CFG)
    assert len(feed(sel, "a", (0.5, 0.5), 0, 1500)) == 1
    assert feed(sel, "a", (0.505, 0.5), 1600, 3000) == []  # small drift: still done
    feed(sel, "a", (0.6, 0.5), 3100, 3200)  # a real move, still on the target
    assert len(feed(sel, "a", (0.6, 0.5), 3300, 4500)) == 1


def test_a_new_target_starts_over():
    sel = DwellSelector(CFG)
    feed(sel, "a", (0.5, 0.5), 0, 300)
    assert feed(sel, "b", (0.5, 0.5), 333, 700) == []  # b has only been pointed for ~370 ms
