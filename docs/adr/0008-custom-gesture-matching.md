# ADR 0008: Custom gestures are matched with nearest neighbour and DTW

- **Status**: Accepted for implementation (2026-10-13). Not yet measured: whether each kind meets
  its reliability target is decided in the manual validation session (spec 004 SC-007, SC-008),
  and a kind that misses is switched off in `CUSTOM_KINDS_AVAILABLE`.
- **Date**: 2026-10-13
- **Related**: spec 004 FR-023..FR-028, plan D9, constitution Principle II

## Context
Users can record their own gesture for an allowed action. It must work from a handful of examples
(five takes, a few seconds of effort), run well inside the frame budget on a laptop CPU, store
only numbers, never override a built-in gesture, and be testable with the landmark-replay
harness. The clarify session chose both still hand shapes and movements.

## Options Considered
1. **A trained classifier** (small neural network, or an SVM, on landmark features): better with
   many examples, but five takes are too few, it adds a dependency, and the result is hard to
   reason about and to test deterministically.
2. **Nearest neighbour on a normalized descriptor for shapes, and DTW (dynamic time warping, which
   matches paths drawn at different speeds) for movements**: works from a few examples, is a few
   dozen lines of pure Python, is deterministic, and each decision can be explained to the user.
3. **MediaPipe's gesture recognizer / model customization**: a separate model to fine-tune and
   ship; it conflicts with the project's own pose layer.

## Decision
Option 2.
- **Shape descriptor**: the 20 landmarks around the wrist, divided by hand size, rotated so the
  wrist-to-middle-knuckle line points up, mirrored for a left hand: 40 numbers that do not depend on
  position, distance to the camera, turning the hand in the image, or which hand it is.
- **Shape match**: the distance to the nearest recorded sample must be under the gesture's
  threshold (1.5 times the largest spread among the five takes, at least 0.25) and clearly smaller
  than the distance to any other gesture. The raw pose must be the built-in "relaxed" pose, so a
  fist, an open palm, a pinch and so on can never match. It must hold for the stable frames and
  `custom_hold_ms` (0.6 s), then fires once; the cursor holds still while it is held.
- **Movement**: the path of the palm centre relative to its start, in hand sizes, resampled to 32
  points, plus the hand shape at the start. A movement begins above 1.0 hand sizes per second and
  ends after 150 ms below 0.4; it must last 0.25 to 2.5 s and be at least 1 hand size long. It
  matches if the DTW distance (per step, in hand sizes) to the nearest sample is under the gesture's
  threshold (1.3 times the largest spread, at least 0.2), the duration is within half to twice the
  recorded one, the start shape is close, and no other gesture fits about as well.
- **Enrollment** takes five timed takes and refuses: a take that looks like a built-in pose, a
  movement that looks like the open-hand swipe, takes that differ a lot (mean distance between takes
  above 0.8 for shapes and 0.2 hand sizes for movements), and a gesture too similar to an existing
  one.
- **Safety**: a custom gesture is ignored while a built-in gesture is in progress, needs the usual
  confidence, stable frames, and a 1.5 s cooldown, and its action comes from the allowed set, which
  excludes clicks, pause, resume, emergency stop, the mode menu and the level panel.
- **Storage**: `%APPDATA%\GesCRTL\custom_gestures.json`, numbers and names only.

## Consequences
- No new dependency; the matcher runs in the pure core and is covered by landmark-replay tests.
  Measured: about 0.3 ms p95 per frame with 10 gestures of 5 samples (`bench --matcher`), against
  a 2 ms budget.
- Movements drawn in Pointer Mode move the cursor while they are performed (accepted in the clarify
  session); the action runs once at the end.
- The thresholds are starting points. The validation session measures recognition (18 of 20) and
  false triggers (none in 10 minutes of non-control recordings) separately for shapes and
  movements, and the spread limit for movements (0.2 hand sizes) may need relaxing for real
  hands. A kind that does not meet its target is disabled and listed in the known limitations.
