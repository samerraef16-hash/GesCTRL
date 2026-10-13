# Tasks: Keyboard Mode, Personalization, Custom Gestures, and Calibration

**Input**: `specs/004-keyboard-personalization/plan.md` (decisions D0–D11), `spec.md` (US1–US5,
FR-001–FR-030)

**Tests**: Required (constitution IV, FR-029). In each story, write the tests first and confirm
they fail before implementing.

**Format**: `- [ ] T### [P?] [US?] What, where — done when`.

Conventions:
- "Dn" refers to a decision in plan.md. Read it before starting the task.
- Core code (`src/gescrtl/core/`) MUST NOT import cv2, mediapipe, PySide6, ctypes, comtypes,
  pycaw, winreg, or `time`. `tests/test_architecture.py` enforces this.
- Never import from `spikes/`.
- Synthetic replay scripts use `tests/support/hands.py`. Every new replay test also runs its
  script twice on fresh engines and asserts identical events (SC-010).
- Keyboard Mode and `SETUP` MUST NOT emit `MoveCursor`, `Click`, `ButtonDown`, or `Scroll`.
  Assert this in every Keyboard, calibration, and enrollment test.
- `(user)` tasks need the camera, a second monitor, or a human. Stop and ask the user to run
  them, giving exact PowerShell commands. Don't invent their results.
- Behaviour from specs 002/003 must not change unless a task says so. The full existing test
  suite stays green after every phase.

---

## Phase 1: Setup (rule change first, D0)

- [X] T001 Amend `.specify/memory/constitution.md` to v1.2.0: add the Keyboard-Mode confirming-hand exception to Principle I (exact wording in D0), bump the version and amendment date, and add a sync-impact note. Update the "one primary hand only" line in `CLAUDE.md` to match. Done when: both files state the exception and nothing else in Principle I changed.
- [X] T002 [P] Write `docs/adr/0007-keyboard-two-hand-confirm.md` (context, decision, the same-person check from D3, rejected alternatives, consequences including the mandatory bystander fixture). Done when: the ADR follows the format of `docs/adr/0006-*.md`.
- [X] T003 [P] Extend `tests/support/hands.py`:
  - `Script` can add a **second hand** per frame (`second=pose(...)`, with its own handedness label and position).
  - `Script.path(points, pose, duration_ms)` moves the anchor along a polyline (for custom movements).
  - `Script` can emit `Command.DISPLAYS` and `Command.START_SETUP/END_SETUP` at a given time.
  - Done when: a tiny test builds a two-hand frame and a circle path, and `features.compute()` works on both hands.

---

## Phase 2: Foundational (blocks all stories)

- [X] T004 Add to `src/gescrtl/core/types.py` (D2–D9):
  - `Sub.SETUP`; `Command.START_SETUP`, `END_SETUP`, `DISPLAYS`.
  - `OverlayKind.KEYBOARD`, `OverlayKind.SETUP`; `CueKind.DWELL`.
  - `Action`: `COPY, PASTE, CUT, UNDO, REDO, SELECT_ALL, WIN, ESC, MODE_POINTER, MODE_PRESENTATION, MODE_MEDIA, MODE_KEYBOARD`.
  - Events: `KeyStroke(key: str, mods: frozenset[str])`, `KeyboardView(...)` (fields per D2), `SetupView(step: str, text: str, progress: float, target: tuple[float, float] | None)`, `SetupResult(kind: str, values: dict[str, object] | None)`, `CustomFired(name: str, action: Action)`.
  - Done when: mypy --strict passes on core and existing tests are green.
- [X] T005 Add the D1 core fields to `src/gescrtl/core/config.py` (`confirm_method`, `dwell_ms`, `dwell_still_dist`, `pointer_dwell_click`, `two_hand_press`, `second_hand_max_dist`, `keyboard_position`, `key_repeat_delay_ms`, `key_repeat_ms`, `key_cooldown_ms`, `active_center_x`, `active_center_y`, `mappings` as a tuple of pairs, `custom_gestures_enabled`, `custom_hold_ms`, `custom_cooldown_ms`), with the defaults from D1. Done when: `CoreConfig()` builds and existing tests are green.
- [X] T006 Make `src/gescrtl/settings/store.py` type-aware (D1): each field validated by its own `TypeAdapter`; bool rejected only for numeric fields; add every D1 field with its range and a `title` on every `Field`; `to_core_config` excludes `overlay_monitor`, `start_with_windows`, `calibrated_at`; `mappings` dict → tuple of pairs. Tests in `tests/unit/test_settings.py`: bool/str/literal/dict fields, bad values warn and default, every field has a title, old settings files still load. Done when: tests pass.
- [X] T007 Add `DwellSelector` to `src/gescrtl/core/select.py` (D4): fire once after `dwell_ms` on one target with the point within `dwell_still_dist`; re-arm on target change or a move > 2× the distance; `progress` property. Also let `PinchSelector` take an external pinch signal (needed by D3). Tests in `tests/unit/test_dwell.py`. Done when: fire, no-repeat, re-arm, progress, and the external signal are covered and pass.
- [X] T008 Add `Sub.SETUP` to `src/gescrtl/core/state_machine.py` and route it in `src/gescrtl/core/engine.py` (D7): `START_SETUP`/`END_SETUP` commands enter/leave (Active only; ignored otherwise), `ReleaseAll` on enter and exit, pill text "Setup", pause / emergency stop / loss behave as in Normal and end the session with `SetupResult(kind, None)`. The engine forwards features to a pluggable setup session (protocol in `src/gescrtl/core/modes.py`: `update(feats, raw, stable, t_ns) -> (events, result | None)`). Tests in `tests/replay/test_setup_state.py` with a dummy session: no pointer/key events while in SETUP, every exit path, replay of recorded commands. Done when: tests pass.

**Checkpoint**: foundation ready. Stories can now start; US1 first.

---

## Phase 3: User Story 1 – Type short text and use shortcuts (P1) 🎯 MVP

**Goal**: Keyboard Mode with an on-screen keyboard, modifiers, shortcut row, recent-text strip,
and two-handed pressing.

**Independent Test**: In a text editor, type a short phrase, fix a typo with Backspace, press
Enter, copy and paste a word — no physical keyboard.

### Tests (write first, see them fail)

- [X] T009 [P] [US1] `tests/replay/test_us1_keyboard.py`: per plan "Replay Test Coverage" row for this file. Done when: tests exist and fail for the right reason.
- [X] T010 [P] [US1] `tests/replay/test_us1_modifiers.py`: one-shot, locked, off; Shift folds into upper case; Ctrl+C; modifiers cleared on pause/loss/stop/mode change. Done when: tests exist and fail.
- [X] T011 [P] [US1] `tests/replay/test_us1_two_hand.py`: every case in the plan row (same label, too far, bystander, both pinch = one press, second hand lost, setting off, other modes). Done when: tests exist and fail.
- [X] T012 [P] [US1] Extend `tests/unit/test_layout.py`: every keyboard key ≥ 48 px at 1280×720 in both positions, no overlaps, all D2 keys present. Done when: tests exist and fail.

### Implementation

- [X] T013 [P] [US1] Add `keyboard_keys(position)` to `src/gescrtl/core/layout.py` (D2 rows, ids such as `"k:a"`, `"k:enter"`, `"s:copy"`, `"m:shift"`, `"move"`). Done when: T012 passes.
- [X] T014 [US1] Create `src/gescrtl/core/keyboard.py` `KeyboardController` (D2): hand → keyboard-rect mapping with One Euro, highlight via `layout.hit`, confirm via `PinchSelector` or `DwellSelector` per `confirm_method`, modifiers, repeat for Backspace/arrows, `recent` text, Move key, `KeyboardView` on changes, `reset()`. Done when: T009 and T010 pass.
- [X] T015 [US1] Create `src/gescrtl/core/second_hand.py` `SecondHand` (D3: the five acceptance checks, nearest-wrist following, own classifier/tracker, pinch onset → external signal). Done when: the unit cases in T011 that don't need the engine pass.
- [X] T016 [US1] Wire Keyboard Mode in `src/gescrtl/core/engine.py` and `src/gescrtl/core/state_machine.py`: `Mode.KEYBOARD` selectable from menu and tray, controller registered, other hands passed to `SecondHand` only in Keyboard · Normal with `two_hand_press`, hints text per D2, `apply_config` rebuilds it. Done when: T009–T011 pass and spec 003 tests still pass (update the ones that asserted Keyboard is unavailable).
- [X] T017 [US1] Add `key_stroke(key, mods)` to `InputBackend` in `src/gescrtl/platform/interfaces.py` and implement it in `src/gescrtl/platform/win_input.py` (D10: Unicode for plain characters, VK for named keys, `VkKeyScanW` with modifiers, one `SendInput` per stroke, chord marked in `_keys_down` before sending). Add the new shortcut `Action`s to `default_keys_for`. Done when: a unit test with a fake `_send` checks the INPUT sequences for `"a"`, `"A"`, `"é"`, `"enter"`, Ctrl+C, Win.
- [X] T018 [US1] Add `KeyboardOverlay` to `src/gescrtl/platform/overlays.py` and route `KeyboardView`/`KeyStroke`/`CustomFired` in `src/gescrtl/platform/hud.py` and `src/gescrtl/app.py` (D11): keys, highlight, flash, modifier states, recent strip, dwell ring, top/bottom position; click-through and non-activating. Done when: `python -m gescrtl` shows the keyboard in Keyboard Mode and it never takes focus (manual check by the user in T019).
- [ ] T019 [US1] (user) Record R1 `typing_one_hand`, `typing_two_hands`, R2 `bystander_pinch`, R3 `idle_keyboard` (plan "Recordings to make"); copy to `tests/fixtures/` with `.expect.json`; extend `tests/replay/test_fixture_regressions.py`. Done when: the fixtures replay with the expected KeyStrokes, and 0 from the bystander and idle recordings.

**Checkpoint**: Keyboard Mode works end to end (MVP).

---

## Phase 4: User Story 2 – Adjust GesCRTL without editing files (P2)

**Goal**: Settings window, remapping, reset, Start with Windows.

**Independent Test**: From the tray, change range and a hold time, remap a swipe, reset — no
file opened.

### Tests

- [X] T020 [P] [US2] `tests/unit/test_mapping.py`: defaults, overrides, unknown slot/action warns, excluded actions not representable, mode action uses the SET_MODE path, grid labels from resolved actions. Done when: tests exist and fail.
- [X] T021 [P] [US2] Extend `tests/unit/test_settings.py`: reset disables every custom gesture without deleting it (with a fake custom store). Done when: test exists and fails.

### Implementation

- [X] T022 [US2] Create `src/gescrtl/core/mapping.py` (D6: slots, allowed actions, `resolve`). Use it in `src/gescrtl/core/presentation.py` (swipes, thumbs) and `src/gescrtl/core/media.py` (grid positions `media.t0..t9`); make `MODE_*` actions go through the `SET_MODE` path in `src/gescrtl/core/state_machine.py`. Done when: T020 passes and spec 003 replay tests pass unchanged with default mappings.
- [X] T023 [US2] Create `src/gescrtl/platform/win_autostart.py` (D5: set/remove `HKCU\…\Run\GesCRTL`, command from `sys.executable` preferring `pythonw.exe`). Apply `start_with_windows` on settings apply in `src/gescrtl/app.py`. Done when: a unit test with a fake registry writer checks the command line, and turning it off removes the value.
- [X] T024 [US2] Create `src/gescrtl/platform/settings_window.py` (D5): tabs, controls generated from `Settings.model_fields` (title, ge/le), Literal fields as combo boxes, bool as check boxes; Apply validates with `store.parse`, shows warnings per field, saves, calls the existing reload; reloads its values when the file is reloaded from the tray; in-window reset confirmation. Gestures tab: one combo per remappable slot. Done when: the window opens from the tray and an applied value reaches the engine (manual check in T026).
- [X] T025 [US2] Add "Settings…" to `src/gescrtl/platform/tray.py` and wire it in `src/gescrtl/app.py`; make Reset also disable custom gestures (T021). Done when: T021 passes.
- [ ] T026 [US2] (user) Acceptance check for US2 and SC-005 (timed). Done when: the user confirms each scenario.

---

## Phase 5: User Story 3 – Calibrate to my hand, camera, and reach (P2)

**Goal**: Guided calibration and the accessibility options (dwell everywhere, reduced movement).

**Independent Test**: Run calibration from the tray; afterwards reach all corners and click with
the new pinch thresholds; cancel a second run and confirm nothing changed.

### Tests

- [X] T027 [P] [US3] `tests/replay/test_us3_calibration.py`: per the plan row (check failures, reach → region/center, pinch → thresholds with hysteresis, too-similar failure, cancel/pause/loss → `SetupResult(None)`, no input). Done when: tests exist and fail.
- [X] T028 [P] [US3] `tests/replay/test_dwell_modes.py`: dwell in mode menu, Media grid, level panel ± targets (step and repeat); pointer dwell click opt-in, fires once, re-arms after a move, never during clutch/fist/scroll/drag; pinch still works with dwell on. Done when: tests exist and fail.

### Implementation

- [X] T029 [US3] Create `src/gescrtl/core/calibration.py` (D7 steps and math) as a setup session; add `active_center_x/y` to the mapping in `src/gescrtl/core/pointer.py` (defaults keep today's behaviour). Done when: T027 passes and spec 002 pointer tests are unchanged.
- [X] T030 [US3] Add dwell to `src/gescrtl/core/mode_menu.py`, `src/gescrtl/core/media.py`, `src/gescrtl/core/level_panel.py` (with `LEVEL_STEP_TARGETS` in `src/gescrtl/core/layout.py`), and the pointer dwell click to `src/gescrtl/core/pointer.py` (D4, `CueKind.DWELL`). Done when: T028 passes.
- [X] T031 [US3] Add `SetupOverlay` to `src/gescrtl/platform/overlays.py`; "Calibrate…" in the tray and in the settings window; on `SetupResult` show Keep / Discard; Keep merges values, sets `calibrated_at`, saves, reloads (`src/gescrtl/app.py`). Draw ± targets and the dwell ring in the existing overlays. Done when: a calibration run can be kept or discarded (manual check in T032).
- [ ] T032 [US3] (user) Record R6 `calibration`; acceptance check for US3; SC-006 with at least 3 people or setups. Done when: results are noted for the report.

---

## Phase 6: User Story 4 – Use GesCRTL across several monitors (P3)

**Goal**: The cursor covers all monitors as one area; overlays on a chosen monitor.

**Independent Test**: Two monitors at different scaling: reach all corners of each and hit 48 px
targets on both.

### Tests

- [X] T033 [P] [US4] `tests/unit/test_displays.py` and `tests/replay/test_us4_displays.py`: two and three monitors, mixed sizes, vertical offsets, gaps clamp to the nearest monitor; `DISPLAYS` change mid-session; recordings without `DISPLAYS` replay exactly as before; double-click snapping keeps its pixel distance. Done when: tests exist and fail.

### Implementation

- [X] T034 [US4] Create `src/gescrtl/core/displays.py` (layout from the `DISPLAYS` arg, desktop box, `clamp`); in `src/gescrtl/core/engine.py` handle `Command.DISPLAYS`; in `src/gescrtl/core/pointer.py` map to the desktop box and clamp; scale `double_click_dist` (D8). Done when: T033 passes and every existing fixture replays unchanged.
- [X] T035 [US4] Create `src/gescrtl/platform/displays.py` (`EnumDisplayMonitors` + `GetMonitorInfoW`, Qt screen signals, 2 s poll, posts `DISPLAYS` only when the layout changed); `WinInput.move` maps over the virtual rect; overlays placed on `overlay_monitor` with fallback to primary; Displays tab lists monitors (`src/gescrtl/platform/settings_window.py`). Done when: on one monitor, behaviour is unchanged (existing `win_input` corner smoke still works).
- [ ] T036 [US4] (user) SC-009 on two monitors at mixed scaling, plus unplug/replug while running. Done when: results are noted for the report.

---

## Phase 7: User Story 5 – Teach GesCRTL my own gesture (P4)

**Goal**: Enroll, assign, recognize, retrain, disable, and delete custom shapes and movements.

**Independent Test**: Enroll a gesture, assign play/pause, trigger it 20 times, replay 10 minutes
of non-control recordings, then disable and delete it.

### Tests

- [X] T037 [P] [US5] `tests/unit/test_custom_match.py`: shape descriptor invariance (scale, in-plane rotation, left/right), NN threshold, DTW on identical/time-stretched/different paths, segmenter start/end/timeout. Done when: tests exist and fail.
- [X] T038 [P] [US5] `tests/replay/test_us5_custom_shape.py` and `tests/replay/test_us5_custom_move.py`: per the plan rows (enrollment refusals, hold/fire once/cooldown/re-arm, cursor freeze for shapes, cursor keeps moving for movements in Pointer, never while busy, swipe-like refused, discarded during pinch/scroll/swipe, mode filter, global off switch). Done when: tests exist and fail.
- [X] T039 [P] [US5] `tests/unit/test_custom_store.py`: round trip, atomic write, damaged file disables without overwrite, stored keys contain no image data. Done when: tests exist and fail.

### Implementation

- [X] T040 [US5] Create `src/gescrtl/core/custom.py` (D9): descriptors, NN, DTW, segmenter, `CustomRecognizer` (shapes + movements, cooldowns, busy gating), enrollment session (setup session: takes, live checks, refusals, thresholds), `CUSTOM_KINDS_AVAILABLE`. Done when: T037 passes.
- [X] T041 [US5] Wire the recognizer into `src/gescrtl/core/engine.py` (D9 order: globals → custom shape → controller; movement in parallel; swipe first in Presentation); `CustomFired` + mapped action via `mapping.resolve`. Done when: T038 passes and all spec 002/003 tests still pass with custom gestures off and on (none enrolled).
- [X] T042 [US5] Create `src/gescrtl/settings/custom_store.py` (D9 file format, atomic write, damaged-file handling); load in `src/gescrtl/app.py` and pass gestures to the engine. Done when: T039 passes.
- [X] T043 [US5] Custom gestures tab in `src/gescrtl/platform/settings_window.py` (list, record shape/movement, live feedback from `SetupView`, assign action and modes, retrain, enable/disable, delete; kinds hidden if not in `CUSTOM_KINDS_AVAILABLE`); "Disable custom gestures" in `src/gescrtl/platform/tray.py`. Done when: a gesture can be enrolled and deleted from the window (manual check in T045).
- [X] T044 [P] [US5] Write `docs/adr/0008-custom-gesture-matching.md` (NN + DTW, descriptors, thresholds, the per-kind gate). Done when: the ADR follows the existing format.
- [ ] T045 [US5] (user) Record R4 `custom_shapes`, `custom_moves`, R5 `all_builtins`; measure SC-007/SC-008 per kind; set `CUSTOM_KINDS_AVAILABLE` from the results; add the fixtures to `tests/replay/test_fixture_regressions.py`. Done when: the decision per kind is recorded and the fixtures replay as expected.

---

## Phase 8: Polish & Cross-Cutting

- [X] T046 [P] Extend `src/gescrtl/tools/bench.py`: count `KeyStroke`, `CustomFired`, dwell clicks; time the custom matcher per frame (p95). Done when: `--replay` prints the new counts.
- [X] T047 [P] Update `docs/interaction/gesture-vocabulary.md`, `interaction-model.md`, `safety-policy.md`, `feedback-hud.md` (Keyboard Mode, second hand, dwell, SETUP, custom gestures, remapping). Done when: the conflict check tables include Keyboard Mode and custom gestures.
- [X] T048 [P] Update `docs/product/known-limitations.md` and `README.md` (FR-030): remove "primary monitor only" and "Keyboard: Later"; add typing speed (measured), monitor aspect note, custom gesture limits, US layout display. Done when: no statement contradicts the new behaviour.
- [X] T049 Quality gate: `ruff check .`, `mypy src/gescrtl/core`, `pytest`. Done when: all pass.
- [ ] T050 (user) Validation session (plan "Validation"): US1–US5 scenarios, SC-001–SC-009, non-US input language, Start with Windows, performance gate. Write `docs/measurements/phase5-7-8-9-report.md` with a short retrospective. Done when: the report exists with measured numbers.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. T001 (constitution) blocks T011, T015, and T016 (second hand).
- **US1** (P1): needs Phase 2 only. MVP.
- **US2** (P2): needs Phase 2; the Gestures tab needs T022. Independent of US1.
- **US3** (P2): needs Phase 2 (`SETUP`, `DwellSelector`); the "Calibrate…" button in the window needs T024.
- **US4** (P3): needs Phase 2 only; the Displays tab needs T024.
- **US5** (P4): needs T008 (`SETUP`), T022 (mapping), T024 (window). Last, because it may end up gated off.
- Polish after the stories that are shipped.

## Parallel Opportunities

- Phase 1: T002 and T003 together, after T001.
- Each story's test tasks ([P]) together, before its implementation.
- US1: T013 alongside T015 (different files). US2 (T022–T023) and US4 (T034) can run alongside US1 once Phase 2 is done.
- US5: T044 at any time.
- Polish: T046–T048 together.

## Implementation Strategy

1. Phases 1–2, then **US1** → stop and check Keyboard Mode (MVP).
2. **US2** and **US3** (settings window first, then calibration and dwell).
3. **US4** (needs a second monitor for T036).
4. **US5** last; ship each kind only if T045 meets SC-007/SC-008.
5. Polish and the single validation session (T050).
