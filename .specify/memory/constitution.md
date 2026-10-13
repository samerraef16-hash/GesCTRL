<!--
SYNC IMPACT REPORT
Version change: 1.2.0 → 1.3.0 (MINOR: the Keyboard-Mode exception widens from confirming to typing)
Modified sections: Principle I (one-primary-hand rule: Keyboard Mode confirming hand, spec 004,
  ADR 0007)
Earlier (1.0.0 → 1.1.0, MINOR): Development Workflow and Quality Gates (lean Spec Kit cycle);
  Technical Standards (portfolio repo run from source; packaging optional)
Principles II–VIII: unchanged
Templates: no edits required
Deferred TODOs: none
-->

# GesCRTL Constitution

## Core Principles

### I. Safety First: No Unintended Input (NON-NEGOTIABLE)

GesCRTL injects real OS input; a wrong click or stuck key is the worst possible failure.

- Consequential actions (clicks, drags, key presses, mode switches, system/media actions) MUST
  only be emitted when tracking confidence is above a configured threshold and the gesture has
  been stable for a minimum number of frames.
- Every gesture threshold MUST use hysteresis (separate enter/exit thresholds) and discrete
  actions MUST have cooldowns to prevent repeated triggers.
- On hand loss, camera loss, pause, mode change, shutdown, or unhandled exception, the system MUST
  release every held mouse button and key (guaranteed via `finally`/exit handlers).
- A user MUST always be able to stop gesture control instantly through at least two independent
  paths (a gesture and a global keyboard hotkey), plus a system-tray exit.
- Only one controlling hand is tracked at a time (primary-hand lock); other hands/people in frame
  MUST NOT produce input. Exception: in Keyboard Mode only, a second hand that passes the
  same-person check (ADR 0007) may point at and press keys like the primary hand (two-handed
  typing); it never moves the cursor, changes state or mode, or triggers anything but keys, and a
  hand that fails the check is ignored.

Rationale: users will only adopt an input device they trust not to act on its own.

### II. Reliability Before Breadth

- A feature MUST NOT ship unless it meets its documented acceptance criteria in the declared
  supported environments; unreliable gestures are removed or disabled, not shipped "experimental"
  by default.
- New gestures are added only when a mode or existing control cannot solve the need more simply.
- Research-heavy capabilities (learned gestures, two-handed air typing, broad cross-platform
  support) MUST NOT block or destabilize the first usable release.
- Claims about accuracy, speed, or typing performance MUST be backed by recorded measurements.

### III. Predictable, Visible State

- The application is governed by a single explicit interaction state machine
  (Inactive, Active, Paused, TrackingLost) combined with an explicit Mode
  (Pointer, Keyboard, Presentation, Media/System). Gesture recognizers emit intents only; the
  state machine alone decides whether an intent becomes an action.
- The current state and mode MUST always be visible in a compact HUD that never steals focus or
  clicks (always-on-top, click-through, non-activating).
- Tracking or camera unavailability (including camera held by another app) MUST be surfaced to
  the user within one second.
- Mode transitions MUST be deliberate (held/confirmed gesture), never triggered by a single frame.

### IV. Deterministic, Testable Core (NON-NEGOTIABLE)

- Everything downstream of hand tracking (filtering, feature extraction, gesture recognition,
  state machine, action mapping) MUST be deterministic logic: inputs are landmark frames plus an
  injected clock; outputs are events. No direct camera, OS, or wall-clock access in this core.
- Landmark sessions MUST be recordable to a replayable format (timestamped JSONL) and replayed in
  automated tests; every gesture and state transition MUST have replay-based regression tests.
- Every bug involving a misfire MUST be captured as a recorded fixture and a failing test before
  it is fixed.
- Camera-dependent behavior that cannot be automated MUST have a written, repeatable manual
  acceptance procedure.

### V. Measured Performance and Responsiveness

- Initial budgets (on a mid-range laptop CPU, single hand): end-to-end latency (frame capture →
  OS input) ≤ 80 ms at p95; tracking ≥ 25 FPS; idle CPU (no hand present) reduced via lower
  processing rate.
- Pipeline stages MUST be instrumented for per-stage latency, and a benchmark tool MUST report
  latency, FPS, CPU usage, and false-trigger rate.
- Frame queues MUST be "latest frame wins" (bounded size 1); backlog that increases latency is a
  defect.
- A change that regresses a budget beyond 10% MUST be justified in its plan or rejected.

### VI. Privacy by Design

- All video processing MUST happen on-device and in memory. Camera frames MUST NOT be written to
  disk or transmitted over any network.
- The application MUST NOT make network calls at runtime unless a future feature explicitly
  requires it, documents it, and requires user opt-in.
- Recording tools for development store landmark coordinates only, never images, unless the
  developer explicitly opts in for a local debugging session.
- Camera activity MUST be clearly indicated, and releasing the camera MUST be one action away.

### VII. Modular, Platform-Isolated Architecture

- The system is a one-directional pipeline: Capture → Tracking → Filtering → Features →
  Gesture Recognition → State Machine → Action Mapping → Output Backends (input, HUD).
- All OS-specific code (input injection, DPI handling, overlay window flags, hotkeys, tray) MUST
  live behind interfaces (e.g., `InputBackend`, `OverlayBackend`) in a `platform/` package;
  core modules MUST NOT import platform modules.
- Third-party tracking libraries MUST be wrapped by an adapter producing project-owned landmark
  types, so the tracking engine can be replaced without touching gesture logic.
- Known platform limits MUST be documented rather than hidden (e.g., Windows UIPI blocks input to
  elevated windows; secure desktop, UAC prompts, and lock screen are unreachable).

### VIII. Simplicity, Ergonomics, and Sensible Defaults

- The app MUST be usable in Pointer Mode immediately after first launch with no configuration.
- Gesture vocabulary per mode MUST stay small and be shown in the HUD for the active mode.
- Interactions MUST be designed to minimize arm fatigue: map a comfortable active region of the
  camera frame to the full screen; support a resting/clutch posture; support left- and
  right-handed use.
- All thresholds, sensitivity, and mappings MUST be configurable, persisted, validated, and
  resettable to defaults without editing source code.
- Prefer rule-based, explainable gesture logic; introduce ML models only when a demonstrated need
  exists and recorded data is available to evaluate them.

## Technical Standards and Constraints

- **Initial platform**: Windows 10/11 desktop and laptop with a standard RGB webcam. Other OSes
  are future targets enabled by Principle VII.
- **Baseline stack** (changes require an ADR): Python 3.11+; MediaPipe Hand Landmarker (Tasks
  API) for tracking; OpenCV for capture; Win32 `SendInput` for input injection (no
  `pyautogui`-style high-level automation in production paths); PySide6 for HUD, tray, and
  settings UI; Pydantic-validated settings stored under `%APPDATA%\GesCRTL`; `pytest` for tests.
  The project is a portfolio GitHub repository run from source; packaging (PyInstaller) is
  optional and not a quality gate.
- **Pointer correctness**: process MUST be per-monitor DPI aware (V2); cursor positions use
  absolute virtual-desktop coordinates. Cursor anchor is a stable hand point (palm center or
  index MCP), not a fingertip; motion is smoothed with an adaptive filter (One Euro or
  equivalent); clicks apply cursor stabilization at pinch onset.
- **Scale invariance**: gesture distances MUST be normalized by hand size so behavior is
  consistent across camera distances.
- **Architecture decisions** with lasting impact (stack, tracking engine, mapping model,
  packaging) MUST be recorded as ADRs in `docs/adr/`.
- **Code quality**: type hints on public APIs, a configured linter/formatter (e.g., Ruff), and
  structured logging; logs MUST NOT contain image data.

## Development Workflow and Quality Gates

- Work proceeds one bounded capability at a time using a lean Spec Kit cycle: specify → plan →
  tasks → implement → verify. Clarify runs only when a spec has more than 3 open questions;
  checklist and analyze are optional. A plan produces `plan.md` only (decisions recorded inline)
  unless a phase genuinely needs a separate research, data-model, contract, or quickstart file.
  Code and tests are the primary record; documents stay short. `Plan.md` is the roadmap; it is
  not a specification.
- Every spec MUST include measurable acceptance criteria (including false-trigger expectations
  for any action-producing gesture).
- Every implementation plan MUST pass a Constitution Check against Principles I–VIII; any
  deviation MUST be listed with justification in the plan's complexity/deviation section.
- A change is mergeable only when: automated tests (including landmark-replay tests) pass; lint
  and type checks pass; performance budgets are not regressed beyond the allowed margin; manual
  acceptance steps for camera-dependent behavior are completed and recorded; user-facing docs
  are updated for changed controls or limitations.
- Each phase ends with a demonstrable, testable improvement and a short retrospective noting
  lessons and any constitution amendments needed.

## Governance

- This constitution supersedes other project practices. Where `Plan.md`, specs, or plans
  conflict with it, the constitution wins until amended.
- Amendments are proposed as a change to this file with a rationale and an updated Sync Impact
  Report, and take effect when merged to `main`.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle; MINOR for
  adding a principle/section or materially expanding guidance; PATCH for clarifications and
  wording.
- Every plan and review MUST verify compliance; non-negotiable principles (I and IV) cannot be
  waived, only amended.
- Runtime development guidance lives in `Plan.md` (roadmap) and `docs/adr/` (decisions).

**Version**: 1.3.0 | **Ratified**: 2026-10-10 | **Last Amended**: 2026-10-13
