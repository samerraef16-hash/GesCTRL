# Feasibility Measurement Report (Phase 0)

> Status: **Measured 2026-10-10** on the author's laptop. Numbers come from
> `spikes/feasibility/out/*_summary.json` and `*_frames.csv`. The slow-motion video check (T028)
> was **skipped by the owner**; see section 4. Items not measured are marked `TBD`.

## 1. Reference setup

| Item | Value |
|---|---|
| CPU model / RAM / OS build | TBD (not recorded); Windows 11 Home 10.0.26200 |
| Python / mediapipe / OpenCV versions | Python 3.12.6, mediapipe 1.1.0, OpenCV 5.0.0 |
| Camera model, capture resolution / FPS | Built-in webcam (model not recorded); 640×480 at 30 FPS, MJPG, DirectShow |
| Display resolution / scaling | 1920×1080 primary, per-monitor DPI awareness |
| Lighting | Normal indoor for all runs except the dim-light run |
| Hand distance | About 40–60 cm |

## 2. Method

- **Internal per-stage timing**: capture-pickup, inference, filter, inject, total (`measure.py`, research R6.1). "Total" runs from frame capture to cursor injection. It does not include camera sensor or display delay.
- **End-to-end cross-check**: not done (T028 skipped by the owner).
- **CPU**: `psutil` process CPU sampled once per second; machine % = one-core % ÷ logical cores.
- **Frame rate**: frames ÷ time between the first and last frame timestamps. The `fps_avg` in the first-run summary files divided by elapsed time including startup and reads about 25% low; the values below are corrected from `*_frames.csv`.
- **Sessions (60 s each)**: pointing, idle hand, no hand at a 10 FPS cap, dim light, typing nearby. The two-people session was not run.

## 3. Results

| Metric | Target | Measured | Conditions | Pass/Fail |
|---|---|---|---|---|
| Hand-to-cursor delay p95 (end-to-end, video) | ≤ 80 ms | TBD (check skipped by owner) | normal light | Unverified |
| Internal pipeline delay p50 / p95 | (informational) | 24.5 ms / 32.0 ms (max 60.8 ms) | pointing, normal light | n/a |
| Internal delay, idle hand p50 / p95 | (informational) | 25.1 ms / 29.3 ms | normal light | n/a |
| Inference p50 / p95 | (informational) | 23.6 ms / 26.3 ms with a hand; 15.1 ms / 16.1 ms with no hand | normal light | n/a |
| Inject p95 | (informational) | 0.41 ms | pointing | n/a |
| Tracking rate | ≥ 25 FPS | 29.7 (pointing), 29.8 (idle hand), 30.0 (typing nearby) | normal light | Pass |
| Tracking rate, dim light | ≥ 25 FPS | **10.0** (601 frames in 60 s) | dim light | **Fail** |
| CPU, Active with hand | (informational) | 4.6% (pointing) to 5.3% (idle hand) of the machine; 74–84% of one core | 60 s avg | n/a |
| CPU, no hand at 10 FPS cap | budget set here | 1.3% of the machine (20.7% of one core); 8.1 FPS achieved | 60 s avg | n/a |
| Memory (RSS max) | (informational) | 171 MB | all runs | n/a |
| Frames with a hand | (informational) | pointing 57.8%, idle hand 100%, dim light 98.0%, typing nearby 24.3% | the hand left view in pointing and typing runs by design | n/a |
| Dropout runs (interior no-hand runs) | (sets loss window) | pointing 1/1/0/8 (lengths 1/2/3/4+); dim light 1/2/1/0; idle hand and typing 0 | see section 5 | n/a |
| Target task, absolute | (ADR 0005 evidence) | mean 3.94 s, median 2.80 s, miss rate 36.2% (30 trials) | pinch click inside a circle | n/a |
| Target task, relative | (ADR 0005 evidence) | mean 4.63 s, median 2.99 s, miss rate 57.7% (30 trials) | same | n/a |

Target task by size (mean time / miss rate; a miss is a pinch outside the target):

| Size | Absolute | Relative |
|---|---|---|
| 24 px | 5.00 s / 47.4% | 4.62 s / 63.0% |
| 48 px | 3.82 s / 33.3% | 7.11 s / 68.8% |
| 96 px | 2.99 s / 23.1% | 2.16 s / 16.7% |

The relative run includes one 39 s trial at 48 px with 16 misses, which inflates its 48 px mean.
Its median at 48 px (3.2 s) is close to the absolute median (3.3 s), but its miss rate is higher.

## 4. Gaps and mitigations

| Gap | Probable cause | Proposed mitigation | Decision |
|---|---|---|---|
| End-to-end delay (≤ 80 ms) not verified; only the internal 32 ms p95 (capture to cursor) is known | Slow-motion video check skipped | Camera sensor plus display delay typically adds tens of ms, so the end-to-end figure is probably higher than 32 ms; re-check by feel in Phase 1 and measure if the cursor feels late | **Skipped by owner on 2026-10-10 (risk accepted)** |
| Dim light: 10 FPS, below 25 | The camera lowers its own frame rate in low light to lengthen exposure; this is not a CPU limit | Document as a known limitation (the 25 FPS target applies to normal indoor light); optionally suggest a light source in the HUD or settings | Awaiting owner |
| Small-target precision: absolute mapping misses 47% of pinches on 24 px targets and takes about 5 s | Hand jitter and pinch movement at small target sizes | Design Phase 1 around targets of 48 px or larger; consider cursor slowdown near a pinch; revisit after Phase 1 | Awaiting owner |

## 5. Derived values

| Value | Rule | Result |
|---|---|---|
| Idle CPU budget (FR-015) | `_nohand_rate10` machine CPU average (1.29%), rounded UP to the nearest 5% (research R13) | **5% of total CPU** at about 10 FPS processing |
| Loss-confirmation window | Smallest N such that runs shorter than N are ≥ 95% of dropout runs; keep 3 if fewer than 20 runs (research R9) | **3 frames kept**: only 17 interior dropout runs were recorded (fewer than 20) |
| One Euro parameters | Values preferred in T029 | **min_cutoff 1.0, beta 0.007 kept**: the owner reported smooth, jitter-free pointing with the defaults and did not test other values |
| Pointer mapping | Lower miss rate wins; within 5 points the lower mean time; otherwise absolute | **Absolute** (36.2% vs 57.7% miss rate; 3.94 s vs 4.63 s mean) |

## 6. Raw data

`spikes/feasibility/out/` (git-ignored): `*_frames.csv`, `*_summary.json`, `*.jsonl`
(landmark recording of the pointing run, no images), `smoke-notes.txt`. An extra
`20261010-193502_dim-light_*` run lasted only 12 s and was repeated; it is kept but not used.
