# Tasks: Pointer Mode MVP + Reliability Hardening (Phases 1–2)

**Input**: `specs/002-pointer-mode-mvp/plan.md` (decisions D1–D19, hardening H1–H6), `spec.md`

**Tests**: Required. The constitution (Principle IV) and FR-030 require replay tests. Write each story's tests first and make sure they fail before you implement.

**Format**: `- [ ] T### [P?] [US?] What, where — done when`.

Conventions:
- "Dn" refers to a decision in plan.md. Read that decision before starting the task.
- Core code (`src/gescrtl/core/`) MUST NOT import cv2, mediapipe, PySide6, ctypes, or `time`.
- Never import from `spikes/`.

---

## Phase 1: Setup

- [X] T001 Create `pyproject.toml`:
  - src layout, package `gescrtl`, Python `>=3.12`.
  - Dependencies: mediapipe, opencv-python, PySide6, pydantic>=2, psutil.
  - `[dev]` extra: pytest, ruff, mypy.
  - Ruff config (line length 100) and mypy strict for `gescrtl.core`.
  - pytest `testpaths=["tests"]`.
  - Done when: `pip install -e ".[dev]"` succeeds.
- [X] T002 [P] Create package skeleton:
  - Empty `__init__.py` in `src/gescrtl/` and in its subpackages `core`, `tracking`, `recording`, `settings`, `platform`, `tools`.
  - `tests/{support,unit,replay,fixtures}/` folders.
  - Done when: `python -c "import gescrtl"` works.
- [X] T003 [P] Add model download and ignores:
  - Add `scripts/fetch_model.ps1`. It downloads the MediaPipe `hand_landmarker.task` (float16 bundle from storage.googleapis.com) to `models/hand_landmarker.task` and skips the download if the file exists.
  - Add `models/`, `recordings/`, and `*.png`/`*.jpg` under `recordings/` to `.gitignore`.
  - Done when: running the script yields the model file.

---

## Phase 2: Foundational (blocks all stories)

- [X] T004 Define core types in `src/gescrtl/core/types.py` (D1). Use frozen dataclasses.
  - Inputs: `Landmark(x,y,z)`, `Hand(landmarks: tuple[Landmark,...21], handedness, score)`, `HandFrame(t_ns, hands)`.
  - `Command` enum: Resume, Pause, EmergencyStop, TurnOff, TurnOn, CameraLost, CameraBack, ReloadSettings, HotkeyUnavailable, HotkeyAvailable.
  - `CameraLost` carries a `cause: str`.
  - `State` enum: INACTIVE, PAUSED, ACTIVE, TRACKING_LOST.
  - `Sub` enum: NORMAL, CLUTCHED, HAND_MISSING, CAMERA_UNAVAILABLE, NONE.
  - `Pose` enum: G1–G7, NONE.
  - `CueKind` enum: HIDDEN, READY, PINCH, CLICK, DRAG, SCROLL, CLUTCH.
  - `Event` dataclasses: `StateChanged(state, sub, hud_text)`, `CueChanged(kind, progress)`, `MoveCursor(nx, ny)`, `ButtonDown(button)`, `ButtonUp(button)`, `Click(button)`, `Scroll(delta)`, `ReleaseAll(reason)`, `Warning(text)`, `HintsShown(items)`.
  - Done when: mypy strict passes.
- [X] T005 [P] Write `CoreConfig` in `src/gescrtl/core/config.py`. It is a frozen dataclass whose defaults equal `docs/interaction/safety-policy.md` plus plan values:
  - `active_region=0.6`
  - `one_euro_min_cutoff=1.0`, `one_euro_beta=0.007`, `one_euro_d_cutoff=1.0`
  - `min_confidence=0.5`, `stable_frames=3`, `loss_frames=3`
  - `pinch_enter=0.25`, `pinch_release=0.35`
  - `resume_hold_ms=1000`, `pause_hold_ms=1500`, `drag_hold_ms=300`
  - `right_click_cooldown_ms=300`, `pause_resume_cooldown_ms=1000`
  - `click_stabilize_ms=100`, `pinch_lookback_frames=2`
  - `scroll_max_rate=1800`, `scroll_deadzone_deg=8`, `scroll_full_deg=45`, `scroll_settle_ms=250`, `scroll_step=30`
  - `max_hand_jump=0.15`, `max_anchor_jump=0.12`
  - `stopped_display_ms=600`, `hint_display_ms=3000`
  - `double_click_ms=500`, `double_click_dist=0.005` (normalized; the platform converts `SM_CXDOUBLECLK` and overrides both at startup)
  - Done when: the module imports and has docstrings citing safety-policy.md.
- [X] T006 [P] Write the architecture guard in `tests/test_architecture.py`:
  - It scans `src/gescrtl/core/**/*.py` imports and fails on `cv2|mediapipe|PySide6|ctypes|time|socket|gescrtl.platform|gescrtl.tracking`.
  - It scans all of `src/` for `imwrite|socket|urllib|requests|http.client` and fails on any match. `scripts/` is not scanned.
  - Done when: it passes on the skeleton.
- [X] T007 [P] Write the JSONL reader/writer in `src/gescrtl/recording/jsonl.py` (D16):
  - `write_header(meta)`, `write_frame(HandFrame)`, `write_command(t_ns, cmd, arg)`.
  - The header has `format_version: 2`, tracker, camera, `mirrored`, `scenario`.
  - `read(path) -> Iterator[HandFrame | CommandRecord]` accepts v1 (the Phase 0 `spikes/feasibility/out/*.jsonl` shape: `hands[].landmarks` as `[x,y,z]` lists, `handedness`, `presence`) and v2.
  - Unknown line types are skipped.
  - No image fields ever.
  - Done when: the unit test in T008 passes.
- [X] T008 [P] Write the JSONL round-trip test in `tests/unit/test_jsonl.py`:
  - It writes frames plus commands, reads them back, and asserts they are equal.
  - It reads the first 50 lines of `spikes/feasibility/out/20261010-192935_pointing.jsonl` copied to `tests/fixtures/phase0_pointing_head.jsonl`. Copy the file, do not import spikes.
  - Done when: it passes.
- [X] T009 [P] Write synthetic hands in `tests/support/hands.py` (D17):
  - `pose(kind: Pose|"relaxed", cx, cy, scale=0.2, score=0.95) -> Hand` builds 21 plausible landmarks.
  - Each built pose must classify correctly with the T011 rules. Examples: open = all tips far from the wrist; fist = all four curled, thumb tucked; thumbs-up = all four curled, thumb out and away from the index tip; flat hand = four fingers extended, thumb across the palm; pinch-index = thumb tip ≈ index tip, ratio ≈ 0.1; pinch-middle; three fingers.
  - Script DSL `Script(fps=30).hold(pose, ms, at=(x,y)).move(pose, to=(x,y), ms).none(frames).cmd(Command, arg=None).frames() -> list[HandFrame|CommandRecord]`.
  - Timestamps start at 1_000_000_000 ns and step by 1/fps.
  - Add `run(engine, items) -> list[Event]`, which feeds `step`/`command` in order.
  - Done when: `tests/unit/test_hands_support.py` asserts each built pose classifies to its intended Pose. Write that test after T011.
- [X] T010 [P] Write the One Euro filter in `src/gescrtl/core/one_euro.py`:
  - Timestamp-based (seconds from `t_ns`), with `reset()`.
  - Test it in `tests/unit/test_one_euro.py`: a constant input gives a constant output; a step input converges; and it is deterministic.
- [X] T011 Write features and pose recognition in `src/gescrtl/core/features.py` and `src/gescrtl/core/poses.py` (D3):
  - `hand_size` = wrist→middle-MCP distance.
  - Pinch ratios are thumb-tip→index-tip and thumb-tip→middle-tip distances divided by `hand_size`.
  - A finger is "extended" when its tip is farther from the wrist than its PIP joint. For the thumb, compare the tip with IP vs the index MCP.
  - `anchor` = mean of landmarks 0, 5, 9, 13, 17. Mirror x when `mirrored`.
  - `raw_pose()` order:
    1. pinch-index or pinch-middle with hysteresis state (enter < `pinch_enter`, release > `pinch_release`; if both are below enter, the smaller ratio wins)
    2. all four curled: thumbs-up if the thumb is out and away from the index tip, otherwise fist
    3. all four extended: open palm if the thumb is out, otherwise flat hand
    4. three fingers
    5. otherwise relaxed
  - `PoseTracker.update(raw, t_ns) -> (stable_pose, since_t_ns)` changes the stable pose only after `stable_frames` consecutive identical raw poses.
  - Tests in `tests/unit/test_poses.py`:
    - each pose;
    - a ratio oscillating 0.24↔0.30 after the pinch starts keeps the pinch (no flicker);
    - a ratio oscillating 0.26↔0.34 from released never pinches;
    - stable-frame delay.
- [X] T012 Write the state machine in `src/gescrtl/core/state_machine.py` (D7, D8):
  - It implements the Pointer subset of the matrix in `docs/interaction/interaction-model.md`: E2–E11 and E15–E17, with exact HUD texts.
  - `ReleaseAll` is emitted on every exit from Active, on entry to Clutched, on TurnOff, and on EmergencyStop/Pause even from Paused (the matrix lists "no-op · RA").
  - The app starts in PAUSED.
  - It handles the pause/resume cooldown.
  - EmergencyStop shows `StateChanged(... "Stopped")`, then "Paused" after `stopped_display_ms`. This is driven by the next step/command timestamp.
  - Resume is refused while the hotkey is unavailable (FR-008): it emits a `Warning`.
  - Done when: the T015 tests pass.
- [X] T013 Write the engine in `src/gescrtl/core/engine.py` (D1):
  - Constructor: `Engine(config: CoreConfig, mirrored=True)`.
  - `step(frame: HandFrame | None, t_ns) -> list[Event]`.
  - `command(cmd, t_ns, arg=None) -> list[Event]`.
  - `apply_config(cfg) -> list[Event]`: emits `ReleaseAll("reload")` first, then swaps the config, keeping the state. This covers FR-024a.
  - Flow: primary-hand selection (simple stub until T047: pick the highest-score hand) → confidence gate → loss counter (`loss_frames` consecutive missing or low-confidence frames → E8) → poses → state machine → pointer (stubbed for US1 movement in T017).
  - Pure: no wall clock.
  - Done when: `tests/unit/test_engine_smoke.py` replays a synthetic script twice and gets equal event lists.

**Checkpoint**: the core skeleton runs synthetic scripts deterministically.

---

## Phase 3: US1 — Turn on control and move the cursor safely (P1) 🎯 MVP

**Goal**: Starts paused. Open palm resumes. The cursor follows the palm across the whole primary screen. Flat hand = clutch, flat hand held 1.5 s = pause. `Ctrl+Alt+Esc` stops. Hand loss is shown in the HUD. Turn off/on works.

**Independent Test**: spec US1 Independent Test, run live with `python -m gescrtl`.

### Tests (write first)

- [X] T014 [P] [US1] Write `tests/replay/test_us1_pointer_move.py`:
  - Moving the relaxed hand across the active region produces `MoveCursor` that reaches (0,0), (1,1), and every corner, clamped. A hand outside the region clamps to the edge with no jump.
  - Movement is smooth: no step bigger than 0.2 between frames for a 0.05/frame hand motion.
  - No `MoveCursor` is emitted while Paused.
- [X] T015 [P] [US1] Write `tests/replay/test_us1_states.py`. One test per transition:
  - Launch → Paused, with no input events.
  - G6 held for less than `resume_hold_ms` stays Paused; held for the full time → Active·Normal with "Pointer" and `HintsShown` (≤ 4 items).
  - Flat hand → Clutched (no Move while held), then back to Normal when released.
  - Flat hand held for 1.5 s → Paused + ReleaseAll; shorter stays Clutched.
  - A fist freezes the cursor but is not Clutched and never pauses, however long.
  - The thumb-out fist (G4) is neither clutch nor pause.
  - EmergencyStop from each state: no effect in Inactive; "Stopped" then "Paused" + ReleaseAll elsewhere.
  - Hand missing for less than `loss_frames` → no change. Missing for `loss_frames` → TrackingLost·HandMissing, "Hand not visible", RA.
  - Hand returns → Active·Normal automatically.
  - Paused + hand leaves and returns → still Paused.
  - TurnOff from each state → Inactive + RA. TurnOn → Paused.
  - Pause/Resume commands work, including the cooldown.
  - CameraLost → TC with cause text and RA. CameraBack → TH.
  - Resume refused while HotkeyUnavailable.
  - G7 held → no events except cue/none.
- [X] T016 [P] [US1] Write `tests/replay/test_determinism.py`: every script in `tests/replay/` registers itself in a shared list, and this test runs each one twice and asserts the event lists are equal. Use a `conftest.py` fixture registry in `tests/replay/conftest.py`.

### Implementation

- [X] T017 [US1] Implement movement in `src/gescrtl/core/pointer.py` (D4):
  - Anchor → One Euro filter → active-region map with clamping → `MoveCursor` only in Active·Normal.
  - Reset the filter on entering Active.
  - Cue READY in Normal, CLUTCH in Clutched, HIDDEN otherwise.
  - Wire it into `engine.py`.
  - Done when: T014 and T015 pass.
- [X] T018 [P] [US1] Define the platform interfaces in `src/gescrtl/platform/interfaces.py`:
  - `InputBackend`: `move(nx,ny)`, `button_down(b)`, `button_up(b)`, `click(b)`, `scroll(delta)`, `release_all()`, `double_click_ms()`, `double_click_dist()`.
  - `Overlay`: `on_event(Event)`.
  - `Hotkeys`: `start(on_emergency, on_toggle_pause, on_toggle_power) -> bool`.
  - `Tray`.
- [X] T019 [P] [US1] Write the Win32 input backend in `src/gescrtl/platform/win_input.py` (D13):
  - `enable_dpi_awareness()` calls `SetProcessDpiAwarenessContext(-4)`.
  - The primary monitor rect comes from `GetMonitorInfoW(MonitorFromPoint((0,0)))`.
  - `move` uses `SendInput` with `MOUSEEVENTF_MOVE|ABSOLUTE|VIRTUALDESK`, normalized over `SM_*VIRTUALSCREEN`.
  - The class is lock-guarded, keeps a set of pressed buttons, and its `release_all` is idempotent.
  - `GetDoubleClickTime`/`SM_CXDOUBLECLK` are converted to normalized distances.
  - Add a manual smoke script, `python -m gescrtl.platform.win_input --corners`, that moves to the 4 corners and the center with a 1 s pause between moves.
- [X] T020 [P] [US1] Write the camera thread in `src/gescrtl/tracking/camera.py` (D11, basic part):
  - `cv2.VideoCapture(index, CAP_DSHOW)` with MJPG at 640×480@30.
  - The thread keeps only the latest frame plus its `perf_counter_ns` timestamp; the slot holds one frame and is overwritten.
  - `get_latest(timeout)`.
  - `stop()` releases the device.
  - Reconnect is added in T048.
- [X] T021 [P] [US1] Write the MediaPipe adapter in `src/gescrtl/tracking/mediapipe_adapter.py`:
  - `HandLandmarker` in VIDEO mode with `num_hands=2`, model `models/hand_landmarker.task`, and a clear error if the model is missing ("run scripts/fetch_model.ps1").
  - Mirror the frame horizontally before detection.
  - `detect(frame, t_ns) -> HandFrame`, with timestamps in ms that increase monotonically.
  - Score = handedness score.
  - Return per-stage timings (`grab_ns`, `track_ns`).
- [X] T022 [P] [US1] Write the global hotkeys in `src/gescrtl/platform/win_hotkeys.py` (D12):
  - A thread runs `RegisterHotKey` + `GetMessageW` for `Ctrl+Alt+Esc` (emergency), `Ctrl+Alt+P` (pause/resume), and `Ctrl+Alt+O` (turn off/on).
  - `start()` returns False if the emergency hotkey registration fails.
  - The emergency callback runs `input.release_all()` on this thread before it enqueues the command.
  - `stop()` posts `WM_QUIT`.
- [X] T023 [P] [US1] Write the HUD pill in `src/gescrtl/platform/hud.py` (D14):
  - A frameless PySide6 widget at the top-right of the primary screen.
  - Flags `Tool|WindowStaysOnTopHint|WindowTransparentForInput|WindowDoesNotAcceptFocus` + `WA_ShowWithoutActivating` + `WA_TranslucentBackground`.
  - After show, set `WS_EX_NOACTIVATE|WS_EX_TRANSPARENT|WS_EX_LAYERED|WS_EX_TOOLWINDOW` via ctypes.
  - Text/colour per `docs/interaction/feedback-hud.md`, including the first-launch hint "Show open palm to start".
  - Hints are shown for `hint_display_ms`.
  - Hidden in Inactive.
  - Updated by a Qt signal carrying `Event`s.
- [X] T024 [P] [US1] Write the tray in `src/gescrtl/platform/tray.py`:
  - `QSystemTrayIcon` with On/Off icon states.
  - Menu items: Resume/Pause, Turn off/Turn on, Reload settings, Reset to defaults, Exit.
  - Items enqueue commands.
  - Warnings are shown via `showMessage`.
- [X] T025 [US1] Write app wiring in `src/gescrtl/app.py` and `src/gescrtl/__main__.py` (D12):
  1. `enable_dpi_awareness()` before `QApplication`.
  2. Load settings. Use the CoreConfig defaults until T040.
  3. Start the hotkeys and send `HotkeyUnavailable` if registration fails.
  4. Run the worker thread loop:
     - drain the command queue, waiting at most 50 ms;
     - grab the latest frame;
     - in Paused, track only every 3rd frame (≈10 FPS);
     - otherwise run `adapter.detect` → `engine.step`;
     - dispatch input events to `InputBackend`;
     - emit UI events to Qt.
  5. In Inactive, stop the camera and drop references to it. TurnOn reopens it.
  6. Make ReleaseAll happen on exit: worker `try/finally: input.release_all()`, `atexit`, `sys.excepthook`, `threading.excepthook`, and `SetConsoleCtrlHandler`.
  7. Exit from the tray stops the threads cleanly.
  - Done when: running `python -m gescrtl` starts Paused with the HUD visible.
- [X] T026 [US1] Add stage timing in `src/gescrtl/app.py`:
  - For each frame, record `grab→track→engine→input` durations in a ring buffer of the last 1000 frames.
  - Expose `stats()` returning p50/p95 delay and FPS. This covers FR-032. T050 uses it.

**Checkpoint**: MVP. Do a live check of US1 scenarios 1–8 (deferred to the T055 session, or run a quick check now).

---

## Phase 4: US2 — Click, double-click, right-click (P2)

**Goal**: Pinch taps click where the user aimed. Two taps make a double-click. A thumb–middle pinch makes a right-click with a cooldown.

**Independent Test**: a 48 px target page: click, double-click, and right-click succeed, and there are no accidental clicks.

- [X] T027 [P] [US2] Write `tests/replay/test_us2_clicks.py`:
  - **Tap**: G2 for 150 ms → exactly one `Click(left)`, at the position from `pinch_lookback_frames` before the stable onset. The hand moves during the pinch; assert that the position is still the pre-pinch one.
  - **Double-click**: two taps 250 ms apart with a small hand drift → two `Click(left)`, the second at the first click's position.
  - **Two taps too far apart in time**: 700 ms apart → two clicks, and the second uses its own position.
  - **Right-click**: a G3 tap → one `Click(right)`. A second G3 within 300 ms → none.
  - **Hover flicker**: a ratio oscillating around 0.25–0.35 never clicks.
  - **Low-confidence pinch**: score 0.3 → no click.
  - **Cue sequence**: READY → PINCH with increasing progress → CLICK → READY.
- [X] T028 [US2] Implement clicks in `src/gescrtl/core/pointer.py` (D5):
  - At the stable G2/G3 onset, freeze the cursor at the lookback position for `click_stabilize_ms`. The cursor stays frozen until release or drag start.
  - Releasing before `drag_hold_ms` → `Click`.
  - Double-click snap: if the onset falls within `double_click_ms` and `double_click_dist` of the last left click, use the last click position.
  - G3 never drags and respects the cooldown.
  - Cue PINCH progress = clamp((release − ratio)/(release − enter)) computed on the raw ratio, starting before the stable onset. Cue CLICK on emit.
  - Done when: T027 passes.
- [X] T029 [US2] Implement the platform click path in `src/gescrtl/platform/win_input.py`:
  - `click(b)` = down+up in one `SendInput` call, at the current cursor position. The engine has already emitted `MoveCursor` to the frozen point.
  - Feed `double_click_ms()` into CoreConfig in `app.py` (done in T025; `double_click_dist` stays a config value).
- [X] T030 [P] [US2] Add the cursor cue to `src/gescrtl/platform/hud.py` (D14):
  - A second click-through window, 48 px, centred on the last `MoveCursor` position converted to pixels via the primary monitor rect.
  - Draws: ring (READY), arc (PINCH progress), flash for 150 ms (CLICK), filled (DRAG), arrows (SCROLL), dashed (CLUTCH).
  - Hidden on HIDDEN.
  - Updates on each `CueChanged`/`MoveCursor` event with no timer polling.
- [X] T031 [P] [US2] Write the target page tool in `src/gescrtl/tools/targets.py`:
  - A PySide6 full-screen window with random 24/48/96 px targets.
  - It logs hit/miss for left, double, and right clicks to `recordings/<ts>_targets.csv` (numbers only).
  - Done when: it gives a summary of hit rate per size. It is used for SC-005.

---

## Phase 5: US3 — Drag and scroll (P3)

**Goal**: Hold a pinch to drag and release to drop. A fist with the thumb out scrolls the page by thumb tilt, like a held scroll wheel.

**Independent Test**: drag a file between folders; scroll a long document to the end and back.

- [X] T032 [P] [US3] Write `tests/replay/test_us3_drag.py`:
  - A G2 held for 400 ms + move → `ButtonDown(left)` at the frozen position, followed by `MoveCursor`s and a `ButtonUp` on release. No `Click`.
  - Drag + hand missing for `loss_frames` → `ReleaseAll`/`ButtonUp`, no re-press when the hand returns still pinching. A new drag requires a release and a fresh pinch.
  - A drag + 2-frame gap (less than `loss_frames`) → the drag continues.
  - A drag + Pause / EmergencyStop / TurnOff / ReloadSettings → released immediately.
  - The cue is DRAG during the drag.
- [X] T033 [P] [US3] Write `tests/replay/test_us3_scroll.py` (thumb-tilt scroll, see plan D6):
  - Level thumb → no `Scroll`; tilt up → positive deltas; tilt down → negative; larger tilt → faster; inside the dead zone → none; capped beyond full tilt.
  - Neutral is where the pose started (formed tilted → no scroll until tilted further); a vertical thumbs-up does not run away; no scrolling while settling.
  - Speed independent of FPS (30 vs 60); whole `scroll_step` events; no `MoveCursor` while scrolling; cue shows signed strength.
  - Stops when the pose ends, on pause, on hand loss, and with low confidence.
- [X] T034 [US3] Implement drag in `src/gescrtl/core/pointer.py` (D5):
  - G2 stable for `drag_hold_ms` → `ButtonDown` at the frozen point, then unfreeze and follow the hand.
  - Release → `ButtonUp`.
  - Any `ReleaseAll` clears the drag state, and there is no automatic re-press.
  - Done when: T032 passes.
- [X] T035 [US3] Implement scroll in `src/gescrtl/core/pointer.py` (D6):
  - Thumb tilt from `Features.thumb_tilt_deg`, filtered; start angle taken when G4 is stable (follows the thumb for `scroll_settle_ms`).
  - Rate curve with dead zone and cap; `acc += rate * dt`; emit whole multiples of `scroll_step`; only while the raw pose is G4.
  - The cursor stays frozen. Done when: T033 passes.
- [X] T036 [P] [US3] Implement the platform `button_down`/`button_up`/`scroll` in `src/gescrtl/platform/win_input.py`:
  - `MOUSEEVENTF_WHEEL` with `mouseData=delta`.
  - Track pressed buttons for `release_all`.

---

## Phase 6: US4 — Adjust sensitivity and restore defaults (P4)

**Goal**: A JSON settings file with validation, tray reload, and reset.

**Independent Test**: change `active_region`, reload from the tray, and check that the hand travel changes; reset and check that the defaults are back.

- [ ] T037 [P] [US4] Write `tests/unit/test_settings.py` using `tmp_path`:
  - A missing file → defaults are written.
  - A valid change is loaded.
  - `active_region: -1` → default used + a warning naming `active_region`; the other fields are still loaded.
  - Bad JSON → all defaults + a warning, and the file is not overwritten.
  - Unknown keys → ignored with a warning.
  - There is no field for the emergency hotkey, pause, or release-on-loss; assert the model has no such keys.
  - Reset rewrites the defaults.
- [ ] T038 [P] [US4] Write `tests/replay/test_us4_reload.py`:
  - `engine.apply_config(new)` during a drag → `ReleaseAll` first; the state and sub are unchanged.
  - A new `active_region` changes the `MoveCursor` mapping for the same hand path.
- [ ] T039 [US4] Write the settings store in `src/gescrtl/settings/store.py` (D15):
  - A pydantic `Settings` model mirrors the tunable `CoreConfig` fields, with `Field(ge,le)` ranges. Examples:
    - `active_region` 0.2–1.0
    - `min_confidence` 0.1–0.95
    - `stable_frames` 1–10
    - `pinch_enter` 0.05–0.5 < `pinch_release` 0.1–0.6
    - hold times 100–5000 ms
    - `scroll_max_rate` 100–6000
  - Path: `%APPDATA%\GesCRTL\settings.json`, overridable for tests.
  - `load() -> (Settings, warnings)` validates field by field.
  - Also: `save()`, `reset()`, `to_core_config()`.
- [ ] T040 [US4] Wire settings in `src/gescrtl/app.py` and `src/gescrtl/platform/tray.py`:
  - Load settings at startup and show warnings via the tray/HUD.
  - Tray "Reload settings" → load → `engine.apply_config` (ReleaseAll first) → warnings.
  - Tray "Reset to defaults" → `reset()` → reload.
  - No file watching.
  - Done when: T037 and T038 pass and a manual reload works.

---

## Phase 7: US5 — Record and replay sessions (P5)

**Goal**: Live landmark recording (no images), and a camera-free replay that is identical every time.

**Independent Test**: record a 30 s session with clicks, a drag, a scroll, and a hand loss; replay it twice; the outputs are identical; no camera is used and no OS input is sent.

- [X] T041 [P] [US5] Write `tests/replay/test_us5_replay_cli.py`:
  - Run `gescrtl.replay.main([fixture])`, capture stdout twice, and assert the two outputs are equal.
  - Monkeypatch-assert that `gescrtl.platform` and `cv2` are never imported, by checking `sys.modules` before and after the run in a subprocess.
- [X] T042 [US5] Add recording to `src/gescrtl/app.py` and `src/gescrtl/__main__.py`:
  - `--record NAME` writes `recordings/<YYYYmmdd-HHMMSS>_<NAME>.jsonl` via `recording/jsonl.py`. It contains every tracked `HandFrame` and every command, including camera events, with their timestamps.
  - The HUD pill shows "● REC".
  - No image data is written.
- [X] T043 [US5] Write the replay CLI in `src/gescrtl/replay.py`:
  - `python -m gescrtl.replay FILE [--settings PATH]` feeds the file to `Engine`, using `CoreConfig` defaults or the given settings.
  - It prints one line per event, `t_ms<TAB>EventRepr`, and a summary of counts per event type.
  - It uses no camera, no Qt, and no OS input.
- [X] T044 [US5] Document how to turn a misfire into a test in `tests/fixtures/README.md`:
  1. Record the misfire.
  2. Trim it with `python -m gescrtl.replay FILE --slice START_MS END_MS --out tests/fixtures/NAME.jsonl`. Add `--slice` to T043.
  3. Write a failing test asserting no misfire.
  4. Fix it.

  Add an example test, `tests/replay/test_fixture_regressions.py`, that loads every `tests/fixtures/*.jsonl` that has a sidecar `*.expect.json` (a list of forbidden event types) and asserts that none of them occur.

---

## Phase 8: Reliability Hardening (Phase 2 items H1–H6)

- [ ] T045 [P] Write `tests/replay/test_h1_primary_hand.py` (H1):
  - A second synthetic hand pinching or moving anywhere while the primary hand is relaxed → 0 clicks and the cursor follows the primary hand only.
  - The primary hand leaves while a second hand stays → TrackingLost (no swap).
  - On return with 2 hands → the one nearest the last primary position is chosen.
  - The hand that completed the resume hold becomes primary even if another hand has a higher score.
- [ ] T046 [P] Write `tests/replay/test_h3_uncertain.py` (H3):
  - During a pinch, insert frames with score below `min_confidence` → no click until the pose is stable again for `stable_frames`.
  - An anchor jump greater than `max_anchor_jump` in 1 frame → that frame is rejected and the cursor holds.
  - `loss_frames` consecutive bad frames during a drag → `ButtonUp`/RA.
- [ ] T047 Write primary-hand lock and jump rejection in `src/gescrtl/core/primary_hand.py` (D9, D10):
  - `PrimaryHand.select(frame) -> Hand | None` with nearest-wrist continuity within `max_hand_jump`.
  - Lock at resume completion: the engine passes the hand that held G6. In Paused, track the candidate hand that is holding G6.
  - Reacquire nearest on return.
  - Replace the T013 stub in `engine.py`.
  - Done when: T045 and T046 pass.
- [ ] T048 Add camera recovery to `src/gescrtl/tracking/camera.py` + `src/gescrtl/app.py` (D11, H2):
  - No frame for 1 s or a `read()` failure → enqueue `CameraLost(cause)`.
  - If the open fails while the device still exists, the cause is "in use by another app"; otherwise "disconnected".
  - Retry the open every 2 s → `CameraBack`.
  - Never retry while Inactive.
  - Unit test `tests/unit/test_camera_recovery.py` uses a fake `VideoCapture` factory: it fails reads, then succeeds; assert the command sequence and the retry timing with an injected clock.
- [ ] T049 [P] Write the benchmark replay mode in `src/gescrtl/tools/bench.py` (D18, H4):
  - `--replay GLOB` runs each file through `Engine`.
  - The scenario comes from the header `scenario`.
  - It counts consequential events (Click, ButtonDown, Scroll, and Resume transitions) per scenario.
  - It reports false triggers per minute for the `idle|typing|talking|second-person` scenarios.
  - Exit code 1 if any of those scenarios has a count above 0.
  - It prints a markdown table.
- [ ] T050 Write the benchmark live mode in `src/gescrtl/tools/bench.py` (FR-032):
  - `--live SECONDS` runs the real pipeline with a `NullInput` backend: it counts events and sends no OS input.
  - It reports capture→engine-done p50/p95, tracking FPS, and process CPU% (psutil, normalized to total CPU) for Active and Paused/no-hand. Use `--paused` to start Paused.
  - It prints a markdown table.
- [ ] T051 Tune values and finalize docs (H5, D19). Do this after T055 recordings exist:
  - Run `bench --replay` on the real recordings with candidate values passed via `--settings`.
  - Pick final values in this order: confidence, stable frames, pinch ratios, hold times, cooldowns, click stabilize.
  - Update the `CoreConfig`/`Settings` defaults.
  - Remove every *(provisional)* mark in `docs/interaction/safety-policy.md`, with the evidence line.
  - Add any new idle-scenario misfire as a fixture (T044 flow).

---

## Phase 9: Polish & verification

- [ ] T052 [P] Write `README.md` (short):
  - What it is.
  - Run-from-source steps (venv, `pip install -e ".[dev]"`, `scripts/fetch_model.ps1`, `python -m gescrtl`).
  - The Pointer gesture table.
  - Safety controls (`Ctrl+Alt+Esc`, flat-hand hold, tray).
  - The privacy statement.
  - A link to `docs/product/known-limitations.md`.
- [ ] T053 [P] Update `docs/product/known-limitations.md`:
  - G7/mode menu inactive in this phase.
  - Scroll is vertical only; high-resolution wheel deltas may be coarse in some apps.
  - Camera recovery behaviour.
- [ ] T054 Run the quality gate:
  - `ruff check .`, `ruff format --check .`, `mypy src/gescrtl/core`, and `pytest` must all be green.
  - Fix any issues found.
  - Confirm that every transition and gesture in plan.md "Replay Test Coverage" has a test (FR-030/SC-009). Add any missing ones.
- [ ] T055 Run the one manual session (user, PowerShell venv), following the plan.md "Validation" checklist:
  - US1–US4 acceptance scenarios.
  - SC-001 first-resume time.
  - SC-002 task set timed.
  - SC-005 via `python -m gescrtl.tools.targets`.
  - SC-006 stop/pause/loss.
  - SC-007 at 100/125/150% scaling.
  - SC-008 via `bench --live --paused`.
  - H2 unplug and the Windows Camera app.
  - SC-010: `recordings/` contains only `.jsonl` files and `Get-NetTCPConnection -OwningProcess <pid>` shows no connections.
  - Record `idle`, `typing`, `talking`, `second-person`, and `demo` sessions totalling at least 10 min of non-controlling hands. Then run T051 and `bench --replay`.
- [ ] T056 Write `docs/measurements/phase1-2-report.md`:
  - The measured numbers from T055, `bench --live`, `bench --replay`, and `targets`.
  - Pass/fail for each SC and H item.
  - A short retrospective (H6: activation/pause changes; constitution amendments, if any).

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T013)** → user stories.
- **US1 (T014–T026)** is the MVP and all live stories depend on it: the platform backends and app wiring (T018–T025) are reused.
- **US2 (T027–T031)** and **US3 (T032–T036)** both edit `core/pointer.py` and `platform/win_input.py`, so do them in order US2 → US3.
- **US4 (T037–T040)** depends only on Foundational + T025. It can run in parallel with US2/US3 if a different person edits `app.py` with care.
- **US5 (T041–T044)**: T043 depends on Foundational only. T042 depends on T025.
- **Hardening**:
  - T045–T047 depend on T013 + T017.
  - T048 depends on T020/T025.
  - T049 depends on T043.
  - T050 depends on T026.
  - T051 depends on T055 recordings.
- **Polish**: T054 runs before T055. T055 runs before T051, and T051 before T056.

Within each story, tests come first and must fail before the implementation, which must then make them pass.

## Parallel Examples

- Foundational: T005, T006, T007+T008, T009, and T010 can run together after T004.
- US1: T014–T016 (tests) together; then T018–T024 (separate platform/tracking files) together while T017 is done in core.
- US2: T027, T030, and T031 together; T028 → T029 sequential.
- US3: T032, T033, and T036 together; T034 → T035 sequential (same file).
- Hardening: T045, T046, and T049 together.

## Implementation Strategy

1. Setup + Foundational → the core runs synthetic scripts.
2. US1 → **stop and validate live**: move, clutch, pause, stop, loss. This is the MVP demo.
3. US2 → US3: the full mouse vocabulary, each validated by replay tests.
4. US4 and US5: settings and the recording/replay tooling.
5. Hardening T045–T050, then the single manual session T055 → tuning T051 → report T056.
