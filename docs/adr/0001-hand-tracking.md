# ADR 0001: Hand tracking approach

- **Status**: Accepted (≥ 25 FPS in normal light measured 2026-10-10); dim-light gap noted below
- **Date**: 2026-10-10
- **Related**: spec FR-014, research R1

## Context
GesCRTL needs real-time hand landmarks from a standard webcam, offline, on a laptop CPU, with
confidence scores so unsafe actions can be gated (constitution Principles I and V).

## Options Considered
1. **MediaPipe Hand Landmarker (Tasks API), VIDEO mode**: 21 3D landmarks, handedness and confidence; runs in real time on CPU; offline; maintained. Needs a Python version with a wheel.
2. **Legacy `mp.solutions.hands`**: same model family, but a deprecated path.
3. **MediaPipe Gesture Recognizer**: adds canned labels, but its gesture set does not match ours and it hides thresholds.
4. **OpenCV skin/contour detection**: fragile under lighting and skin-tone variation.
5. **Other ONNX hand-pose models**: possible later swap behind the tracking adapter; more integration work now.

## Decision
Use MediaPipe Hand Landmarker (Tasks API) in VIDEO mode with `num_hands=2`; only the primary hand is used.

## Evidence
From `docs/measurements/feasibility-report.md` (author's laptop, 640×480 camera):
- Tracking rate 29.7–30.0 FPS in normal light (target ≥ 25): pass.
- Inference p50 / p95: 23.6 / 26.3 ms with a hand in view.
- Hand held in view for 60 s: 100% of frames had a hand and there were no dropouts.
- Dim light: the camera itself fell to 10.0 FPS (not a tracking limit); 98% of frames still had a hand. Owner decision pending (report section 4).

## Consequences
Enables rule-based gesture logic on landmarks. Ties the Phase 1 tracking adapter to MediaPipe's
landmark order, behind project-owned types so the engine can be replaced. Revisit if FPS < 25 or
dropout under normal light is high.
