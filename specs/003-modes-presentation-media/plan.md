# Implementation Plan: Mode System, Presentation Mode, and Media/System Controls

**Branch**: `003-modes-presentation-media` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Scope**: Spec 003 (roadmap phases 3 + 4 + 6) plus quick level controls (volume and brightness
from every mode). Lean cycle: decisions are recorded inline here. There are no separate research,
data-model, contract, or quickstart files.

## Summary

Turn the single-mode engine of spec 002 into a mode system. The `StateMachine` gains a current
**mode** (Pointer, Presentation, Media/System; Keyboard listed but unavailable) and two temporary
**overlays** that block all other input: the **mode menu** (G7 held 0.8 s) and the **level panel**
("call me" G9 held 0.5 s). Each mode is a small pure controller behind one interface. The engine
handles global gestures first (pause, clutch, menu, panel, loss) and then hands the frame to the
current controller.

New poses: **G9 call me** (global) and **G10 index point** (Presentation pointer). New motion:
**open-hand swipe** (Presentation slide change). The existing G4 pose is reused in Presentation
as **thumbs-up / thumbs-down**, told apart by thumb angle.

Every menu, panel, target, and the laser pointer is drawn by the HUD and hit-tested in the core
using a shared normalized layout. While an overlay or a non-pointer mode is on, **the OS cursor
is never moved**. The core emits semantic actions (`SystemAction`, `LevelStep`). The platform
maps these to keys, Core Audio volume, and WMI brightness.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: existing (mediapipe, opencv-python, PySide6, pydantic v2, psutil) +
**pycaw** (Core Audio endpoint volume; pulls in **comtypes**). Brightness uses WMI
(`root\WMI`, `WmiMonitorBrightness` / `WmiMonitorBrightnessMethods`) through `comtypes`, with no
further dependency. Keys use the existing `SendInput` (`KEYBDINPUT`) in `platform/win_input.py`.

**Storage**: unchanged (`%APPDATA%\GesCRTL\settings.json`, `recordings/*.jsonl`, `tests/fixtures/`)

**Testing**: pytest (unit + landmark replay with `tests/support/hands.py` scripts), Ruff, mypy
`--strict` on `gescrtl.core`, `tests/test_architecture.py` purity guard

**Target Platform**: Windows 11, primary monitor, 100/125/150% scaling (FR-020)

**Project Type**: desktop app (tray + overlay), run from source

**Performance Goals**: unchanged from spec 002 (p95 internal delay ≤ 80 ms, idle CPU ≤ 5%).
Level changes must never block the worker thread: brightness WMI calls can take 50–200 ms.

**Constraints**: no network; no images written; ReleaseAll on every overlay open/close and mode
change; emergency stop ≤ 200 ms in every mode

**Scale/Scope**: about 6 new core modules, 3 new or extended platform modules, about 10 new
replay test files

All items are resolved. None are marked NEEDS CLARIFICATION.

## Constitution Check (pre- and post-design)

| Principle | How this plan complies | Status |
|---|---|---|
| I Safety | Every key or level action needs a stable pose (`stable_frames`) or, for the swipe, the open-hand pose on every frame of the motion (≥ `swipe_min_frames`), plus a cooldown. Menu/panel open and close, mode change, pause, loss and exit all emit `ReleaseAll`. Emergency stop and the pause gesture work in every mode and overlay. One primary hand (unchanged `PrimaryHand`). | ✅ |
| II Reliability | New gestures are tuned on recordings (R1–R4 below). Any gesture that fails SC-002/SC-003 is disabled by default, not shipped. | ✅ |
| III Visible state | `StateMachine` is the single owner of mode and overlay. The HUD pill always shows the mode (FR-005). Mode changes only through the menu (held + pinch-confirmed). | ✅ |
| IV Testable core | All new logic is in `gescrtl.core` (layout, controllers, swipe), with time from frame timestamps. The platform reads the actual volume/brightness and shows it in the HUD *outside* the core, so replays stay deterministic. Each transition and action has a replay test (table below). | ✅ |
| V Performance | Level backend runs on its own thread with latest-target-wins coalescing. Bench counts new events. | ✅ |
| VI Privacy | No change. The screenshot action is a user-requested OS shortcut (Win+PrtSc), not a camera image. | ✅ |
| VII Platform isolation | Keys, foreground-app detection, Core Audio, WMI, and the new widgets live in `platform/` behind `Protocol`s. The core emits semantic enums only. | ✅ |
| VIII Simplicity | Two new hand forms and one motion, each justified in Complexity Tracking. Hints: at most 4 per mode. All new thresholds are validated settings. Either hand works the same way; no handedness logic. | ✅ |

## Key Design Decisions

**D1 – Mode and overlay in the state machine.**
- `Mode` enum in `core/types.py`: `POINTER`, `PRESENTATION`, `MEDIA`, `KEYBOARD`.
  `StateMachine.mode` starts as `POINTER` on every launch (FR-004). It is kept through Paused,
  Tracking Lost and emergency stop.
- New `Sub` values: `MODE_MENU`, `LEVEL_PANEL` (both are Active sub-states, like `CLUTCHED`).
- New methods, each returning events:
  - `open_menu()` (E12), `confirm_mode(mode)` (E13), `cancel_menu()` (E14)
  - `open_panel()`, `close_panel()`
- Every open/close/confirm emits `ReleaseAll`. Confirm also emits `ModeChanged(mode)` and the new
  mode's hints.
- Every HUD text uses the mode name: `"Pointer"`, `"Presentation"`, `"Media"` (the short form of
  Media/System, used in the pill and the menu), plus `" · Hold"` when clutched. `resume` and `hand_back` restore the current mode's text. `resume` shows that
  mode's hints; `hand_back` shows none.
- Hand loss, pause, emergency stop, camera loss, or exit while in `MODE_MENU`/`LEVEL_PANEL` close
  the overlay (mode unchanged) via the existing `_go(...)` paths, per the interaction-model table.
- `KEYBOARD` cannot be confirmed: the item is drawn greyed and a pinch on it does nothing.
- **Tray fallback (FR-025)**: new `Command.SET_MODE` with `arg` = mode name (`"PRESENTATION"`).
  `StateMachine.on_command` handles it with the same path as `confirm_mode`:
  - In Active: `ReleaseAll`, close any overlay, `ModeChanged`, hints.
  - In Paused or Tracking Lost: just set `mode` and emit `ModeChanged`. The indicator text stays
    "Paused"; the new mode is used on resume.
  - `KEYBOARD`, an unknown name, or Inactive → no-op.

  It is recorded and replayed like every other command (JSONL v2 already stores `arg`).

**D2 – Engine dispatch.** `Engine.step` keeps its existing frame/confidence/loss handling. After
the stable pose is known, while Active:
1. `CLUTCHED`: as today (G8 held still 1.5 s pauses; another pose ends the clutch). In
   Presentation, the swipe detector also runs (D6), so a flat-hand swipe still changes slides.
   Outside Pointer Mode, clutch emits **no** `CueChanged(CLUTCH)`, so the Pointer cursor cue never
   appears during a presentation. The pill reads "Presentation · Hold" / "Media · Hold".
2. `MODE_MENU` → `ModeMenu.update(...)`; `LEVEL_PANEL` → `LevelPanel.update(...)`.
3. `NORMAL`, global gestures first:
   - G8 → clutch, as today
   - G7 held `menu_hold_ms` → `open_menu`
   - G9 held `panel_hold_ms` → `open_panel`

   G7 and G9 are ignored while the current controller reports `busy` (mid-pinch, drag, scroll,
   swipe in progress, or pending confirmation). The hold timer starts when the pose becomes
   stable, using `tracker.since_ns`.
4. Otherwise → the current mode controller: `PointerController` (the existing `Pointer`, unchanged
   behaviour), `PresentationController`, or `MediaController`.

Controllers share one small protocol in `core/modes.py`:
`update(feats, raw, stable, t_ns) -> list[Event]`, `reset() -> list[Event]`, and `busy: bool`.
`_after_transition` resets all controllers and overlays. The existing fist-freeze (`_fist_held`)
stays Pointer-only.

**D3 – Shared layout and overlay pointer.**
- `core/layout.py` defines every on-screen target as normalized rects (0..1 of the primary
  monitor), imported by the core (hit-testing) and by `platform/hud.py` (drawing):
  - mode menu: 4 items in a row, centred, each 0.18 × 0.16, Keyboard greyed
  - level panel: 2 vertical sliders, Volume and Brightness, each 0.10 × 0.45, centred
  - media grid: 10 targets in 2 rows of 5, each 0.15 × 0.14
- Minimum target size is ≥ 48 px at 1280×720. A unit test checks this for 1280×720, 1920×1080, and
  2560×1440 (FR-020, CLAUDE.md "design for ≥ 48 px").
- Overlays and Media mode point with the same mapping as Pointer Mode (palm anchor, active region,
  One Euro). They emit `OverlayPointer(nx, ny, style)` with style `SELECT` (ring) or `LASER` (red
  dot), and `OverlayPointerHidden()`. **No `MoveCursor` is emitted outside Pointer Mode's normal
  pointing** (FR-003, FR-009, FR-023).
- Pointing uses hysteresis (constitution I). A target becomes "pointed" only when the pointer is
  inside it by at least `target_margin` (0.01). It stays pointed until the pointer leaves the rect
  itself. A pointer on an edge or between targets never newly selects anything (FR-016), and
  the highlight doesn't flicker on edges.

**D4 – Selection by pinch (shared helper `core/select.py`).** Used by the mode menu, the media
grid, and the level panel:
- A target is chosen when a **stable** G2 starts while a target is pointed. The pointed target is
  frozen at the first raw pinch frame, `pinch_lookback_frames` earlier (same trick as D5 in spec
  002), so the pinch motion does not slide off the target.
- One action per pinch. A new action needs the pinch released and the per-target
  `action_cooldown_ms` (400) passed.

**D5 – Mode menu (`core/mode_menu.py`).**
- Confirm = D4 on an enabled mode item → `confirm_mode`.
- Cancel = stable G5, or `menu_timeout_ms` (5000) without a confirm → `cancel_menu`.
- The menu emits `OverlayShown(kind=MODE_MENU, highlight=<pointed item or "">)` whenever the
  highlight changes. `OverlayHidden()` is emitted on close.

**D6 – Presentation Mode (`core/presentation.py` + `core/swipe.py`).**
- **Laser pointer (FR-009)**: shown only while the *stable* pose is G10 index point. It uses its
  own One Euro filter (`laser_min_cutoff` 0.3, `laser_beta` 0.002) on the palm anchor, keeping the
  measured palm-center anchor. When the stable pose leaves G10, the dot stays put for
  `laser_grace_ms` (300) and then `OverlayPointerHidden`. If G10 comes back within the grace
  period, the filter is not reset, so the dot doesn't jump. Mode exit, pause, and loss hide it at
  once.
- **Swipe (FR-008)**, `SwipeDetector`, fed with the anchor, hand size, and *raw* pose on every
  good frame:
  - "Open hand" = all four fingers extended (raw G6, G8, or the four-extended G1 case). Any frame
    that isn't open hand, any bad frame, or any G10 clears the window.
  - Fires when, inside `swipe_window_ms` (350), there are ≥ `swipe_min_frames` (3) open-hand
    frames, horizontal travel ≥ `swipe_min_dist` (1.5 hand sizes), and |dy| ≤
    `swipe_max_dy_ratio` (0.5) × |dx|.
  - Direction is in screen space (landmarks are already mirrored): +x = `SLIDE_NEXT`, −x =
    `SLIDE_PREV`.
  - After a swipe: global `swipe_cooldown_ms` (600). The opposite direction is blocked for
    `swipe_return_block_ms` (1000). Re-arming needs the hand speed below `swipe_rearm_speed` (1.0
    hand sizes/s) for 100 ms.
  - Requiring the raw pose on ≥ 3 frames *is* the stable-frames gate for this motion. It also
    works at ~10 FPS: 3 frames ≈ 300 ms, inside the window.
- **Show start/end (FR-010)**: stable G4 held `show_hold_ms` (1000).
  - Thumb direction uses hysteresis (constitution I). It becomes "up" at `thumb_tilt_deg` ≥
    `thumb_dir_enter_deg` (50) and stays up until it drops below `thumb_dir_exit_deg` (35). "Down"
    mirrors this (≤ −50, cleared above −35). The 1 s hold runs only while the direction stays
    the same; leaving the direction resets it. Up → `SHOW_START`, down → `SHOW_END`, neither →
    nothing.
  - Note: `_thumb_tilt` uses |dx|, so tilt is −90..+90 with up positive; that works for both
    hands.
  - Fires once per hold. A new hold needs another stable pose first. `show_cooldown_ms` (2000).
    The laser is hidden while G4 is held.
- `busy` is true while a swipe window has ≥ 2 frames, or while G4 is held.

**D7 – Media/System Mode (`core/media.py`).**
- Shows the media grid (D3) with `OverlayShown(kind=MEDIA, ...)` while the mode is Active ·
  Normal. Targets: play/pause, previous, next, volume −, volume +, mute, brightness −,
  brightness +, screenshot, switch app.
- Play/pause, previous, next, mute: one `SystemAction` per D4 selection.
- Volume/brightness ±: on selection emit `LevelStep(level, ±level_step)`, then repeat every
  `level_repeat_ms` (150) while the raw pose stays G2 *and* the pointer stays on the target
  (FR-014). Repeats stop on release, leaving the target, loss, pause, or mode change.
- Screenshot and switch app: the first selection puts the target in *pending* state for
  `confirm_window_ms` (3000) and shows "Pinch again to confirm". A second D4 selection on the same
  target sends the action. Stable G5, timeout, or selecting another target cancels it (FR-015).
  `busy` is true while pending.

**D8 – Level panel (`core/level_panel.py`), all modes (FR-021–FR-024).**
- Opened by D2 step 3. Shows `OverlayShown(kind=LEVELS, highlight=...)`.
- Pinch (D4) on a slider starts an adjustment. Relative drag: travel = `(start_y − y) /
  slider_height × level_drag_gain` (100 % per slider height) is accumulated. Whole multiples of
  `level_step` (2 %) are emitted as `LevelStep(level, ±2)`, capped at `level_max_rate` (40 %/s)
  using frame `dt` (capped at 100 ms). The level therefore never jumps (FR-022).
- Release stops the change. Stable G5 or `panel_timeout_ms` (5000) without a pinch closes the
  panel. Pause, loss, menu, and emergency stop close it through D1.
- The core never knows the absolute level. The platform reads it and shows it (D10).

**D9 – Poses (`core/poses.py`, `core/features.py`).** The classifier order stays pinch first,
then:
- all four curled → G4/G5 (unchanged)
- **G9 call me**: index, middle and ring curled, pinky extended, thumb extended, and
  `pinch_index > THUMBSUP_MIN_TIP_DIST`. A pinky that is neither curled nor extended (between
  the thresholds) → not G9; it stays in the existing branches (usually G1, or G4 if all curled).
  This is the "loose pinky scroll" edge case.
- four extended → G6/G8/G1 (unchanged)
- G7 (unchanged)
- **G10 index point**: index extended, middle/ring/pinky curled, thumb not extended.
- else G1

Pointer Mode treats G10 exactly like G1: add it to `_MOVE_POSES` in `core/pointer.py`, so the
cursor behaviour of spec 002 is unchanged. G9 also moves the cursor until its 0.5 s hold
completes, which is acceptable because no clicks are possible in that pose. Both poses get unit
tests in `tests/unit/test_poses.py` and builders in `tests/support/hands.py`.

**D10 – Platform.**
- `InputBackend.system_action(action: Action) -> bool` in `platform/interfaces.py`,
  implemented in `win_input.py` with `KEYBDINPUT` (down+up in one `SendInput` call, so no key
  stays held; `release_all` also releases any modifier it pressed).
- Media keys: `VK_MEDIA_PLAY_PAUSE`, `VK_MEDIA_NEXT_TRACK`, `VK_MEDIA_PREV_TRACK`,
  `VK_VOLUME_MUTE`. Screenshot = Win+PrtSc. Switch app = Alt+Tab tap (previous app).
- `platform/presenter_keys.py` picks slide keys from the foreground window
  (`GetForegroundWindow` → process exe + title):

  | Foreground | Next / Prev | Start (current slide) | End |
  |---|---|---|---|
  | `POWERPNT.EXE` | Right / Left | Shift+F5 | Esc |
  | Browser (`msedge.exe`, `chrome.exe`) with "Google Slides" in the title | Right / Left | Ctrl+Shift+F5 | Esc |
  | Anything else (incl. the Edge PDF viewer) | Right / Left | unsupported | unsupported |

  **Verify the Google Slides start shortcut in the manual session** and fix the table if it
  differs. Keys go to the foreground window; the app never changes focus (spec edge case).
- `LevelBackend` protocol (`interfaces.py`): `step(level, delta)`, `read(level) -> int | None`.
  - `platform/levels.py` `WinLevels` runs on one daemon thread that calls `CoInitialize` and
    coalesces pending deltas (latest wins).
  - Volume uses pycaw `IAudioEndpointVolume` (`SetMasterVolumeLevelScalar`, clamp 0..1).
  - Brightness uses WMI `WmiSetBrightness(1, level)`; it reads `WmiMonitorBrightness.CurrentBrightness`.
  - If the WMI class is missing or the call fails → `read` returns `None` and the HUD shows
    "Brightness unavailable" (FR-024). After each applied step it calls an `on_level(level,
    value)` callback; app.py routes this to the HUD through the Qt bridge.
- `InputBackend.system_action(action) -> bool` returns `False` when the action isn't supported in
  the foreground app. `Worker._emit_all` then calls `self.ui(Warning("Start/end not supported in
  this app"))`.
- Worker `_emit_all` dispatches `SystemAction` → `input.system_action` and `LevelStep` →
  `levels.step`. Both are swallowed with a log line on failure, never raised (ReleaseAll still
  applies).

**D11 – HUD (`platform/hud.py`, new `platform/overlays.py`).** One frameless, click-through,
non-activating widget per overlay kind (same window flags as `CursorCue`), drawn from
`core/layout.py`:
- `ModeMenuView`, `LevelPanelView` (slider fill = last `on_level` value, or "unavailable"),
  `MediaGridView` (pending target outlined with "Pinch again to confirm").
- `LaserDot` (red, 16 px, with a soft glow).
- `platform/tray.py`: a "Mode" submenu with checkable, exclusive actions Pointer, Presentation,
  Media/System, and Keyboard (disabled). It checks the item from `ModeChanged`. A pick calls a
  new `on_mode(mode)` callback, which app.py wires to `worker.post(Command.SET_MODE, mode.name)`.
- `SelectRing` for `OverlayPointer(SELECT)`.

Pill text = mode name (FR-005). `HintsShown` on mode entry, at most 4 lines:
- Pointer: "Pinch: click · hold: drag", "Thumb out, tilt: scroll", "Three fingers: modes · call
  me: volume/brightness", "Flat hand 1.5 s: pause"
- Presentation: "Index finger: pointer", "Open-hand swipe: next / previous", "Thumb up 1 s: start
  show · down: end", "Flat hand 1.5 s: pause"
- Media: "Point + pinch: run action", "Hold pinch on ±: keep changing", "Fist: cancel", "Flat
  hand 1.5 s: pause"

**D12 – New events (`core/types.py`).**
- `ModeChanged(mode)`
- `OverlayShown(kind: OverlayKind, highlight: str = "", pending: str = "")` and `OverlayHidden()`
- `OverlayPointer(nx, ny, style: PointerStyle)` and `OverlayPointerHidden()`
- `SystemAction(action: Action)`, where `Action` is: `SLIDE_NEXT`, `SLIDE_PREV`, `SHOW_START`,
  `SHOW_END`, `PLAY_PAUSE`, `NEXT_TRACK`, `PREV_TRACK`, `MUTE`, `SCREENSHOT`, `APP_SWITCH`
- `LevelStep(level: Level, delta: int)`, where `Level` is `VOLUME` or `BRIGHTNESS`

Recordings (JSONL v2) need no format change: they hold frames and commands, and events are
re-derived on replay.

**D13 – Settings.** Add these to `CoreConfig` **and** `settings/store.py` (validated, resettable),
with the defaults above:
- `menu_hold_ms`, `menu_timeout_ms`, `panel_hold_ms`, `panel_timeout_ms`
- `swipe_window_ms`, `swipe_min_frames`, `swipe_min_dist`, `swipe_max_dy_ratio`,
  `swipe_cooldown_ms`, `swipe_return_block_ms`, `swipe_rearm_speed`
- `show_hold_ms`, `show_cooldown_ms`, `thumb_dir_enter_deg`, `thumb_dir_exit_deg` (enter must be
  above exit; validated)
- `laser_min_cutoff`, `laser_beta`, `laser_grace_ms`
- `level_step`, `level_max_rate`, `level_drag_gain`, `level_repeat_ms`
- `action_cooldown_ms`, `confirm_window_ms`, `target_margin`

All of these are provisional until the R1–R4 recordings are replayed.

## Project Structure

```text
src/gescrtl/core/
├── types.py          # + Mode, OverlayKind, PointerStyle, Action, Level, Pose.G9/G10, new events
├── config.py         # + D13 fields
├── features.py       # (no change expected; G9/G10 use existing curl/thumb features)
├── poses.py          # + G9, G10 (D9)
├── state_machine.py  # + mode, MODE_MENU, LEVEL_PANEL, mode-aware text and hints (D1)
├── engine.py         # dispatch (D2)
├── modes.py          # NEW controller protocol + PointerController wrapper
├── layout.py         # NEW normalized rects + hit test (D3)
├── select.py         # NEW pinch-on-target helper (D4)
├── mode_menu.py      # NEW (D5)
├── swipe.py          # NEW (D6)
├── presentation.py   # NEW (D6)
├── media.py          # NEW (D7)
├── level_panel.py    # NEW (D8)
└── pointer.py        # G10 added to _MOVE_POSES only
src/gescrtl/platform/
├── interfaces.py     # + system_action, LevelBackend
├── win_input.py      # + keyboard SendInput, system_action
├── presenter_keys.py # NEW foreground-app → keys (D10)
├── levels.py         # NEW WinLevels (pycaw + WMI) (D10)
├── overlays.py       # NEW menu/panel/grid/laser widgets (D11)
└── hud.py            # route new events
src/gescrtl/platform/tray.py # + Mode submenu (FR-025)
src/gescrtl/app.py           # wire LevelBackend, dispatch new events, on_level → HUD
src/gescrtl/settings/store.py # + D13 fields
src/gescrtl/tools/bench.py   # count SystemAction, LevelStep, ModeChanged, overlay opens
docs/interaction/            # gesture-vocabulary, interaction-model, feedback-hud, safety-policy
docs/product/known-limitations.md, README.md
docs/adr/0006-system-levels-pycaw-wmi.md   # NEW (constitution: stack decisions need an ADR)
```

## Recordings to make (camera steps, user)

These are needed for tuning and as replay fixtures. Record with
`python -m gescrtl --record <name>`, then copy the chosen ones to `tests/fixtures/` with an
`.expect.json`:

- **R1** `swipes_near` / `swipes_far`: 20 open-hand swipes each way, at 0.7 m and at the farthest
  distance that still tracks. One take in dim light (~10 FPS).
- **R2** `presenting`: about 3 min of talking while pointing with the index, swiping, and
  thumbs-up/down. Ground truth noted by the user.
- **R3** `callme_vs_scroll`: alternate "call me" and thumb-out scroll with a loose pinky.
- **R4** `idle_modes`: about 5 min idle, typing, and talking while in each mode, for SC-002.

The R4 recording and the existing spec 002 idle/typing/talking recordings must produce 0
`ModeChanged`, `OverlayShown`, `SystemAction` and `LevelStep` events (SC-002).

## Replay Test Coverage (FR-019 / SC-008)

Synthetic scripts (`tests/support/hands.py`) unless marked *(fixture)*:

| File | Covers |
|---|---|
| `test_us1_mode_menu.py` | open (0.8 s), confirm, fist cancel, 5 s timeout, single-frame pinch/fist ignored, Keyboard not selectable, ReleaseAll on open, no MoveCursor while open, loss/pause/stop close it, G7 ignored mid-drag |
| `test_us1_mode_persistence.py` | mode kept through Paused, Tracking Lost, emergency stop; launch starts in Pointer; mode-specific hints only |
| `test_us1_tray_mode.py` | `SET_MODE` in Active (ReleaseAll, overlay closed, hints), in Paused (applies on resume), Keyboard/unknown/Inactive no-op, replay of a recorded `SET_MODE` |
| `test_us2_swipe.py` | next/prev direction, too slow/short/diagonal ignored, return stroke ignored, cooldown, 10 FPS swipe, bad frame mid-swipe cancels, G10 motion never swipes, flat-hand swipe while clutched still swipes, swipe never pauses |
| `test_us2_laser.py` | dot only in G10, 300 ms grace, no jump on return, hidden on exit/pause/loss, no MoveCursor/clicks/scroll |
| `test_us2_show.py` | thumbs-up start once per hold, thumbs-down end, sideways nothing, cooldown |
| `test_us3_media.py` | each target sends its action once, volume/brightness repeat while held and stop on release/leave, screenshot and app-switch confirm, cancel, and timeout, edge pointing selects nothing |
| `test_us4_level_panel.py` | open from Pointer, Presentation, and Media; relative drag steps bounded by rate; fist/timeout close; loss/pause/menu close; no MoveCursor/clicks while open; G9 ignored mid-scroll |
| `test_poses.py` (extend) | G9, G10, loose-pinky scroll stays G4 |
| `test_layout.py` | every target ≥ 48 px at 1280×720 / 1920×1080 / 2560×1440; no overlaps; margin rule |
| `test_fixture_regressions.py` (extend) | R1–R4 fixtures *(fixture)* |

Every new test also asserts determinism by running the script twice and comparing events.

## Validation (one manual session, after implementation)

Run in the user's PowerShell venv:

```powershell
python -m pip install -e ".[dev]"
ruff check .; mypy src/gescrtl/core; pytest
python -m gescrtl --preview
python -m gescrtl.tools.bench --replay recordings\*.jsonl
python -m gescrtl.tools.bench --live 60   # once in Pointer, once in Presentation with the laser on
```

Session checklist:
- US1–US4 acceptance scenarios, including switching modes from the tray
- SC-001 timed menu switch (10 tries)
- SC-003 20-slide deck in PowerPoint and Google Slides at the documented distance; Edge PDF slide
  changes only
- SC-004 laser rest jitter (≤ 12 px over 2 s, 1080p)
- SC-005 each media action 10×
- SC-006 stop/pause/loss timings in each mode
- SC-009 volume and brightness to a requested level
- FR-020 menu, panel, and grid at 100/125/150% scaling
- FR-011: measure and document the working distance (step back 0.5 m at a time until swipes or
  the index pose fail)
- Verify the Google Slides start key
- SC-007: a short walkthrough where test users name the current mode and two of its gestures
- Performance gate: the live bench (p95 latency, FPS, idle CPU) is not worse than the spec 002
  numbers beyond the allowed margin

Results go to `docs/measurements/phase3-4-6-report.md`, with a short retrospective.

## Complexity Tracking

| Deviation | Why | Simpler alternative rejected because |
|---|---|---|
| New global gesture G9 "call me" (vocabulary grows past the 8 forms of R10) | Volume/brightness from every mode (FR-021); the user chose a direct gesture over the slower mode-menu sliders | Sliders inside the mode menu need a 0.8 s hold plus menu each time; two direct tilt gestures had high confusion risk (V-sign vs G7) |
| New Presentation pose G10 index point | Laser pointer must not be confused with swipes (spec clarification) | "Any relaxed hand" pointing streaks the pointer across the slide on every swipe |
| Swipe is a motion, gated per frame instead of by the stable-pose tracker | A swipe lasts 3–10 frames; waiting 3 stable frames first would miss it at 10 FPS | Held-pose slide navigation was offered and declined by the user |
| New dependency pycaw (+ comtypes) | Need to read and set the absolute volume to show the level (FR-022) | Volume media keys step by 2% blindly and can't report the current level |
