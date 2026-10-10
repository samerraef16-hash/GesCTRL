"""In-window target-acquisition task for the Phase 0 spike (THROWAWAY).

Compares absolute vs relative pointer mapping. Sends NO operating-system input: the "cursor" is a
dot drawn in this window, and pinches are detected only inside this task.
"""
import argparse
import csv
import json
import random
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from mapping import AbsoluteMapper, RelativeMapper
from one_euro import OneEuro2D
from tracking import (
    HandTracker,
    LatestFrameGrabber,
    PrimaryHandSelector,
    is_fist,
    palm_center,
    pinch_ratio,
)
from winput import primary_screen_rect, set_dpi_awareness

SIZES = [24, 48, 96]
WINDOW = "GesCRTL target task"


def new_target(rng, width, height, size):
    margin = 100
    return (rng.randint(margin, width - margin), rng.randint(margin, height - margin), size)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapping", choices=["absolute", "relative"], default="absolute")
    p.add_argument("--trials", type=int, default=30)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--region", type=float, default=0.6)
    p.add_argument("--gain", type=float, default=2.5)
    p.add_argument("--min-cutoff", type=float, default=1.0)
    p.add_argument("--beta", type=float, default=0.007)
    p.add_argument("--d-cutoff", type=float, default=1.0)
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--model", default="models/hand_landmarker.task")
    args = p.parse_args()

    set_dpi_awareness()
    left, top, width, height = primary_screen_rect()
    rect = (0, 0, width, height)
    rng = random.Random(args.seed)
    mapper = AbsoluteMapper(rect, args.region) if args.mapping == "absolute" else RelativeMapper(rect, args.gain)
    smoother = OneEuro2D(args.min_cutoff, args.beta, args.d_cutoff)
    selector = PrimaryHandSelector()

    grabber = LatestFrameGrabber(args.camera)
    grabber.start()
    tracker = HandTracker(args.model)

    cv2.namedWindow(WINDOW, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    cursor = (width // 2, height // 2)
    pinching = False
    trial = 0
    misses = 0
    results = []
    target = new_target(rng, width, height, SIZES[0])
    t_target = time.perf_counter()
    seq = 0
    try:
        while trial < args.trials:
            item = grabber.latest(seq)
            if item is not None:
                seq, frame, t_ns = item
                primary = selector.select(tracker.detect(frame, t_ns))
                if primary is not None:
                    lms = primary.landmarks
                    clutched = is_fist(lms)
                    sx, sy = smoother(*palm_center(lms), t_ns / 1e9)
                    if args.mapping == "absolute":
                        if not clutched:
                            cursor = mapper.map(sx, sy)
                    else:
                        pos = mapper.map(sx, sy, clutched, cursor)
                        if pos is not None:
                            cursor = pos
                    ratio = pinch_ratio(lms)
                    was = pinching
                    if not pinching and ratio < 0.25:
                        pinching = True
                    elif pinching and ratio > 0.35:
                        pinching = False
                    if pinching and not was:
                        tx, ty, size = target
                        if (cursor[0] - tx) ** 2 + (cursor[1] - ty) ** 2 <= (size / 2) ** 2:
                            results.append((trial, size, (time.perf_counter() - t_target) * 1000, misses))
                            trial += 1
                            misses = 0
                            if trial < args.trials:
                                target = new_target(rng, width, height, SIZES[trial % 3])
                                t_target = time.perf_counter()
                        else:
                            misses += 1
            canvas = np.zeros((height, width, 3), dtype=np.uint8)
            tx, ty, size = target
            cv2.circle(canvas, (tx, ty), size // 2, (0, 200, 0), -1)
            cv2.circle(canvas, cursor, 8, (255, 255, 255), -1)
            cv2.putText(canvas, f"Trial {trial + 1}/{args.trials}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(canvas, "Pinch on the green circle - Esc to quit", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
            cv2.imshow(WINDOW, canvas)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cv2.destroyAllWindows()
        grabber.stop()
        tracker.close()

    out = Path("out")
    out.mkdir(exist_ok=True)
    prefix = str(out / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_target_{args.mapping}")
    with open(prefix + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trial", "size_px", "time_ms", "misses"])
        w.writerows(results)

    def stats(rows):
        times = [r[2] for r in rows]
        miss = sum(r[3] for r in rows)
        return {
            "n": len(rows),
            "mean_time_ms": float(np.mean(times)) if times else None,
            "median_time_ms": float(np.median(times)) if times else None,
            "miss_rate": miss / (miss + len(rows)) if rows or miss else None,
        }

    summary = {"mapping": args.mapping, "overall": stats(results)}
    for s in SIZES:
        summary[str(s)] = stats([r for r in results if r[1] == s])
    with open(prefix + "_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("Summary:", prefix + "_summary.json")
    print(json.dumps(summary["overall"]))


if __name__ == "__main__":
    main()
