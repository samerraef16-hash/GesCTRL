"""FR-029 / SC-009: replaying any scripted scenario twice gives identical events."""

from support.hands import run
from support.registry import SCENARIOS

from gescrtl.core.engine import Engine


def test_every_scenario_replays_identically():
    # pytest imports every test module at collection time, which registers its scenarios
    assert SCENARIOS, "no scenarios registered"
    for name, build in SCENARIOS.items():
        first = run(Engine(), build())
        second = run(Engine(), build())
        assert first == second, name
        assert first, name
