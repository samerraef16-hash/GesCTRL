"""Every fixture with a ``NAME.expect.json`` sidecar must not produce its forbidden events."""

import json
from pathlib import Path

import pytest

from gescrtl.recording import jsonl
from gescrtl.replay import replay

FIXTURES = Path(__file__).parent.parent / "fixtures"
CASES = sorted(FIXTURES.glob("*.expect.json"))


@pytest.mark.parametrize("sidecar", CASES, ids=lambda p: p.name.removesuffix(".expect.json"))
def test_fixture_has_no_forbidden_events(sidecar: Path):
    forbidden = set(json.loads(sidecar.read_text(encoding="utf-8"))["forbidden"])
    recording = sidecar.with_name(sidecar.name.removesuffix(".expect.json") + ".jsonl")
    events = replay(jsonl.read(recording), resume=True)
    bad = [type(e).__name__ for _, e in events if type(e).__name__ in forbidden]
    assert not bad, f"{recording.name}: {sorted(set(bad))} appeared {len(bad)} times"


def test_there_is_at_least_one_regression_fixture():
    assert CASES
