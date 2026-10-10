"""Timed measurement session for the Phase 0 spike (THROWAWAY).

Writes <prefix>_frames.csv, <prefix>_summary.json and (with --record) <prefix>.jsonl
(landmark recording; numbers only, never images).
"""
import argparse
import csv
import json
import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import psutil

import spike
import winput

SCENARIOS = ["idle-hand", "pointing", "pinch-clicks", "typing-nearby", "two-people", "dim-light", "free"]


def pct(values, q):
    return float(np.percentile(values, q)) if len(values) else None


def stage_stats(values):
    return {"p50": pct(values, 50), "p95": pct(values, 95), "max": float(max(values)) if len(values) else None}


def dropout_runs(hand_flags):
    """Interior runs of no-hand frames (hand frames on both sides)."""
    runs, n, seen_hand = [], 0, False
    for has in hand_flags:
        if has:
            if seen_hand and n:
                runs.append(n)
            n, seen_hand = 0, True
        else:
            n += 1
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    spike.add_common_args(parser)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--scenario", choices=SCENARIOS, default="free")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--no-hand", action="store_true", help="label only")
    parser.add_argument("--paused-rate", type=float, default=0.0)
    args = parser.parse_args()
    if args.paused_rate > 0:
        args.max_rate = args.paused_rate
        args.no_inject = True

    print("DPI:", winput.set_dpi_awareness())
    stop = threading.Event()
    listener = spike.start_safety(stop)

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = f"{stamp}_{args.scenario}"
    if args.no_hand:
        prefix += "_nohand"
    if args.paused_rate > 0:
        prefix += f"_rate{int(args.paused_rate)}"
    prefix = str(out_dir / prefix)

    rows, hand_flags = [], []
    jsonl = open(prefix + ".jsonl", "w", encoding="utf-8") if args.record else None
    proc = psutil.Process()
    proc.cpu_percent(None)
    cpu_samples, rss_max = [], 0.0
    last_sample = time.perf_counter()
    state = {"header_written": False}

    def write_header(camera):
        header = {
            "type": "header",
            "format_version": 1,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tracker": {"name": "mediapipe-hand-landmarker", "version": _mp_version(), "running_mode": "VIDEO"},
            "camera": {"width": camera["width"], "height": camera["height"], "fps_requested": args.fps},
            "mirrored": True,
            "scenario": args.scenario,
            "notes": "presence is set to handedness_score (the Hand Landmarker does not expose per-hand presence)",
        }
        jsonl.write(json.dumps(header) + "\n")

    def on_result(r: spike.FrameResult):
        nonlocal last_sample, rss_max
        if jsonl and not state["header_written"]:
            write_header(spike.run_loop.camera_actual)
            state["header_written"] = True
        capture = (r.t_pickup_ns - r.t_capture_ns) / 1e6
        inference = (r.t_infer_ns - r.t_pickup_ns) / 1e6
        filt = (r.t_filter_ns - r.t_infer_ns) / 1e6
        inject = (r.t_inject_ns - r.t_filter_ns) / 1e6 if r.t_inject_ns else 0.0
        total = ((r.t_inject_ns or r.t_filter_ns) - r.t_capture_ns) / 1e6
        rows.append((r.seq, r.t_capture_ns, len(r.hands), capture, inference, filt, inject, total))
        hand_flags.append(bool(r.hands))
        if jsonl:
            frame = {
                "type": "frame",
                "t_ns": r.t_capture_ns,
                "hands": [
                    {
                        "handedness": h.handedness,
                        "handedness_score": round(h.handedness_score, 5),
                        "presence": round(h.handedness_score, 5),
                        "landmarks": [[round(c, 5) for c in p] for p in h.landmarks],
                        **(
                            {"world_landmarks": [[round(c, 5) for c in p] for p in h.world_landmarks]}
                            if h.world_landmarks
                            else {}
                        ),
                    }
                    for h in r.hands
                ],
                "timing_ms": {
                    "capture": round(capture, 3),
                    "inference": round(inference, 3),
                    "filter": round(filt, 3),
                    "inject": round(inject, 3),
                },
            }
            jsonl.write(json.dumps(frame) + "\n")
        now = time.perf_counter()
        if now - last_sample >= 1.0:
            cpu_samples.append(proc.cpu_percent(None))
            rss_max = max(rss_max, proc.memory_info().rss / 1e6)
            last_sample = now

    t0 = time.perf_counter()
    try:
        spike.run_loop(args, on_result, args.duration, stop)
    finally:
        listener.stop()
        if jsonl:
            jsonl.close()
    elapsed = time.perf_counter() - t0

    with open(prefix + "_frames.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "t_capture_ns", "n_hands", "capture_ms", "inference_ms", "filter_ms", "inject_ms", "total_ms"])
        w.writerows(rows)

    cols = list(zip(*rows)) if rows else [[]] * 8
    runs = dropout_runs(hand_flags)
    buckets = {"1": 0, "2": 0, "3": 0, "4+": 0}
    for n in runs:
        buckets[str(n) if n < 4 else "4+"] += 1
    cores = psutil.cpu_count(logical=True) or 1
    one_core = float(np.mean(cpu_samples)) if cpu_samples else None
    summary = {
        "scenario": args.scenario,
        "duration_s": elapsed,
        "frames_processed": len(rows),
        # Frame timestamps, so camera/model startup is not counted (elapsed includes it)
        "fps_avg": ((len(rows) - 1) / ((rows[-1][1] - rows[0][1]) / 1e9)) if len(rows) > 1 else None,
        "stage_ms": {
            "capture": stage_stats(cols[3]),
            "inference": stage_stats(cols[4]),
            "filter": stage_stats(cols[5]),
            "inject": stage_stats(cols[6]),
            "total": stage_stats(cols[7]),
        },
        "cpu_percent_one_core_avg": one_core,
        "cpu_percent_machine_avg": (one_core / cores) if one_core is not None else None,
        "rss_mb_max": rss_max,
        "frames_with_hand_pct": (100.0 * sum(hand_flags) / len(hand_flags)) if hand_flags else None,
        "dropout_runs": buckets,
        "single_frame_drop_fraction": (buckets["1"] / len(runs)) if runs else None,
        "env": {
            "python": platform.python_version(),
            "mediapipe": _mp_version(),
            "cv2": cv2.__version__,
            "camera": getattr(spike.run_loop, "camera_actual", None),
            "primary_screen_rect": winput.primary_screen_rect(),
            "dpi_mode": winput.set_dpi_awareness(),
        },
    }
    with open(prefix + "_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary: {prefix}_summary.json")
    print(
        f"frames={summary['frames_processed']} fps={summary['fps_avg']:.1f} "
        f"total_p95={summary['stage_ms']['total']['p95']} cpu_machine={summary['cpu_percent_machine_avg']}"
    )


def _mp_version() -> str:
    import mediapipe

    return mediapipe.__version__


if __name__ == "__main__":
    main()
