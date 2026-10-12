# Tasks: Mode System, Presentation Mode, and Media/System Controls

**Input**: `specs/003-modes-presentation-media/plan.md` (decisions D1–D13), `spec.md` (US1–US4, FR-001–FR-025)

**Tests**: Required (constitution IV, FR-019). In each story, write the tests first and confirm
they fail before implementing.

**Format**: `- [ ] T### [P?] [US?] What, where — done when`.

Conventions:
- "Dn" refers to a decision in plan.md. Read it before starting the task.
- Core code (`src/gescrtl/core/`) MUST NOT import cv2, mediapipe, PySide6, ctypes, comtypes,
  pycaw, or `time`. `tests/test_architecture.py` enforces this.
- Never import from `spikes/`.
- Synthetic replay scripts use `tests/support/hands.py` (`Script`, `run`, `resume_script`). Every
  new replay test also runs its script twice on fresh engines and asserts identical events
  (determinism, SC-008).
- Outside Pointer Mode's normal pointing, the core MUST NOT emit `MoveCursor` (D3). Assert this
  in every overlay, Presentation, and Media test.
- `(user)` tasks need the camera or a human. Stop and ask the user to run them, giving exact
  PowerShell commands. Don't invent their results.
- Pointer Mode behaviour from spec 002 must not change. The full existing test suite stays green
  after every phase.

---

## Phase 1: Setup

- [X] T001 Add `pycaw` (it brings `comtypes`) to `dependencies` in `pyproject.toml`. Done when: `pip install -e ".[dev]"` succeeds and `python -c "import pycaw, comtypes"` works.
- [X] T002 [P] Extend `tests/support/hands.py`:
  - `pose()` builds `Pose.G9_CALL_ME` (index, middle, ring curled; pinky extended; thumb out, tip > 0.8 hand sizes from the index tip).
  - `pose()` builds `Pose.G10_INDEX_POINT` (index extended; middle, ring, pinky curled; thumb tucked).
  - `pose()` gets a new keyword `pinky_curl: float | None = None` that overrides the pinky's tip/pip ratio. `pose(Pose.G4_THUMBS_UP, at, pinky_curl=1.10)` is the "loose pinky" scroll (between `CURLED_MAX` 1.05 and `EXTENDED_MIN` 1.15). `Script.hold`/`Script.move` pass it through.
  - `G4` with a negative `thumb_tilt_deg` gives thumbs-down.
  - Done when: `features.compute()` on each built hand gives the intended curl/thumb values (quick assert in `tests/unit/test_poses.py`).

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Add to `src/gescrtl/core/types.py` (D1, D12):
  - Enums: `Mode` (POINTER, PRESENTATION, MEDIA, KEYBOARD), `OverlayKind` (MODE_MENU, LEVELS, MEDIA), `PointerStyle` (SELECT, LASER), `Action` (SLIDE_NEXT, SLIDE_PREV, SHOW_START, SHOW_END, PLAY_PAUSE, NEXT_TRACK, PREV_TRACK, MUTE, SCREENSHOT, APP_SWITCH), `Level` (VOLUME, BRIGHTNESS).
  - `Pose.G9_CALL_ME` and `Pose.G10_INDEX_POINT`.
  - `Sub.MODE_MENU` and `Sub.LEVEL_PANEL`.
  - `Command.SET_MODE`.
  - Events: `ModeChanged(mode)`, `OverlayShown(kind, highlight="", pending="")`, `OverlayHidden()`, `OverlayPointer(nx, ny, style)`, `OverlayPointerHidden()`, `SystemAction(action)`, `LevelStep(level, delta: int)`.
  - Done when: mypy strict passes on core.
- [X] T004 [P] Add every D13 setting with the plan's defaults to `CoreConfig` in `src/gescrtl/core/config.py` **and** to `Settings` in `src/gescrtl/settings/store.py`:
  - Give each a sensible `Field(ge=, le=)` range, e.g. ms 50–10000, `swipe_min_frames` 2–10, `swipe_min_dist` 0.3–5.0, `level_step` 1–10, `target_margin` 0.0–0.05, `thumb_dir_enter_deg` 20–80, `thumb_dir_exit_deg` 10–75.
  - A model validator requires `thumb_dir_enter_deg > thumb_dir_exit_deg`, like the existing pinch enter/release rule.
  - Done when: `tests/unit/test_settings.py` has a case showing the new defaults round-trip and an out-of-range value falls back with a warning.
- [X] T005 [P] Create `src/gescrtl/core/layout.py` (D3):
  - A frozen `Rect(x, y, w, h)` (normalized) with `contains(nx, ny, margin)`.
  - Constants `MODE_MENU_ITEMS` (Pointer, Keyboard, Presentation, Media in a row, each 0.18 × 0.16, centred), `LEVEL_SLIDERS` (Volume, Brightness, each 0.10 × 0.45), `MEDIA_TARGETS` (10 ids in 2 rows of 5, each 0.15 × 0.14, order from D7).
  - `hit(items, nx, ny, margin, current: str | None) -> str | None` with hysteresis (plan D3). The `current` id stays while the point is anywhere inside its rect (margin 0). A new id is returned only if the point is inside that rect by ≥ margin. Otherwise None.
  - Done when: T006 passes.
- [X] T006 [P] Write `tests/unit/test_layout.py`:
  - Every rect is ≥ 48 px on both sides at 1280×720, 1920×1080, and 2560×1440.
  - No two rects in a group overlap.
  - `hit` with `current=None` returns None on edges, in gaps, and outside.
  - With `current` set, an edge point inside the current rect keeps it (no flicker), and leaving the rect clears it.
- [X] T007 Create `src/gescrtl/core/select.py` (D4): a `PinchSelector` that is fed `(pointed_id, raw, stable, t_ns)` every frame. `pointed_id` comes from `layout.hit(..., current=<last pointed>)`, so pointing has hysteresis.
  - It remembers the pointed id from `pinch_lookback_frames` ago.
  - It returns the selected id once when a *stable* G2 begins, using the id pointed at the first raw-G2 frame minus the lookback.
  - It never returns again until the raw pose leaves G2 and `action_cooldown_ms` has passed for that id.
  - It exposes `held_id` (the id while the pinch stays held on it) for repeat actions.
  - Done when: unit tests in `tests/unit/test_select.py` cover the single fire, a one-frame pinch ignored, the cooldown, an edge or gap giving None, and sliding during the pinch onset still picking the original target.
- [X] T008 Add G9 and G10 to `PoseClassifier.classify` in `src/gescrtl/core/poses.py`, in the order from D9. Done when: the new cases in `tests/unit/test_poses.py` pass:
  - G9 is recognized.
  - G10 is recognized.
  - The loose-pinky thumb-out pose stays G4, never G9.
  - G7 is still G7.
  - All existing pose tests still pass.
- [X] T009 Add `Pose.G10_INDEX_POINT` to `_MOVE_POSES` in `src/gescrtl/core/pointer.py`. Done when: a test in `tests/replay/test_us1_pointer_move.py` shows G10 moves the cursor like G1.
- [X] T010 Create `src/gescrtl/core/modes.py` with a `ModeController` Protocol (`update(feats, raw, stable, t_ns) -> list[Event]`, `reset() -> list[Event]`, `busy: bool`) and `PointerController`, which wraps the existing `Pointer`. `busy` = pointer phase is not MOVE.
  - Refactor `Engine.step` in `src/gescrtl/core/engine.py` to the dispatch shape of D2, with only Pointer registered.
  - Keep `_fist_held` Pointer-only.
  - G7 and G9 still do nothing yet.
  - Done when: the full existing test suite passes unchanged.
- [X] T011 [P] Add `system_action(action: Action) -> bool` (False = unsupported in the foreground app) to `InputBackend` in `src/gescrtl/platform/interfaces.py`. Implement it in `src/gescrtl/platform/win_input.py`:
  - Use `KEYBDINPUT`; send all downs, then ups in reverse, in one `SendInput` call.
  - Keys: `VK_MEDIA_PLAY_PAUSE` 0xB3, `VK_MEDIA_NEXT_TRACK` 0xB0, `VK_MEDIA_PREV_TRACK` 0xB1, `VK_VOLUME_MUTE` 0xAD, Win+PrtSc for SCREENSHOT, Alt+Tab for APP_SWITCH.
  - Slide/show actions call `presenter_keys.keys_for(action)` (T029). Until then, use Right/Left for slides and return False for show.
  - Return False when `keys_for` returns None; otherwise True.
  - `release_all` also sends key-up for any modifier this backend pressed.
  - Add the method to `NullInput` in `src/gescrtl/tools/bench.py` and to the fake backends in tests.
  - Done when: `tests/unit/test_worker.py` still passes and a new unit test checks the INPUT sequence built for Alt+Tab, without sending.
- [X] T012 [P] Create `src/gescrtl/platform/overlays.py` with a base `OverlayWindow` that copies `CursorCue`'s frameless, click-through, non-activating window flags and covers the primary monitor. Add:
  - `SelectRing`: 28 px ring for `OverlayPointer(SELECT)`.
  - `LaserDot`: red 16 px dot with a glow for `OverlayPointer(LASER)`.
  - Both hide on `OverlayPointerHidden` or any non-Active `StateChanged`.
  - Done when: `tests/unit/test_ui_smoke.py` constructs both offscreen.
- [X] T013 Route the new events:
  - In `src/gescrtl/app.py` `Worker._emit_all`, send `SystemAction` → `input.system_action`. `LevelStep` → `levels.step` comes in T037; leave a stub that logs for now.
  - When `system_action` returns False, call `self.ui(Warning("Start/end not supported in this app"))`.
  - Wrap each call in try/except with a log line; never raise.
  - In `src/gescrtl/platform/hud.py` `Hud.handle`, route `OverlayPointer*` to the T012 widgets and `ModeChanged` to the pill.
  - Done when: `tests/unit/test_worker.py` has a case showing a `SystemAction` event reaches the fake backend, a False return produces the `Warning`, and an exception in it is logged, not raised.
- [X] T014 [P] In `src/gescrtl/tools/bench.py`, count `ModeChanged`, `OverlayShown`, `SystemAction`, and `LevelStep` per recording. All four must be 0 for "must be quiet" recordings (SC-002). Done when: `tests/unit/test_bench.py` covers it.

**Checkpoint**: everything from spec 002 still passes; the new types, layout, selector and poses exist.

---

## Phase 3: User Story 1 – Mode menu and switching (P1) 🎯 MVP

**Goal**: open the menu with G7, choose with a pinch, cancel with a fist or timeout, switch from the tray; the mode persists and the indicator shows it.

**Independent test**: replay scripts open, select, and cancel the menu; check the mode, indicator text, hints, and that no input is sent while it is open.

- [X] T015 [P] [US1] Write `tests/replay/test_us1_mode_menu.py` covering US1 scenarios 1–6 and the edge cases. Each must emit `ReleaseAll` on open and no `MoveCursor`/`Click`/`ButtonDown`/`Scroll`/`SystemAction` while the menu is open:
  - G7 held 0.8 s opens it (`OverlayShown(MODE_MENU)`); 0.7 s doesn't.
  - Pointing highlights an item.
  - A pinch on Presentation → `ModeChanged(PRESENTATION)` plus Presentation hints.
  - A fist → closed and the mode is unchanged; so is a 5 s timeout.
  - A one-frame pinch or fist does nothing.
  - Keyboard can't be chosen.
  - Hand loss, pause gesture, and `Command.EMERGENCY_STOP` each close it.
  - G7 during a drag is ignored.
  - A second hand (`others=`) pinching or making a fist inside the menu changes nothing.
- [X] T016 [P] [US1] Write `tests/replay/test_us1_mode_persistence.py`:
  - The mode is kept through Paused, Tracking Lost, and emergency stop.
  - A new `Engine()` starts in Pointer.
  - `resume` shows the current mode's hints, never another mode's.
  - `hand_back` shows none.
  - The pill text is the mode name.
- [X] T017 [P] [US1] Write `tests/replay/test_us1_tray_mode.py`:
  - `Command.SET_MODE` "MEDIA" in Active → ReleaseAll, any open overlay closed, `ModeChanged`, hints.
  - In Paused → mode set, text stays "Paused", the new mode is used on resume.
  - "KEYBOARD", "BOGUS", and the Inactive state → no events.
  - A JSONL round trip of a `SET_MODE` command replays identically (use `gescrtl.recording.jsonl`).
- [X] T018 [US1] Implement D1 in `src/gescrtl/core/state_machine.py`:
  - `mode` attribute.
  - `open_menu`, `confirm_mode`, `cancel_menu`, `set_mode_command`.
  - Mode-aware HUD text, including "· Hold" when clutched.
  - `clutch_start` emits `CueChanged(CLUTCH)` only in Pointer Mode (plan D2 step 1).
  - `MODE_HINTS` dict holding the three hint tuples from D11 (Keyboard has none).
  - The overlay is closed on every exit from Active (the existing `_go` paths); `SET_MODE` is handled in `on_command`.
  - Done when: T016 and T017 pass.
- [X] T019 [US1] Create `src/gescrtl/core/mode_menu.py` (D5): uses `layout.MODE_MENU_ITEMS`, its own One Euro on the anchor with the Pointer mapping, `PinchSelector`, `OverlayPointer(SELECT)`, `OverlayShown` when the highlight changes, the fist cancel, and the `menu_timeout_ms` timeout. Done when: its unit-level behaviour is exercised by T015.
- [X] T020 [US1] Wire the menu into `src/gescrtl/core/engine.py` (D2):
  - G7 stable for `menu_hold_ms`, while Normal and the controller isn't `busy` → `open_menu`.
  - `MODE_MENU` → `ModeMenu.update`.
  - Confirm switches the current controller.
  - `_after_transition` resets the menu.
  - Done when: T015 passes and the full suite is green.
- [X] T021 [P] [US1] Add `ModeMenuView` to `src/gescrtl/platform/overlays.py`:
  - Draws `MODE_MENU_ITEMS` in pixels from the primary rect.
  - The current mode is filled, the pointed item outlined, Keyboard greyed with "Later".
  - Footer: "Pinch to choose · Fist to cancel".
  - Shown on `OverlayShown(MODE_MENU)`, hidden on `OverlayHidden`.
  - Route it in `hud.py`.
  - Done when: an offscreen smoke test constructs it and handles both events.
- [X] T022 [P] [US1] In `src/gescrtl/platform/tray.py`, add a "Mode" submenu with exclusive checkable actions Pointer, Presentation, Media/System, and Keyboard (disabled).
  - `handle(ModeChanged)` checks the matching item.
  - A new constructor callback `on_mode(Mode)`; app.py wires it to `worker.post(Command.SET_MODE, mode.name)`.
  - Done when: `tests/unit/test_ui_smoke.py` checks the submenu exists and that a `ModeChanged` event moves the check.

**Checkpoint**: modes can be switched by gesture and by tray; Presentation and Media are still empty modes.

---

## Phase 4: User Story 2 – Presentation Mode (P2)

**Goal**: open-hand swipe changes slides, the index finger shows a stable laser dot, thumbs-up/down starts and ends the show.

**Independent test**: replay scripts in Presentation produce exactly one `SystemAction` per swipe/hold and laser events only in G10.

- [X] T023 [P] [US2] Write `tests/replay/test_us2_swipe.py`. Use `Script.move` with G6 or G8 for an open hand; position is the palm anchor.
  - A fast move right of ≥ 1.5 hand sizes in 250 ms → one `SLIDE_NEXT`; left → `SLIDE_PREV`.
  - Too slow (1500 ms), too short, or diagonal (dy = dx) → nothing.
  - An immediate return stroke → nothing.
  - A second swipe within 600 ms → nothing; after re-arming → fires.
  - The same swipe at `fps=10` → exactly one.
  - A no-hand frame in the middle → nothing.
  - A fast G10 move → nothing.
  - A flat-hand swipe while clutched → fires and doesn't pause.
  - A flat hand held still 1.5 s still pauses.
  - Clutch in Presentation emits no `CueChanged(CLUTCH)`, and the pill reads "Presentation · Hold".
  - A second hand (`others=`) swiping never fires.
- [X] T024 [P] [US2] Write `tests/replay/test_us2_laser.py`:
  - G10 → `OverlayPointer(LASER)`; G1 or open hand → none.
  - G10 → G1 for 200 ms → G10: no `OverlayPointerHidden` and no jump > 0.02.
  - G10 → G1 for 400 ms → hidden.
  - Pause, loss, and a mode change → hidden at once.
  - Never `MoveCursor`/`Click`/`Scroll`.
  - At rest with ±0.002 landmark noise, laser output stays within 12 px on 1920×1080 over 2 s (SC-004 proxy).
- [X] T025 [P] [US2] Write `tests/replay/test_us2_show.py`:
  - G4 with tilt +70 held 1 s → one `SHOW_START`; holding 3 s → still one.
  - Tilt −70 → `SHOW_END`; tilt +20 → nothing.
  - Re-trigger needs another pose plus `show_cooldown_ms`.
  - Hysteresis: a tilt reaching 55° then hovering at 40–48° for 1 s still fires `SHOW_START` (stays "up" above the 35° exit). A tilt hovering at 45–49° from the start never fires. A hold that dips below 35° restarts the 1 s timer.
- [X] T026 [US2] Create `src/gescrtl/core/swipe.py` `SwipeDetector` exactly per D6. Window of (t_ns, anchor_x, anchor_y, size, open) samples; it fires `Action` or None. Cooldown, return block, and re-arm speed come from config. Done when: the swipe-only cases of T023 pass in a unit test.
- [X] T027 [US2] Create `src/gescrtl/core/presentation.py` `PresentationController` (D6): laser with its own One Euro (`laser_min_cutoff`, `laser_beta`) and grace timer, the swipe detector, show start/end on G4 tilt, `busy`. Done when: T023–T025 pass after T028.
- [X] T028 [US2] Register `PresentationController` in `src/gescrtl/core/engine.py`. Feed the swipe detector in `CLUTCHED` too when the mode is Presentation (D2 step 1). Done when: T023–T025 and the full suite pass.
- [X] T029 [P] [US2] Create `src/gescrtl/platform/presenter_keys.py` with `keys_for(action) -> list[int] | None`:
  - Read the foreground exe and title via `GetForegroundWindow`, `GetWindowThreadProcessId`, `QueryFullProcessImageNameW`, and `GetWindowTextW`.
  - Map keys using the D10 table.
  - Return None for unsupported start/end. `win_input.system_action` then returns False, and the worker shows the `Warning` (T013).
  - Done when: a unit test with the exe/title lookup injected covers all three rows.
- [X] T030 [P] [US2] Route `OverlayPointer(LASER)` to `LaserDot` in `src/gescrtl/platform/hud.py`, already built in T012. Check it stays visible above a full-screen PowerPoint show (`WindowStaysOnTopHint`; re-raise on show). Done when: smoke test passes; the visual check is in T031.
- [-] T031 [US2] (user, SKIPPED by owner: Presentation Mode stays as built) Record R1 and R2 per plan "Recordings to make":
  - `python -m gescrtl --record swipes_near`, `--record swipes_far`, `--record swipes_dim`, `--record presenting`
  - Note the ground-truth swipe counts.
- [-] T032 [US2] (SKIPPED by owner: no Presentation tuning, defaults stay) Replay R1/R2 and tune the swipe, laser, and show defaults in `core/config.py` + `settings/store.py` until counts match ground truth with 0 extra or wrong-direction swipes. Copy the chosen recordings to `tests/fixtures/` with `.expect.json` and extend `tests/replay/test_fixture_regressions.py`. Done when: fixture tests pass.

**Checkpoint**: Presentation Mode works end to end in replay.

---

## Phase 5: User Story 4 – Volume and brightness from every mode (P2)

**Goal**: "call me" opens the level panel in any mode; pinch-drag on a slider changes volume or brightness in bounded steps.

**Independent test**: replay in Pointer, Presentation, and Media opens the panel and produces bounded `LevelStep` events, with no pointer input.

- [X] T033 [P] [US4] Write `tests/replay/test_us4_level_panel.py`:
  - G9 held 0.5 s in each of Pointer, Presentation, and Media → `OverlayShown(LEVELS)` + ReleaseAll; 0.4 s → nothing.
  - Pinch on Volume, move up by half the slider height → total `+50 ± 2` in `LevelStep(VOLUME, +2)` steps. The rate never exceeds `level_max_rate` (check timestamps).
  - Move down → negative steps; release → steps stop.
  - Pinch on Brightness → `Level.BRIGHTNESS`.
  - A fist → closed; 5 s idle → closed.
  - Loss, pause, G7, and emergency stop → closed.
  - No `MoveCursor`/`Click`/`Scroll`/`SystemAction` while open.
  - G9 during a scroll → ignored.
  - The loose-pinky scroll never opens the panel.
- [X] T034 [US4] Create `src/gescrtl/core/level_panel.py` (D8): `PinchSelector` on `LEVEL_SLIDERS`, relative drag accumulator, rate cap with dt capped at 100 ms, fist and timeout close, `OverlayPointer(SELECT)`. Done when: T033 passes after T035.
- [X] T035 [US4] In `src/gescrtl/core/state_machine.py` add `open_panel`/`close_panel`. In `src/gescrtl/core/engine.py`, G9 stable for `panel_hold_ms`, while Normal and not busy → open; `LEVEL_PANEL` → `LevelPanel.update`. Done when: T033 and the full suite pass.
- [X] T036 [P] [US4] Add a `LevelBackend` Protocol (`step(level, delta)`, `read(level) -> int | None`) in `src/gescrtl/platform/interfaces.py`. Create `src/gescrtl/platform/levels.py` `WinLevels` (D10):
  - One daemon thread with `comtypes.CoInitialize()` and a queue that coalesces deltas per level.
  - Volume uses pycaw `AudioUtilities.GetSpeakers()` → `IAudioEndpointVolume`, `GetMasterVolumeLevelScalar`/`SetMasterVolumeLevelScalar`, clamped 0..1.
  - Brightness uses WMI through `comtypes.client.CoGetObject("winmgmts:root\\WMI")`: `WmiMonitorBrightness.CurrentBrightness` to read, `WmiMonitorBrightnessMethods.WmiSetBrightness(1, value)` to set, clamped 0..100. Any failure → brightness unavailable.
  - `on_level(level, value_or_None)` callback after each apply and once at start.
  - Done when: `python -c "from gescrtl.platform.levels import WinLevels; ..."` reads both levels on the user's laptop (part of T040) and a unit test with fake COM objects covers coalescing and the unavailable path.
- [X] T037 [US4] Wire `WinLevels` into `src/gescrtl/app.py`:
  - Build it in `main`; `Worker._emit_all` sends `LevelStep` → `levels.step`.
  - Send `on_level` to the HUD through the Qt bridge.
  - Stop the thread on exit.
  - Done when: `tests/unit/test_worker.py` shows `LevelStep` reaches a fake `LevelBackend`.
- [X] T038 [P] [US4] Add `LevelPanelView` to `src/gescrtl/platform/overlays.py`:
  - Two vertical sliders from `LEVEL_SLIDERS`, filled to the last `on_level` value with a percentage label.
  - "Brightness unavailable" when the value is None.
  - The pointed slider is outlined. Footer: "Pinch and move · Fist to close".
  - Route it in `hud.py`.
  - Done when: an offscreen smoke test shows both values and the unavailable state.
- [-] T039 (SKIPPED by owner) [US4] (user) Record R3: `python -m gescrtl --record callme_vs_scroll`. Replay it, tune `panel_hold_ms` only if needed, and add it as a fixture: the panel opens only on the real "call me" holds, never during scrolls.
- [X] T040 [US4] (user, confirmed working by owner) Live check: the panel in Pointer Mode changes the real volume and built-in display brightness, and the HUD shows both levels.

**Checkpoint**: level controls work in every mode.

---

## Phase 6: User Story 3 – Media/System Mode (P3)

**Goal**: a 10-target grid; point and pinch to run media and system actions, repeat volume/brightness while held, confirm screenshot and app switch.

**Independent test**: replay in Media produces exactly the selected action once, repeats while held, and needs a second confirmation for screenshot and app switch.

- [X] T041 [P] [US3] Write `tests/replay/test_us3_media.py`:
  - Entering Media → `OverlayShown(MEDIA)`.
  - A pinch on each of play/pause, previous, next, mute → exactly one matching `SystemAction`.
  - Holding the pinch on volume+ for 1 s → `LevelStep(VOLUME, +level_step)` about every 150 ms (6–7 events); same for brightness−.
  - Sliding off the target stops the repeats.
  - Screenshot: one pinch → `pending="screenshot"`, no action; a second pinch within 3 s → `SCREENSHOT`. A fist cancels; after 3 s it expires; pinching another target cancels it.
  - Same for app switch.
  - Pointing at an edge or gap and pinching → nothing.
  - Cooldown prevents a double fire.
  - Hand loss, pause, or a mode change → no pending action and no held input.
- [X] T042 [US3] Create `src/gescrtl/core/media.py` `MediaController` (D7): `PinchSelector` on `MEDIA_TARGETS`, `OverlayPointer(SELECT)`, a repeat timer using `held_id`, a pending confirmation with `confirm_window_ms`, `busy` while pending or repeating. Register it in `src/gescrtl/core/engine.py`. Done when: T041 and the full suite pass.
- [X] T043 [P] [US3] Add `MediaGridView` to `src/gescrtl/platform/overlays.py`:
  - Draws `MEDIA_TARGETS` with a text label and a simple glyph for each.
  - The pointed target is outlined; a pending target is highlighted with "Pinch again to confirm".
  - Shown while `OverlayShown(MEDIA)` is current.
  - Route it in `hud.py`.
  - Done when: an offscreen smoke test passes.

**Checkpoint**: all four stories work in replay.

---

## Phase 7: Polish & Cross-Cutting

- [X] T044 [P] Update `docs/interaction/gesture-vocabulary.md`:
  - Add G9 (global, level panel), G10 (Presentation pointer), thumbs-up/down use of G4 in Presentation, and the open-hand swipe motion.
  - Give each one Scope and Min hold.
  - Add per-mode conflict tables (Presentation, Media, LevelPanel, ModeMenu) and the global vs mode-specific list (FR-006).
- [X] T045 [P] Update `docs/interaction/interaction-model.md` (ModeMenuOpen implemented, LevelPanel sub-state, SET_MODE command, mode persistence) and `docs/interaction/feedback-hud.md` (menu, panel, grid layouts; hints per mode from D11).
- [X] T046 [P] Update `docs/interaction/safety-policy.md` with every D13 value (tuned values from T032/T039). Update `docs/product/known-limitations.md`:
  - Brightness covers the built-in display only.
  - Keys go to the foreground app.
  - Supported presenter apps and keys; Edge PDF has slide changes only.
  - Measured distance range (from T049).
  - Swipes in dim light.
  - The screenshot action saves a file through Windows (Win+PrtSc).
- [X] T047 [P] Update `README.md`: modes, the gesture table per mode, the tray Mode menu, and a note that the screenshot action (Win+PrtSc) saves to `Pictures\Screenshots` (an OS screen capture, never a camera image).
- [X] T047a [P] Write `docs/adr/0006-system-levels-pycaw-wmi.md` in the same format as `docs/adr/0005-pointer-mapping.md`:
  - Decision: volume via pycaw/Core Audio, brightness via WMI through comtypes, built-in display only.
  - Alternatives rejected: volume media keys (blind 2% steps, can't read the level), a DDC/CI library for external monitors (extra dependency, unreliable across monitors), PowerShell CIM calls (process spawn per step is too slow).
  - Consequences: new dependency; brightness is unavailable on desktops and external monitors.
- [-] T048 (SKIPPED by owner) (user) Record R4: `python -m gescrtl --record idle_modes`, about 5 min idle, typing, and talking, spread across Pointer, Presentation, and Media. Then `python -m gescrtl.tools.bench --replay recordings\*.jsonl`. Done when: R4 and the existing spec 002 quiet recordings show 0 `ModeChanged`/`OverlayShown`/`SystemAction`/`LevelStep` (SC-002). Add R4 as a fixture.
- [-] T049 (SKIPPED by owner) (user) Manual session per plan "Validation":
  - US1–US4 scenarios, including the tray.
  - SC-001, SC-003 (PowerPoint, Google Slides; Edge PDF slide changes only), SC-004, SC-005, SC-006, SC-009.
  - SC-007: a short walkthrough where test users name the current mode and two of its gestures.
  - Performance gate: `python -m gescrtl.tools.bench --live 60` once in Pointer and once in Presentation with the laser on. p95 latency, FPS, and idle CPU must not be worse than the spec 002 numbers beyond the allowed margin.
  - FR-020 at 100/125/150%.
  - FR-011 distance measurement.
  - Verify the Google Slides start key and fix the `presenter_keys.py` table if needed.
  - Write `docs/measurements/phase3-4-6-report.md`, ending with a short retrospective (lessons, any constitution amendments needed).
- [X] T050 Quality gate: `ruff check .`, `ruff format --check .`, `mypy src/gescrtl/core`, `pytest`, all clean. Confirm `tests/test_architecture.py` passes with the new modules.

---

## Dependencies

- Phase 1 → Phase 2 → US1 (Phase 3). US1 is needed by all other stories, because modes must be reachable.
- After US1: US2 (Phase 4), US4 (Phase 5) and US3 (Phase 6) are independent of each other in the core. US3's volume/brightness targets reuse `LevelStep`, and only the *live* effect needs T036/T037. Recommended order: US2 → US4 → US3.
- Phase 7 docs can start once the stories they describe are done. T048 and T049 come last.
- Within a story: tests → core module → engine wiring → platform view → (user) recording and tuning.

## Parallel examples

- Phase 2: T004, T005+T006, T011, T012 and T014 touch different files and can run in parallel after T003.
- US1: T015, T016 and T017 (tests) in parallel; then T018 → T019 → T020; T021 and T022 in parallel with T019–T020.
- US2: T023–T025 in parallel; T026 → T027 → T028; T029 and T030 in parallel with the core work.
- US4: T033 and T036 in parallel; T038 alongside T034–T035.

## Implementation strategy

1. **MVP = Phase 1–3**: the mode system with menu and tray. Stop, run the full suite, and let the user try switching live.
2. Add US2, then the user records R1/R2 (T031) so tuning (T032) uses real data.
3. Add US4, then US3.
4. Polish, the R4 benchmark, and one manual session (T049).

Ask the user before committing; commit only when asked.
