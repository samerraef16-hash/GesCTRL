from support.hands import Script

from gescrtl.core.types import Pose
from gescrtl.recording import jsonl
from gescrtl.stats import FrameTiming, StageStats
from gescrtl.tools import bench
from gescrtl.tools.bench import ReplayRow, replay_table, run_replay


def record(path, scenario, build):
    s = build(Script().hold(Pose.G1_RELAXED, 1500))
    with jsonl.RecordingWriter(path, scenario=scenario) as w:
        for it in s.frames():
            if hasattr(it, "cmd"):
                w.command(it.t_ns, it.cmd, it.arg)
            else:
                w.frame(it)


def tap(s):
    return s.hold(Pose.G2_PINCH_INDEX, 150).hold(Pose.G1_RELAXED, 300)


def test_quiet_scenario_with_no_events_passes(tmp_path, capsys):
    record(tmp_path / "a_idle.jsonl", "idle", lambda s: s.hold(Pose.G1_RELAXED, 3000))
    assert run_replay(str(tmp_path / "*.jsonl")) == 0
    out = capsys.readouterr().out
    assert "| idle |" in out and "ok" in out


def test_quiet_scenario_with_a_click_fails_the_run(tmp_path, capsys):
    record(tmp_path / "b_typing.jsonl", "typing", tap)
    assert run_replay(str(tmp_path / "*.jsonl")) == 1
    assert "FAIL" in capsys.readouterr().out


def test_other_scenarios_are_reported_but_never_fail(tmp_path, capsys):
    record(tmp_path / "c_clicking.jsonl", "clicking", tap)
    assert run_replay(str(tmp_path / "*.jsonl")) == 0
    assert "| clicking |" in capsys.readouterr().out


def test_no_matching_files_is_an_error(tmp_path):
    assert run_replay(str(tmp_path / "*.jsonl")) == 2


def test_rate_per_minute_and_table_header():
    row = ReplayRow("f", "idle", 30.0, 1, 0, 0, 1)
    assert row.per_minute == 4.0 and row.must_be_quiet
    assert replay_table([row]).splitlines()[0].startswith("| file | scenario")


def test_null_input_counts_and_sends_nothing():
    n = bench.NullInput()
    n.move(0.1, 0.2)
    n.click("left")
    assert n.counts == {"move": 1, "click": 1}


def test_stats_reset_and_live_table():
    st = StageStats()
    st.record(FrameTiming(0, 0, 1, 1, 1))
    st.record(FrameTiming(10**8, 0, 1, 1, 1))
    assert st.summary()["frames"] == 2
    st.reset()
    assert st.summary() == {"frames": 0}
    assert "| Active | 5 |" in bench.live_table("Active", 5, {"frames": 3}, 1.5)
