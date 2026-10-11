from pathlib import Path

from support.hands import T0_NS, pose

from gescrtl.core.types import Command, CommandRecord, HandFrame, Pose
from gescrtl.recording import jsonl

FIXTURE = Path(__file__).parent.parent / "fixtures" / "phase0_pointing_head.jsonl"


def test_round_trip(tmp_path):
    p = tmp_path / "s.jsonl"
    f1 = HandFrame(T0_NS, (pose(Pose.G1_RELAXED, (0.4, 0.4)),))
    f2 = HandFrame(T0_NS + 33_000_000, ())
    with jsonl.RecordingWriter(p, scenario="unit") as w:
        w.frame(f1)
        w.command(T0_NS + 1, Command.EMERGENCY_STOP, "x")
        w.frame(f2)
    items = list(jsonl.read(p))
    assert len(items) == 3
    assert items[1] == CommandRecord(T0_NS + 1, Command.EMERGENCY_STOP, "x")
    assert items[2] == f2
    got = items[0]
    assert isinstance(got, HandFrame) and len(got.hands) == 1
    for a, b in zip(got.hands[0].landmarks, f1.hands[0].landmarks, strict=True):
        assert abs(a.x - b.x) < 1e-4 and abs(a.y - b.y) < 1e-4
    assert jsonl.read_header(p)["scenario"] == "unit"
    assert jsonl.read_header(p)["format_version"] == 2


def test_reads_phase0_v1_recording():
    header = jsonl.read_header(FIXTURE)
    assert header["format_version"] == 1
    frames = [i for i in jsonl.read(FIXTURE) if isinstance(i, HandFrame)]
    assert len(frames) >= 40
    assert all(len(h.landmarks) == 21 for f in frames for h in f.hands)
    assert frames[0].aspect == 640 / 480


def test_no_image_fields_are_written(tmp_path):
    p = tmp_path / "s.jsonl"
    with jsonl.RecordingWriter(p) as w:
        w.frame(HandFrame(1, (pose(Pose.G1_RELAXED),)))
    text = p.read_text(encoding="utf-8")
    assert "image" not in text and "jpg" not in text and "png" not in text
