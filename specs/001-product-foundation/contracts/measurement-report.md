# Contract: Feasibility Measurement Report

Output: `docs/measurements/feasibility-report.md` (FR-013, FR-015). Required sections:

1. **Reference setup**: CPU model, RAM, OS build, Python and tracker versions, camera model, and
   capture resolution/FPS. Display resolution and scaling. Lighting description. Hand distance.
2. **Method**: Internal per-stage timing (research R6.1), slow-motion video cross-check (R6.2),
   CPU sampling method, session lengths.
3. **Results table**:

| Metric | Target | Measured | Conditions | Pass/Fail |
|---|---|---|---|---|
| Hand-to-cursor delay p95 (end-to-end, video) | ≤ 80 ms | … | normal light | … |
| Internal pipeline delay p50 / p95 | (informational) | … | … | n/a |
| Tracking rate | ≥ 25 FPS | … | normal light | … |
| CPU, Active with hand | (informational) | … % | 60 s avg | n/a |
| CPU, no hand / Paused at reduced rate | budget set here | … % | 60 s avg | n/a |
| Single-frame dropout rate and run-length distribution | (sets loss window) | … | … | n/a |
| Target task: time and miss rate, absolute vs relative | (ADR 0005 evidence) | … | 30 trials each | n/a |
| Dim-light tracking rate and dropout | (informational) | … | dim light | n/a |

4. **Gaps and mitigations**: For each failed target, give the gap, the probable cause, the
   proposed mitigation or revised target, and the owner's decision (required before Phase 0
   closes).
5. **Derived values**: Idle CPU budget (FR-015), loss-confirmation window (R9), and tuned One Euro
   parameters (R7).
6. **Raw data pointer**: Location of CSV/JSONL files (git-ignored), and the summary script used.
