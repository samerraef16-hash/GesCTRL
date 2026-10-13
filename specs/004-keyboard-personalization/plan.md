# Implementation Plan: Keyboard Mode, Personalization, Custom Gestures, and Calibration

**Branch**: `004-keyboard-personalization` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Scope**: Spec 004 (roadmap phases 5a + 7 + 8 + 9). Lean cycle: decisions are recorded inline
here. There are no separate research, data-model, contract, or quickstart files.

## Summary

Add **Keyboard Mode** as a fourth mode controller. A hand-mapped highlight moves over an
on-screen keyboard, and pinch, dwell, or a pinch by the user's other hand confirms the key. Make
everything adjustable from a **settings window** that edits the existing settings file and
**remaps** a small set of gesture slots to allowed actions. Add one new Active sub-state,
**`SETUP`**, which sends no input while it runs and serves both **guided calibration** and
**custom gesture enrollment**. Custom gestures are still shapes, matched by nearest neighbour on
normalized landmarks, or movements, matched by DTW (dynamic time warping, which compares paths
drawn at different speeds) on the palm trajectory. Change `MoveCursor` from "primary monitor" to
the **whole virtual desktop**, with points in gaps between monitors clamped to the nearest
monitor in the core. Overlays stay normalized to one chosen **overlay monitor**.

The only rule change is the Keyboard-Mode confirming hand. It needs a constitution amendment
(v1.2.0) and ADR 0007 **before** any code (spec FR-003b).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: existing (mediapipe, opencv-python, PySide6, pydantic v2, psutil,
pycaw/comtypes). No new dependency: DTW and nearest neighbour are small pure-Python functions
(about 30 lines each, inputs of at most 32×2 points and 10×5 templates). Monitor enumeration uses
`EnumDisplayMonitors` / `GetMonitorInfoW` through ctypes. Autostart uses `winreg` (stdlib).

**Storage**: `%APPDATA%\GesCRTL\settings.json` (extended: non-numeric fields, mappings,
calibration), new `%APPDATA%\GesCRTL\custom_gestures.json` (landmark features only),
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run\GesCRTL` (only when Start with Windows is on)

**Testing**: pytest (unit + landmark replay with `tests/support/hands.py`, extended with a second
hand and movement paths), Ruff, mypy `--strict` on `gescrtl.core`, `tests/test_architecture.py`
purity guard

**Target Platform**: Windows 11; one to three monitors at 100/125/150% scaling, mixed

**Project Type**: desktop app (tray + overlays + settings window), run from source

**Performance Goals**: unchanged (p95 internal delay ≤ 80 ms, idle CPU ≤ 5%). Custom-gesture
matching must add ≤ 2 ms p95 per frame: at most 10 gestures × 5 samples, and DTW runs only once
per completed movement segment, not on every frame.

**Constraints**: no network; no images written; ReleaseAll on every mode change, overlay
open/close, `SETUP` enter/exit; emergency stop ≤ 200 ms in every mode and during `SETUP`

**Scale/Scope**: about 8 new core modules, 5 new or extended platform modules, about 14 new test
files

All items are resolved. None are marked NEEDS CLARIFICATION.

## Constitution Check (pre- and post-design)

| Principle | How this plan complies | Status |
|---|---|---|
| I Safety | Keys need a stable pinch (or dwell with a stillness check) and a per-key cooldown. Modifiers are tracked by the input backend and released by `release_all`. `SETUP` sends nothing. Custom gestures need hold or completion, confidence, stable frames, and a cooldown, and never run while a built-in gesture is busy. **One-primary-hand rule: amended (D0)** so a second hand of the same person may confirm keys in Keyboard Mode only. | ✅ after D0 |
| II Reliability before breadth | Custom gestures are off by default. Each kind (shape, movement) is enabled in the release only if it meets SC-007/SC-008 (D9). Two-handed air typing (5b) stays out. | ✅ |
| III Visible state | Keyboard, calibration, and enrollment are shown by the HUD. The pill reads "Keyboard", "Setup". Custom gesture firings show their name. Mode change stays deliberate (menu or tray only; a custom gesture may *request* a mode change, which uses the tray path, D6). | ✅ |
| IV Testable core | Key selection, dwell, second-hand selection, calibration math, custom matching, monitor clamping, and mapping resolution are in `core/`. Monitor layout and setup commands are recorded commands, so replays are deterministic. | ✅ |
| V Privacy | Custom gestures and calibration store numbers only (landmark features, trajectories, thresholds). No frames are written. | ✅ |
| VI Configurable | Every new threshold is a `CoreConfig`/`Settings` field with a range. Safety controls stay non-configurable. | ✅ |
| VII Portability | Monitor enumeration, autostart, Unicode key injection, and the settings window are in `platform/`. | ✅ |
| Stack | No new dependency. ADR 0007 (two-hand confirm) is required; ADR 0008 (custom gesture matching) is recorded because it is a lasting recognition decision. | ✅ |

## Key Design Decisions

**D0 – Constitution amendment and ADR first.**
- Constitution v1.2.0, Principle I: "Only one controlling hand is tracked at a time … *Exception:
  in Keyboard Mode, a second hand that passes the same-person check may confirm the highlighted
  key; it never moves, selects, or triggers anything else.*" Version bump, plus a sync note in
  `CLAUDE.md` (non-negotiables line).
- `docs/adr/0007-keyboard-two-hand-confirm.md`: context, the same-person check (D3), the
  rejected alternatives (keep one hand only; full two-hand air typing), and the consequences
  (a bystander test fixture is mandatory).

**D1 – Settings model generalized.** `store.parse` currently rejects booleans and expects
numbers. It becomes type-aware: validate each field with its own `TypeAdapter`, and reject bool
only where the annotation is numeric. New field types:
- `confirm_method: Literal["pinch", "dwell"] = "pinch"`, `dwell_ms: int = 800 (300..3000)`,
  `dwell_still_dist: float = 0.015 (0.003..0.05)` (normalized screen distance)
- `pointer_dwell_click: bool = False` (FR-018, separate switch: dwell clicking while reading
  would be risky, so it is opt-in even when `confirm_method` is dwell)
- `two_hand_press: bool = True`, `second_hand_max_dist: float = 3.0 (1.0..6.0)` (hand sizes,
  wrist to wrist)
- `keyboard_position: Literal["bottom", "top"] = "bottom"`, `key_repeat_delay_ms: int = 500`,
  `key_repeat_ms: int = 100`, `key_cooldown_ms: int = 150`
- `active_center_x/y: float = 0.5 (0.2..0.8)` (calibration may move the region, D7)
- `overlay_monitor: str = ""` (device name; empty = primary)
- `start_with_windows: bool = False` (mirrored to the registry by the app, not by the core)
- `mappings: dict[str, str] = {}` (only overrides; D6)
- `custom_gestures_enabled: bool = False`, `custom_hold_ms: int = 600`,
  `custom_cooldown_ms: int = 1500`
- `calibrated_at: str = ""` (ISO date, shown in Settings; informational)

`Settings.to_core_config` passes the core-relevant fields. The platform-only fields
(`overlay_monitor`, `start_with_windows`, `calibrated_at`) are excluded from `CoreConfig`. Reset
rewrites defaults and sets `enabled=False` on every custom gesture (spec FR-013), without
deleting them.

**D2 – Keyboard Mode controller (`core/keyboard.py`).**
- **Layout** (`core/layout.py`): `keyboard_keys(position)` returns rects normalized to the
  overlay monitor. The keyboard spans the full width and 45% of the height, at the bottom or top.
  Rows: shortcut row (Copy, Paste, Cut, Undo, Redo, Select all, Alt+Tab, Win, Esc, Move), digits,
  QWERTY ×3 with punctuation, and a bottom row (Shift, Ctrl, Alt, Win, Space, ←, →, ↑, ↓,
  Backspace, Enter, Tab). Every key is ≥ 48 px at 1280×720 (layout test).
- **Hand mapping**: the hand's active region maps onto the **keyboard rect**, not the whole
  screen (FR-003). The same One Euro filter as the pointer is used, and no `MoveCursor` is ever
  emitted in Keyboard Mode (like Media).
- **Highlight**: `layout.hit()` with the existing hysteresis margin.
- **Confirm**: the existing `PinchSelector` (lookback, one fire per pinch, per-target cooldown
  `key_cooldown_ms`) or the new `DwellSelector` (D4), chosen by `confirm_method`, plus the
  second-hand pinch (D3).
- **Output**: a new event `KeyStroke(key: str, mods: frozenset[str])`. `key` is a printable
  character (`"a"`, `"A"`, `"?"`) or a named key (`"enter"`, `"backspace"`, `"left"`, …).
  Shortcuts are `KeyStroke("c", {"ctrl"})` etc.; Alt+Tab reuses `SystemAction(APP_SWITCH)`.
- **Modifiers**: one tap = one-shot, two taps within `double_click_ms` or a second tap while
  one-shot = locked, a tap while locked = off. Shift + letter becomes the upper-case character
  with no `"shift"` mod, so layout-independent Unicode sending works (D10).
- **Repeat**: Backspace and arrows repeat while the pinch is held (`PinchSelector.held_id`),
  after `key_repeat_delay_ms`, every `key_repeat_ms`. Dwell never repeats.
- **View event**: `KeyboardView(highlight, pressed, oneshot, locked, recent, position,
  dwell_progress)`. `recent` is the last 24 characters the core sent; Backspace removes one, and
  Enter/Tab/arrows/shortcuts clear it. It is a display aid, not a record of the app's text.
- **Move key** toggles `position` for the session; the setting keeps the default.
- `reset()` clears modifiers and emits `KeyboardView` with nothing pressed. The engine already
  emits `ReleaseAll` on every transition. `busy` is true while a pinch or dwell is in progress.
- `Mode.KEYBOARD` becomes selectable in the menu and the tray. Hints: "Point · Pinch to type ·
  Three fingers: menu".

**D3 – Second hand (`core/second_hand.py`), Keyboard Mode only.**
- The engine keeps `PrimaryHand.select` as is. In Keyboard Mode, Active · Normal, with
  `two_hand_press` on, it passes the *other* hands to `SecondHand.select(primary, others)`.
- A candidate is accepted when all of these hold:
  1. its handedness label differs from the primary's (mirroring flips both labels, so only
     "different" matters)
  2. score ≥ `min_confidence`
  3. wrist-to-wrist distance ≤ `second_hand_max_dist` × primary hand size
  4. it is not the hand `PrimaryHand` currently marks as a bystander
  5. it was continuously accepted for `stable_frames`
- Once accepted, it is followed by nearest-wrist tracking within `max_hand_jump`, like the
  primary hand.
- It has its own `PoseClassifier` + `PoseTracker`. Only `G2_PINCH_INDEX` onset matters. A stable
  pinch onset presses the key the primary highlighted `pinch_lookback_frames` ago. That reuses the
  `PinchSelector` history, fed with the primary's highlight and an external "pinch" signal.
- If both hands pinch within the same window, there is one press (the selector fires once per
  pinch episode, and an episode lasts while either hand pinches).
- Losing the second hand does nothing; losing the primary hand is the existing loss path. A
  bystander that fails the check is ignored (fixture: second person pinching nearby, SC-003).

**D4 – Dwell (`core/select.py`: `DwellSelector`, `core/pointer.py`: dwell click).**
- `DwellSelector.update(target, point, t_ns)`: fires once when the same target is pointed and
  the filtered point stays within `dwell_still_dist` for `dwell_ms`. It re-arms only after the
  target changes or the point moves more than 2 × `dwell_still_dist`. It emits `dwell_progress`
  (0..1) for the HUD ring.
- Used by Keyboard, the mode menu, the Media grid, and the level panel when
  `confirm_method == "dwell"`. The pinch still works there too.
- **Level panel in dwell mode**: dragging needs a held pinch, so the panel shows `+`/`−` targets
  under each slider (new `LEVEL_STEP_TARGETS`). Dwelling on one steps once, then repeats every
  `level_repeat_ms` while the point stays on it.
- **Pointer dwell click** (`pointer_dwell_click`): in Pointer Mode, a cursor kept still for
  `dwell_ms` gives one `Click(LEFT)`, with a ring cue (`CueKind.DWELL`, progress). It re-arms
  after a move of more than 2 × `dwell_still_dist`. Never during clutch, fist, scroll, or drag.

**D5 – Settings window (`platform/settings_window.py`).**
- A non-modal PySide6 dialog opened from the tray ("Settings…"). Tabs:
  - Pointer: range, center, smoothing, scroll
  - Timing: holds, cooldowns, confidence and stability
  - Keyboard & access: confirm method, dwell, pointer dwell click, two-hand press, keyboard
    position
  - Displays: overlay monitor, list of detected monitors
  - Gestures: remapping (D6)
  - Custom gestures (D9)
  - General: Start with Windows, Calibrate…, Reset to defaults
- Numeric controls are generated from `Settings.model_fields`: the label comes from a `title`
  added to each `Field`, the range from its `ge`/`le`. No hand-written form per field.
- **Apply** validates the whole form with `store.parse`; any warning is shown next to its field
  and nothing is saved. Then it saves and calls the existing reload path (`apply_settings`, which
  does `Engine.apply_config` + `ReleaseAll`). The file stays the single source; if it changes
  while the window is open (tray Reload), the window reloads its values.
- Reset asks for confirmation inside the window (no OS dialogs needed; the window is a normal
  app window).
- **Start with Windows** (`platform/win_autostart.py`): writes or removes
  `HKCU\…\Run\GesCRTL` = `"<sys.executable with pythonw.exe if present>" -m gescrtl`. The app
  already starts Paused (FR-014).

**D6 – Remapping (`core/mapping.py`).**
- **Slots**:
  - `presentation.swipe_right`, `presentation.swipe_left`, `presentation.thumb_up`,
    `presentation.thumb_down`
  - `media.t0` … `media.t9` (the ten grid positions)
  - `custom.<name>` (for each custom gesture)
- **Allowed actions**: every existing `Action` plus new shortcut actions (`COPY`, `PASTE`, `CUT`,
  `UNDO`, `REDO`, `SELECT_ALL`, `WIN`, `ESC`) and `MODE_POINTER`/`…_PRESENTATION`/`…_MEDIA`/
  `…_KEYBOARD`. A mode action goes through the same path as the tray `SET_MODE` (`ReleaseAll`,
  close overlays, hints), so it is deliberate (it needs the held gesture) and visible.
- **Excluded by construction**: clicks, pause, resume, emergency stop, mode menu, level panel,
  turn off. They are not in the enum the mapping accepts.
- `resolve(slot) -> AllowedAction` combines the defaults with `cfg.mappings`. An unknown slot or
  action produces a settings warning and keeps the default. Media grid labels come from the
  resolved actions, so the grid shows what each target does.
- Confirmation rules follow the *action*: screenshot and app switch keep their double-confirm on
  the grid wherever they are mapped. For custom gestures, the hold acts as the confirmation.

**D7 – Calibration (`core/calibration.py`), run in `Sub.SETUP`.**
- New `Command.START_SETUP` (arg `"calibration"` or `"enroll:<json spec>"`) and
  `Command.END_SETUP`. In `SETUP`, the engine still runs pause, emergency stop, and loss. It
  feeds features to the active session, emits `SetupView` events, and never emits
  `MoveCursor`/clicks/keys. Entering and leaving emit `ReleaseAll`.
- **Steps**:
  1. **Check**: over 2 s, measured FPS (from frame timestamps) ≥ 15 and hand size within
     [0.08, 0.35] of the image width. Otherwise `SetupView` shows "Too dark: N FPS" / "Move
     closer" / "Move back".
  2. **Reach**: for each corner in turn, the user holds the palm still (< `pause_still_dist`)
     for 1 s, and the anchor is recorded.
  3. **Pinch**: 2 s of open hand, then 5 pinches. The `pinch_index` ratios are recorded.
  4. **Review**.
- **Math**:
  - Region = bounding box of the four anchors, grown by 5% so the corners are reachable.
    `active_region` = max(width, height), clamped to 0.2..1.0; `active_center_x/y` = box center,
    clamped.
  - Pinch: `closed` = 90th percentile of the minimum ratio of each pinch, `open` = 10th
    percentile of open frames. `pinch_enter = closed + 0.35·(open−closed)`,
    `pinch_release = closed + 0.65·(open−closed)`, clamped to the settings ranges.
  - If `open − closed < 0.08` the step fails with "pinch and open hand look too similar, try a
    clearer pinch".
- **Pointer change**: the mapping uses `active_center_x/y` instead of the fixed 0.5 center
  (defaults keep today's behaviour).
- **End**: `SetupResult(values)` → the platform shows Keep / Discard. Keep merges the values
  into the settings and saves them. Cancel, pause, emergency stop, or loss for > 3 s →
  `SetupResult(None)`, and nothing changes.

**D8 – Multi-monitor (`core/displays.py`, `platform/displays.py`).**
- **Data**: `Display(x, y, w, h, primary, name)` in physical pixels from `EnumDisplayMonitors`
  (the process is already per-monitor-v2 aware). The platform sends the layout to the engine as
  `Command.DISPLAYS` (arg = JSON list), so replays are deterministic. It is sent at start and on
  `QGuiApplication.screenAdded/screenRemoved` and `QScreen.geometryChanged`, with a 2 s poll as a
  fallback (FR-021).
- **Core**: `MoveCursor(nx, ny)` now means 0..1 across the **virtual desktop bounding box**.
  `displays.clamp(nx, ny)` moves a point that falls in a gap to the nearest point of the nearest
  monitor (FR-020). Without a `DISPLAYS` command (old recordings), the box is the primary
  monitor, so old fixtures replay unchanged.
- **Aspect**: the active region keeps the camera aspect, so with side-by-side monitors one hand
  movement covers more pixels horizontally. Documented; calibration can enlarge the region.
- **Platform**: `WinInput.move` maps 0..1 over the virtual rect it already computes. Overlays
  (HUD, menu, panel, grid, keyboard, laser) are placed on the `overlay_monitor` geometry (falling
  back to the primary if it is missing). Their normalized coordinates keep meaning "0..1 of the
  overlay monitor", so the existing overlay code only changes its placement.
- **Pointer double-click snapping** (`double_click_dist`) is now relative to the desktop box:
  it is scaled by the box/primary width ratio so the distance in pixels stays the same.

**D9 – Custom gestures (`core/custom.py`, `settings/custom_store.py`).**
- **Shape descriptor**: the 21 landmarks minus the wrist, divided by hand size, rotated so wrist
  → middle MCP points up, and mirrored for one handedness so either hand matches. That gives 42
  numbers.
- **Shape matching**: per gesture, the minimum Euclidean distance to its samples. Accepted if
  below the gesture's threshold (at enrollment: 1.5 × the largest leave-one-out nearest
  distance, at least a floor of 0.15) **and** smaller than 0.8 × the distance to any other
  custom gesture's samples.
- **Shape firing**: the raw pose must be `G1_RELAXED` (anything that is a built-in pose never
  matches), the match must hold for `stable_frames`, then `custom_hold_ms` passes, then the
  action fires once. Re-arm after the match is lost; cooldown `custom_cooldown_ms`. Once
  matched, the cursor freezes like the fist, with `ReleaseAll` once (spec FR-025).
- **Movement descriptor**: the palm-anchor path relative to its start, divided by hand size,
  resampled to 32 points, plus the shape descriptor of the start frame (so a "wave with open
  hand" differs from a "wave with fist").
- **Segmentation**: a segment starts when anchor speed exceeds 1.0 hand sizes/s and ends when it
  drops below 0.4 for 150 ms, or after 2.5 s (then discarded). Pinch, drag, scroll, swipe, or any
  `busy` controller during a segment discards it (FR-025a).
- **Movement matching**: DTW distance between the segment and each template. Accepted if below
  the threshold (1.3 × the largest leave-one-out distance at enrollment), duration within
  0.5×..2× of the templates, and start-shape distance under the shape threshold. Fires once at
  the segment end; cooldown.
- **Presentation**: the swipe detector runs first; a segment during which a swipe fired is
  discarded. In Pointer Mode the cursor keeps moving during a movement gesture (clarified,
  accepted).
- **Enrollment** (in `SETUP`, from Settings):
  - Shape: 5 takes of 1 s each. Movement: 5 takes, each starting with a 3-2-1 countdown and
    ending with the segmentation rule.
  - Live checks: hand fully in view, confidence, takes consistent (each take within the
    provisional threshold of the others).
  - Refused if any take classifies as a built-in pose (shape), is detected as a swipe
    (movement), or is within threshold of another custom gesture. Reason shown, e.g. "looks like
    the three-finger menu gesture".
- **Storage**: `custom_gestures.json` `{version: 1, gestures: [{name, kind, action, modes,
  enabled, samples, threshold, created}]}`, written atomically. A damaged file disables custom
  gestures with a warning; the file is not overwritten.
- **Gate (FR-028)**: `custom_gestures_enabled` defaults to False. The release enables a kind only
  if the validation session meets SC-007/SC-008 for it. Otherwise that kind is hidden in Settings
  (`CUSTOM_KINDS_AVAILABLE` in `core/custom.py`) and listed in known limitations.
- **Engine order in Active · Normal**: global gestures → custom shape (if matched) → mode
  controller; the movement recognizer observes in parallel and fires only at segment end.
- **Tray**: "Disable custom gestures" toggles `custom_gestures_enabled` (FR-026).

**D10 – Platform keys (`platform/win_input.py`).**
- `key_stroke(key, mods)`:
  - Printable character with no mods (or only one-shot Shift folded in by the core): one
    `KEYEVENTF_UNICODE` down/up pair, so it works with any input language.
  - Named keys: their VK.
  - With Ctrl/Alt/Win: `VkKeyScanW(char)` gives the VK for the active layout. Mods down → key →
    mods up, in one `SendInput` call.
- Held modifiers (locked) are **not** held at OS level; the core applies them to each stroke. So
  a crash never leaves Ctrl down; `release_all` still sends key-ups for any chord whose send did
  not finish (existing `_keys_down` mechanism).
- `InputBackend` gains `key_stroke`. `default_keys_for` gains the new shortcut actions.

**D11 – HUD (`platform/overlays.py`).**
- `KeyboardOverlay`: keys drawn from the layout; highlighted key; pressed flash
  (`click_flash_ms`); one-shot modifiers outlined, locked ones filled; a recent-text strip above
  the keys; a dwell ring.
- `SetupOverlay`: step title, instruction, corner target, progress, error text.
- The pill shows "Keyboard", "Setup". Custom gesture firings show "‹name› → ‹action›" for
  `hint_display_ms`.
- All overlays stay click-through and non-activating (existing window flags), and are placed on
  the overlay monitor (D8).

## Project Structure

```text
.specify/memory/constitution.md   # v1.2.0 (D0)
docs/adr/0007-keyboard-two-hand-confirm.md   # NEW (D0)
docs/adr/0008-custom-gesture-matching.md     # NEW (D9)
src/gescrtl/core/
├── types.py          # + Sub.SETUP, Command.START_SETUP/END_SETUP/DISPLAYS, KeyStroke, KeyboardView,
│                     #   SetupView, SetupResult, CustomFired, CueKind.DWELL, OverlayKind.KEYBOARD,
│                     #   Action shortcut + mode members
├── config.py         # + D1 core fields
├── state_machine.py  # + SETUP sub-state, KEYBOARD selectable, mode actions via SET_MODE path
├── engine.py         # keyboard + second hand routing, SETUP routing, custom recognizer, displays
├── keyboard.py       # NEW (D2)
├── second_hand.py    # NEW (D3)
├── select.py         # + DwellSelector, external pinch signal (D3, D4)
├── pointer.py        # + dwell click, active center, desktop-box mapping (D4, D7, D8)
├── layout.py         # + keyboard_keys, LEVEL_STEP_TARGETS
├── mapping.py        # NEW (D6)
├── calibration.py    # NEW (D7)
├── displays.py       # NEW clamp to monitors (D8)
├── custom.py         # NEW descriptors, NN, DTW, segmenter, enrollment checks (D9)
├── media.py, presentation.py, mode_menu.py, level_panel.py   # resolved actions, dwell
src/gescrtl/settings/
├── store.py          # type-aware parse, new fields, titles (D1)
└── custom_store.py   # NEW (D9)
src/gescrtl/platform/
├── interfaces.py     # + key_stroke, DisplaySource
├── win_input.py      # + key_stroke, Unicode, virtual-desktop move (D8, D10)
├── displays.py       # NEW EnumDisplayMonitors + Qt screen signals (D8)
├── win_autostart.py  # NEW (D5)
├── settings_window.py# NEW (D5, D6, D9 UI)
├── overlays.py       # + KeyboardOverlay, SetupOverlay, monitor placement (D11)
├── hud.py, tray.py   # route new events; Settings…, Calibrate…, Disable custom gestures
src/gescrtl/app.py    # wire displays, setup results, settings window, custom store
src/gescrtl/tools/bench.py   # count KeyStroke, CustomFired; per-frame matcher time
docs/interaction/*, docs/product/known-limitations.md, README.md   # FR-030
```

## Recordings to make (camera steps, user)

Record with `python -m gescrtl --record <name>`, then copy the chosen ones to
`tests/fixtures/` with an `.expect.json`:

- **R1** `typing_one_hand` / `typing_two_hands`: type "hello world 2026" twice in Keyboard
  Mode, and use Copy/Paste.
- **R2** `bystander_pinch`: a second person's hand pinching near yours, while you point at keys
  (expect 0 presses from it).
- **R3** `idle_keyboard`: about 5 min idle, physical typing, and talking in Keyboard Mode, with
  dwell on and pointer dwell click on (SC-003).
- **R4** `custom_shapes` / `custom_moves`: enroll 2 shapes and 2 movements, then 20 attempts
  each. Plus **R5** `all_builtins`: every built-in gesture several times (SC-008).
- **R6** `calibration`: one full calibration run (at least 3 people or setups for SC-006, live
  only).

R3, R5, and the existing idle/typing/talking fixtures from specs 002/003 must produce 0
`KeyStroke`, `Click` from dwell, and `CustomFired` events.

## Replay Test Coverage (FR-029 / SC-010)

Synthetic scripts unless marked *(fixture)*:

| File | Covers |
|---|---|
| `test_us1_keyboard.py` | menu/tray select Keyboard; highlight follows hand over keyboard rect only; pinch = one KeyStroke; lookback picks the pre-pinch key; no MoveCursor; repeat for Backspace/arrows only; shortcut row; Move key; hints |
| `test_us1_modifiers.py` | one-shot, locked, off; Shift folds into upper case; Ctrl+C; modifiers cleared on pause/loss/stop/mode change |
| `test_us1_two_hand.py` | second-hand pinch presses highlighted key; same-hand-label rejected; too far rejected; bystander rejected; both pinch = one press; second hand lost = nothing; disabled by setting; not active outside Keyboard |
| `test_dwell.py` | DwellSelector fire/re-arm/progress; dwell in menu, grid, panel ± targets; pointer dwell click opt-in, never during clutch/scroll/drag |
| `test_us2_settings.py` | type-aware parse (bool/str/dict), ranges, titles present for every field, reset disables custom gestures, mappings warnings |
| `test_mapping.py` | defaults, overrides, excluded actions impossible, mode action uses SET_MODE path, grid labels |
| `test_us3_calibration.py` | check-step failures (low FPS, too close/far), reach → region/center, pinch → thresholds with hysteresis, too-similar failure, cancel/pause/loss → no change, no input in SETUP |
| `test_us4_displays.py` | two/three monitors, mixed sizes, gaps and offsets clamp; DISPLAYS change mid-session; no DISPLAYS = old behaviour |
| `test_us5_custom_shape.py` | enrollment checks (built-in look-alike refused, inconsistent takes, duplicates); hold, fire once, cooldown, re-arm; cursor freeze; never while busy |
| `test_us5_custom_move.py` | segmentation, DTW match, duration bounds, swipe-like refused, discarded during pinch/scroll/swipe, cursor keeps moving in Pointer |
| `test_custom_store.py` | round trip, damaged file disables without overwrite, no image fields |
| `test_layout.py` (extend) | keyboard keys ≥ 48 px at 1280×720, both positions; ± targets |
| `test_architecture.py` (extend) | new core modules import nothing from platform/settings |
| `test_fixture_regressions.py` (extend) | R1–R5 *(fixture)* |

Every new test also checks determinism by running the script twice and comparing events.

## Order of work (for tasks)

1. D0 constitution + ADR 0007 → 2. D1 settings model → 3. D2 keyboard + D10 keys →
4. D3 second hand → 5. D4 dwell → 6. D8 multi-monitor → 7. D5 settings window + D6 remapping →
8. D7 calibration → 9. D9 custom gestures + ADR 0008 → 10. docs (FR-030) → validation session.

Steps 3–6 deliver a usable product even if custom gestures (9) end up gated off.

## Validation (one manual session, after implementation)

Run in the user's PowerShell venv:

```powershell
python -m pip install -e ".[dev]"
ruff check .; mypy src/gescrtl/core; pytest
python -m gescrtl --preview
python -m gescrtl.tools.bench --replay recordings\*.jsonl
python -m gescrtl.tools.bench --live 60   # once in Keyboard Mode with 3 custom gestures enrolled
```

Session checklist:
- US1–US5 acceptance scenarios
- SC-001 typing trial (5×), record characters per minute
- SC-002 each shortcut 10×
- SC-004 stop/pause/loss timings in Keyboard Mode, with a locked modifier
- SC-005 settings change and reset (timed)
- SC-006 calibration (timed, at least 3 people/setups)
- SC-007/SC-008 custom shapes and movements, separately: decides `CUSTOM_KINDS_AVAILABLE`
- SC-009 two monitors at mixed scaling: corners and 48 px targets on each; unplug and replug
  while running
- A non-US input language: typed characters match the keyboard
- Start with Windows on, sign out and in, starts Paused; then off
- Performance gate: the live bench is not worse than the spec 003 numbers beyond the allowed
  margin; matcher ≤ 2 ms p95

Results go to `docs/measurements/phase5-7-8-9-report.md`, with a short retrospective.

## Complexity Tracking

| Deviation | Why | Simpler alternative rejected because |
|---|---|---|
| Second controlling-input hand in Keyboard Mode (Principle I exception) | User decision in clarify: one hand points, the other pinches | Single hand only: the user explicitly chose two-hand pressing; restricted to confirm-only, same-person check, Keyboard Mode only |
| New Active sub-state `SETUP` | Calibration and enrollment must send no input yet keep pause/stop/loss | A separate app mode outside the state machine would bypass the safety paths |
| Custom movement gestures (DTW) | User decision in clarify (shapes and movements) | Shapes only: declined; gated per kind instead (FR-028) |
| `MoveCursor` changes meaning (primary → virtual desktop) | One area over all monitors (clarify) | Keeping primary-normalized events and remapping in platform would put the gap clamp outside the tested core |
