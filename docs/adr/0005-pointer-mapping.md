# ADR 0005: Pointer mapping model (with smoothing and anchor point)

- **Status**: Accepted (absolute mapping; measured 2026-10-10)
- **Date**: 2026-10-10
- **Related**: spec FR-014, research R5, R7, R8

## Context
The cursor must reach every part of the screen from a comfortable hand position, with low jitter
and without moving when the user pinches.

## Options Considered
1. **Absolute active-region mapping**: the same hand position always means the same screen position; no clutch needed to reposition; lower gesture count. Hypothesis: default.
2. **Relative movement with clutch and gain**: may give better precision on large screens but needs frequent clutching.
3. **Hybrid** (coarse absolute plus fine relative near a target): deferred unless absolute proves too imprecise.

Supporting choices:
- **Anchor point**: palm center (mean of landmarks 0, 5, 9, 13, 17); pinching barely moves it. Index MCP is the fallback.
- **Smoothing**: One Euro filter, start `min_cutoff = 1.0`, `beta = 0.007`, `d_cutoff = 1.0`.

## Decision
Tie-break rule from the task list: choose the mapping with the lower overall miss rate; if within
5 percentage points, the lower mean time; if still tied, absolute.

Result: **absolute mapping**. Overall miss rate 36.2% vs 57.7% (more than 5 points apart), and
mean time 3.94 s vs 4.63 s.

Final values: region 0.6, One Euro min_cutoff 1.0 / beta 0.007 / d_cutoff 1.0, anchor point palm
center. Gain (2.5) applies only to the relative mapping and is not used. The owner found pointing
smooth and jitter-free with these values and tried no alternatives.

## Evidence
Target task, 30 trials each (a miss is a pinch outside the target). Mean time / miss rate:

| Size | Absolute | Relative |
|---|---|---|
| 24 px | 5.00 s / 47.4% | 4.62 s / 63.0% |
| 48 px | 3.82 s / 33.3% | 7.11 s / 68.8% |
| 96 px | 2.99 s / 23.1% | 2.16 s / 16.7% |
| Overall | 3.94 s / 36.2% | 4.63 s / 57.7% |

Relative's 48 px mean includes one 39 s trial with 16 misses. Relative is slightly better only at
96 px. Source: `docs/measurements/feasibility-report.md`.

## Consequences
Determines the Phase 1 cursor logic and the settings exposed for sensitivity.

The revisit condition has been met: the absolute miss rate on 24 px targets is 47%. Phase 1 must
plan for this (targets of 48 px or larger, or help for small targets) rather than assume precise
pointing. The hybrid option (coarse absolute plus fine relative) stays available for a later phase.
