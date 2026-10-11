"""US5: the replay CLI is deterministic and needs no camera, Qt or OS input (FR-029)."""

import subprocess
import sys
from pathlib import Path

from support.hands import Script, resume_script
from support.registry import scenario

from gescrtl.core.types import Command, Pose
from gescrtl.recording import jsonl
from gescrtl.replay import main, replay, slice_items

FIXTURE = Path(__file__).parent.parent / "fixtures" / "phase0_pointing_head.jsonl"


def make_session(path: Path) -> Path:
    s = resume_script().hold(Pose.G1_RELAXED, 400, at=(0.45, 0.45))
    s.hold(Pose.G2_PINCH_INDEX, 150).hold(Pose.G1_RELAXED, 300)
    s.hold(Pose.G2_PINCH_INDEX, 450).hold(Pose.G1_RELAXED, 300)
    s.hold(Pose.G4_THUMBS_UP, 500).ramp_tilt(Pose.G4_THUMBS_UP, 35, 200).hold(
        Pose.G4_THUMBS_UP, 400
    )
    s.hold(Pose.G1_RELAXED, 200).none(8).hold(Pose.G1_RELAXED, 300).cmd(Command.PAUSE)
    with jsonl.RecordingWriter(path) as w:
        for it in s.frames():
            if hasattr(it, "cmd"):
                w.command(it.t_ns, it.cmd, it.arg)
            else:
                w.frame(it)
    return path


@scenario("recorded_session")
def recorded():
    s: Script = resume_script().hold(Pose.G1_RELAXED, 300)
    return s.frames()


def test_replaying_twice_prints_the_same(tmp_path, capsys):
    path = make_session(tmp_path / "session.jsonl")
    assert main([str(path)]) == 0
    first = capsys.readouterr().out
    assert main([str(path)]) == 0
    second = capsys.readouterr().out
    assert first == second
    for name in ("Click:", "ButtonDown:", "ButtonUp", "Scroll:", "ReleaseAll:"):
        assert name in first, name


def test_recording_round_trips_to_identical_events(tmp_path):
    path = make_session(tmp_path / "session.jsonl")
    again = tmp_path / "again.jsonl"
    with jsonl.RecordingWriter(again) as w:
        for it in jsonl.read(path):
            if hasattr(it, "cmd"):
                w.command(it.t_ns, it.cmd, it.arg)
            else:
                w.frame(it)
    assert replay(jsonl.read(path)) == replay(jsonl.read(again))


def test_slice_writes_a_resumed_fixture(tmp_path, capsys):
    path = make_session(tmp_path / "session.jsonl")
    out = tmp_path / "cut.jsonl"
    assert main([str(path), "--slice", "1500", "2500", "--out", str(out)]) == 0
    items = list(jsonl.read(out))
    assert getattr(items[0], "cmd", None) is Command.RESUME
    assert len(items) < len(list(jsonl.read(path)))
    assert slice_items([], 0, 1) == []


def test_unknown_setting_is_rejected(tmp_path):
    path = make_session(tmp_path / "session.jsonl")
    cfg = tmp_path / "s.json"
    cfg.write_text('{"nonsense": 1}')
    try:
        main([str(path), "--settings", str(cfg)])
    except ValueError as exc:
        assert "nonsense" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_replay_imports_no_camera_qt_or_platform_code():
    code = (
        "import sys, gescrtl.replay\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('cv2', 'PySide6', 'mediapipe') "
        "or m.startswith('gescrtl.platform') or m.startswith('gescrtl.tracking')]\n"
        "print(bad)\n"
        "sys.exit(1 if bad else 0)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_phase0_fixture_replays():
    assert replay(jsonl.read(FIXTURE), resume=True)
