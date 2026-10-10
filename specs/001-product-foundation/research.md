# Research: Product Foundation and Interaction Model (Phase 0)

These are **provisional decisions**. Each must be confirmed or overturned with spike evidence and
recorded as an ADR (FR-014). Every item that had no answer when planning started is resolved
below.

---

## R1. Hand-tracking approach → ADR 0001

- **Decision**: MediaPipe **Hand Landmarker** via the **Tasks API** (`mediapipe.tasks.vision`),
  `VIDEO` running mode (synchronous, one result per frame), `num_hands=2`. Two hands are
  detected so the primary-hand lock can be exercised; only the primary hand is used.
- **Rationale**: It gives 21 3D landmarks plus handedness and confidence scores per hand. It runs
  in real time on a laptop CPU, works offline, and is actively maintained. `VIDEO` mode makes
  per-frame latency easy to measure (no callback reordering). `LIVE_STREAM` can be compared in
  the spike.
- **Alternatives considered**:
  - Legacy `mp.solutions.hands`: deprecated path, not a long-term base.
  - MediaPipe Gesture Recognizer: adds canned gesture labels, but its gesture set doesn't match
    ours and it hides thresholds. Rule-based logic on landmarks is more controllable
    (Constitution VIII).
  - OpenCV skin or contour detection: fragile under lighting and skin-tone variation.
  - Other ONNX hand-pose models: possible future swap behind the tracking adapter, but more
    integration work now.
- **Spike evidence to collect**: FPS, per-frame inference time, and detection dropout rate under
  normal and dim lighting; `VIDEO` vs `LIVE_STREAM` latency.

## R2. Method of sending input → ADR 0002

- **Decision**: Win32 **`SendInput`** via `ctypes`, using `MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE |
  MOUSEEVENTF_VIRTUALDESK` with coordinates normalized to 0–65535. Call
  `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` at startup.
- **Rationale**: It is the supported, lowest-level user-mode API. It is fast, it does absolute
  virtual-desktop positioning, and it later supports buttons, high-resolution wheel, and keys
  with explicit up/down events (needed for release-all safety). No extra dependency.
- **Alternatives considered**:
  - `pyautogui`: adds a default 0.1 s pause per call and has a corner fail-safe that conflicts
    with our own safety model.
  - `pynput`: workable, but adds a dependency and abstracts the details we need to control.
  - `mouse_event`: superseded by `SendInput`.
- **Known limits (feed `known-limitations.md`)**:
  - UIPI blocks injection into elevated windows unless GesCRTL is elevated or has `uiAccess`
    (which needs a signed binary installed in Program Files).
  - The secure desktop (UAC prompts, lock screen, Ctrl+Alt+Del) is unreachable.

## R3. On-screen indicator (HUD) approach → ADR 0003

- **Decision**: **PySide6 (Qt)**: a frameless, always-on-top tool window with Win32 extended
  styles `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`, plus
  `QSystemTrayIcon` for the tray menu.
- **Rationale**: It meets FR-011 (never takes focus, never blocks clicks). Qt also provides the
  tray, the later settings UI, and the mode menu overlay from one toolkit. It is cross-platform
  for later phases.
- **Alternatives considered**:
  - Tkinter: weak support for transparency and click-through.
  - Raw Win32 layered window: maximum control, but high effort and no reusable UI for settings.
  - Electron or web overlay: heavy runtime and extra latency.
- **Spike evidence**: Optional in Phase 0. A minimal click-through window can be checked with
  the quickstart steps. Full HUD work is Phase 1.

## R4. Packaging approach → ADR 0004

- **Decision**: **PyInstaller, one-folder (`--onedir`) build** for early releases. Revisit Nuitka
  if startup time or size is unacceptable.
- **Rationale**: It is the most common way to ship Python desktop apps, handles PySide6 and data
  files (the `.task` model), and the one-folder build avoids the per-launch extraction delay of
  `--onefile`.
- **Alternatives considered**:
  - Nuitka: faster startup and harder to reverse engineer, but longer builds and more MediaPipe
    packaging friction.
  - MSIX: good install experience, but signing overhead. Consider at release time (Phase 10).
  - Plain `pip install`: not acceptable for non-developer users.
- **Spike evidence**: A trial build of the spike, recording build success, folder size, and cold
  start time.

## R5. Pointer mapping model → ADR 0005

- **Decision (hypothesis to test)**: **Absolute active-region mapping** as the default. A
  comfortable rectangle (start: the central ~60% × 60% of the mirrored camera frame, adjustable)
  maps linearly onto the primary monitor. **Relative + clutch** is implemented in the spike as
  the comparison.
- **Rationale**: With absolute mapping the same hand position always means the same screen
  position. It needs no clutch for repositioning, so the gesture count is lower and it is easier
  to learn. Relative mapping with acceleration may give better precision on large screens but
  requires frequent clutching.
- **Alternatives considered**: Relative with mouse-like acceleration; hybrid (absolute coarse +
  relative fine near a target). The hybrid is deferred unless spike data shows absolute mapping
  is too imprecise.
- **Spike evidence**: `target_task.py` shows targets of 3 sizes (small ≈ 24 px, medium ≈ 48 px,
  large ≈ 96 px) at random positions. It records time-to-target and miss rate for both models,
  over 30 trials per model.

## R6. Measuring hand-to-cursor delay

- **Decision**: Use two complementary methods.
  1. **Internal pipeline timing** (every frame): timestamps at frame-read-return →
     inference-done → filter-done → `SendInput`-return, using `time.perf_counter_ns()`. This
     reports per-stage and total p50/p95.
  2. **External end-to-end check** (≥ 10 trials): a phone slow-motion video (≥ 240 FPS) filming
     both the hand and the screen. Count frames from hand-motion onset to cursor-motion onset.
     This captures camera exposure/buffer and display latency, which internal timing can't see.
- **Rationale**: Internal timing alone under-reports, because camera capture and display add
  latency. The video check calibrates the gap so the 80 ms target is judged on true end-to-end
  delay.
- **Alternatives considered**: A photodiode/LED rig, which is more precise but needs hardware;
  internal timing only, rejected as misleading.

## R7. Smoothing

- **Decision**: **One Euro filter** on the cursor anchor point. Starting parameters:
  `min_cutoff = 1.0 Hz`, `beta = 0.007`, `d_cutoff = 1.0 Hz`, tuned in the spike. Record the final
  values in ADR 0005.
- **Rationale**: Adaptive: strong smoothing when still (no jitter) and light smoothing when moving
  fast (low lag). It is the standard choice for interactive pointing.
- **Alternatives**: Exponential moving average (one fixed tradeoff between lag and jitter); Kalman
  filter (more tuning, little benefit for this purpose).

## R8. Cursor anchor point

- **Decision**: The **palm center** (mean of the wrist and the index/middle/ring/pinky MCP
  landmarks: 0, 5, 9, 13, 17) drives the cursor.
- **Rationale**: Pinching moves the fingertips but barely moves the palm center, so clicks don't
  drag the cursor. This complements click stabilization.
- **Alternatives**: Index fingertip (most intuitive, but jumps during pinch); index MCP (good
  second choice; compare in the spike).

## R9. Confirming tracking loss (required by clarification Q4)

- **Decision**: **Tracking Lost** is declared when the primary hand is missing or below confidence
  for a **loss-confirmation window** (start: 3 consecutive frames ≈ 100 ms at 30 FPS). Held input
  is then released immediately, with no extra grace period.
- **Rationale**: Webcam trackers drop single frames regularly. Without a confirmation window,
  every one-frame flicker would end a drag. This is detection debouncing, not a grace period, so
  it respects the clarified "release immediately on loss" rule.
- **Spike evidence**: Distribution of dropout run-lengths during continuous tracking. Choose the
  smallest window that filters ≥ 95% of spurious single-frame drops.

## R10. First-release gesture vocabulary (budget ≤ 8)

- **Decision**: Use 7 hand forms. Meaning depends on state and mode:

| # | Hand form | Scope | Meaning |
|---|---|---|---|
| 1 | Relaxed hand (neutral) | Pointer | Move cursor (palm-center anchor) |
| 2 | Thumb–index pinch | Pointer (+ mode menu) | Tap = left click; two taps within the OS double-click time = double click; hold > 300 ms = drag; in the mode menu = confirm |
| 3 | Thumb–middle pinch | Pointer | Right click |
| 4 | Index + middle extended together | Pointer | Vertical scroll by hand motion |
| 5 | Closed fist | Global | Held < 1.5 s = clutch (cursor frozen, no actions); held ≥ 1.5 s = **Pause**, which is also the gesture form of the **emergency stop** (releases all input) |
| 6 | Open palm facing camera, held ≥ 1 s | Global, Paused only | **Resume** |
| 7 | Three fingers extended (index, middle, ring), held ≥ 0.8 s | Global, Active only | Open the **mode menu** |

- **Turn off (Inactive)**: keyboard shortcut or tray only, with no gesture. That keeps the budget
  and avoids turning the camera off by accident.
- **Rationale**:
  - Merging clutch with pause (by hold duration) and emergency stop with pause (same target state
    after clarification Q5) keeps the count at 7.
  - Open palm only means "resume" while Paused, so it doesn't conflict with the relaxed pointer
    hand.
  - Every form is symmetric, so either hand works (FR-010).
- **Alternatives**:
  - A dedicated emergency-stop gesture: redundant, since it has the same target state as pause.
  - A thumbs-up for resume: more easily triggered by accident while gesturing in conversation.

## R11. Primary-hand selection

- **Decision**:
  - The hand that performs the resume gesture becomes primary.
  - While Active, primary identity is kept by nearest-wrist-position continuity between frames.
  - On automatic resume from Tracking Lost, accept a single hand that appears within the active
    region. If several appear, choose the one nearest the last known primary position.
  - Non-primary hands never produce input.
- **Rationale**: Handedness labels can flip between frames. Position continuity is more stable and
  works for left- and right-handed users.

## R12. Reference hardware and environment

- **Decision**: The project owner's Windows laptop and its built-in webcam, under normal indoor
  lighting (overhead room light, no strong backlight), at a 40–70 cm hand distance. The report
  records CPU model, RAM, OS build, camera resolution/FPS, display resolution, and scaling.
- **Additional condition**: one dim-lighting session, reported but not used for pass/fail.

## R13. Idle CPU budget method (FR-015)

- **Decision**:
  - Measure CPU % (process, averaged over 60 s) in three conditions: Active with a hand, Active
    with no hand, and Paused.
  - Set the idle budget to the measured no-hand value at the reduced processing rate (start at
    10 FPS while Paused or no hand), rounded up to the nearest 5%.
  - Record the result in the report and update `Plan.md` §6.

---

All earlier open technical questions (language version, dependencies, testing approach, target
platform, latency method, mapping model) are resolved above. No open questions remain.
