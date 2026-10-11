from gescrtl.stats import FrameTiming, StageStats


def timing(t_ms: float, total_ms: float) -> FrameTiming:
    return FrameTiming(
        t_capture_ns=int(t_ms * 1e6),
        wait_ns=int(total_ms * 0.1e6),
        track_ns=int(total_ms * 0.7e6),
        engine_ns=int(total_ms * 0.1e6),
        input_ns=int(total_ms * 0.1e6),
    )


def test_empty_summary():
    assert StageStats().summary() == {"frames": 0}


def test_fps_and_percentiles():
    s = StageStats()
    for i in range(101):  # 30 FPS cadence, delay 10..110 ms
        s.record(timing(i * 1000 / 30, 10 + i))
    out = s.summary()
    assert abs(out["fps"] - 30.0) < 0.1
    assert 55 < out["delay_p50_ms"] < 65
    assert 100 < out["delay_p95_ms"] <= 110


def test_ring_buffer_keeps_only_recent_samples():
    s = StageStats(size=10)
    for i in range(50):
        s.record(timing(i * 33.0, 20))
    assert s.summary()["frames"] == 10
