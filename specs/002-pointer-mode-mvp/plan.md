# Implementation Plan: Pointer Mode MVP + Reliability Hardening (Phases 1–2)

**Branch**: `002-pointer-mode-mvp` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Scope**: Covers spec 002 (roadmap Phase 1) and the roadmap Phase 2 hardening items (`Plan.md` §3
groups both into spec 002). Lean cycle: decisions are recorded inline here. There are no separate
research, data-model, contract, or quickstart files.

## Summary

Build the first runnable GesCRTL from scratch in `src/gescrtl/`. It has one pipeline:
camera → MediaPipe adapter → **pure core** (filter → features → pose recognizer → state machine →
pointer action mapper) → platform backends (SendInput, HUD/cursor cue, tray, hotkeys). The core is
one deterministic object, `Engine`. It takes landmark frames, commands, and timestamps, and returns
events. This lets the same code run live, from a JSONL recording, and in pytest.

Phase 2 hardening adds the following to the same codebase:
- primary-hand lock robustness
- camera-interruption recovery
- jump/confidence rejection
- a false-trigger benchmark on recorded idle/typing/talking sessions
- tuning that turns every *(provisional)* value in `docs/interaction/safety-policy.md` into a
  measured value

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: mediapipe (Hand Landmarker, Tasks API, VIDEO mode), opencv-python
(DirectShow + MJPG, 640×480@30), PySide6 (HUD, cursor cue, tray), pydantic v2 (settings),
psutil (CPU measurement); Win32 via `ctypes` (SendInput, RegisterHotKey, DPI, window styles)

**Storage**: `%APPDATA%\GesCRTL\settings.json`; dev recordings `recordings/*.jsonl` (gitignored);
test fixtures `tests/fixtures/*.jsonl`

**Testing**: pytest (unit + landmark replay), Ruff (lint/format), mypy `--strict` on `gescrtl.core`

**Target Platform**: Windows 11 (10 expected to work), primary monitor only, 100/125/150% scaling

**Project Type**: desktop app (tray + overlay), run from source

**Performance Goals**: p95 internal delay ≤ 80 ms (Phase 0: 32 ms); tracking ≥ 25 FPS (camera cap
30); Paused at 10 FPS; idle CPU ≤ 5% (Phase 0: 1.3%)

**Constraints**: no network at runtime; no images written; latest-frame-wins (queue size 1);
emergency stop ≤ 200 ms even if the camera or tracker stalls

**Scale/Scope**: one user, one hand, Pointer Mode only; about 15 core modules and 6 platform modules

All Technical Context items are resolved. None are marked NEEDS CLARIFICATION.

## Constitution Check (pre- and post-design)

| Principle | How this plan complies | Status |
|---|---|---|
| I Safety | Confidence gate + stable-frame gate + pinch hysteresis + cooldowns in core. `ReleaseAll` is emitted by the state machine on every exit from Active and also enforced by the backend: `finally`, `atexit`, `sys.excepthook`, `SetConsoleCtrlHandler`. Hotkey `Ctrl+Alt+Esc` calls `InputBackend.release_all()` directly from the hotkey thread, so a stalled worker cannot block it. Gesture G5 is the second path, and the tray is the third. Primary-hand lock is enforced (H1). | ✅ |
| II Reliability | Phase 2 tuning + false-trigger benchmark gate the release (SC-004). Any gesture that fails the target is disabled by default, not shipped. | ✅ |
| III Visible state | The single `StateMachine` decides. Recognizers emit poses/intents only. HUD pill + cursor cue are non-activating and click-through. Hand/camera loss is shown in ≤ 1 s. | ✅ |
| IV Testable core | `gescrtl.core` has no imports of cv2/mediapipe/PySide6/ctypes/`time` (enforced by a test that scans imports). Clock = frame `t_ns`. JSONL record/replay. Each transition has a replay test. Every misfire becomes a fixture first. | ✅ |
| V Performance | Per-stage timing in every frame (`StageTimes`). `gescrtl.tools.bench` reports latency/FPS/CPU/false-trigger rate. Latest-frame-wins capture. | ✅ |
| VI Privacy | Frames exist only in memory in the capture thread. The recorder writes landmarks only. A test asserts that no `cv2.imwrite`/`socket` is used in `src/`. | ✅ |
| VII Platform isolation | All Win32/Qt code is in `gescrtl/platform/` behind `Protocol`s. MediaPipe is wrapped by `tracking/mediapipe_adapter.py` → project `HandFrame` types. | ✅ |
| VIII Simplicity/defaults | Works with zero config. All thresholds are in validated settings with reset. Rule-based recognizer. Left/right hand symmetric (ratios are hand-size-normalized, no handedness assumptions). | ✅ |

**Deviation**: see Complexity Tracking.

## Key Design Decisions

**D1 – Core API.** `Engine(config, double_click_ms)`:
- `engine.step(frame: HandFrame | None, t_ns) -> list[Event]` is called once per tracked frame.
  `None` means a camera frame with no hand.
- `engine.command(cmd, t_ns) -> list[Event]` handles hotkey/tray commands: Resume, Pause,
  EmergencyStop, TurnOff, TurnOn, CameraLost(cause), CameraBack, ReloadSettings.

Events are frozen dataclasses:
- `StateChanged(state, sub, hud_text)`
- `CueChanged(kind, progress)`
- `MoveCursor(nx, ny)` (normalized 0..1 on the primary monitor)
- `ButtonDown/ButtonUp(button)`
- `Click(button)`
- `Scroll(delta)`
- `ReleaseAll(reason)`
- `Warning(text)`

The core never computes pixels. The platform maps normalized coordinates to the monitor.

**D2 – Clock.** Only frame/command timestamps (`time.perf_counter_ns()` stamped in platform/capture)
enter the core. Holds, cooldowns, stabilization, and loss windows all use these timestamps. The
replay reuses the recorded timestamps, so results are identical on every run (FR-029).

**D3 – Pose recognizer (rule-based).** Features use landmarks normalized by hand size
(wrist→middle-MCP distance):
- pinch ratios thumb–index and thumb–middle
- finger-extended flags (tip farther from the wrist than the PIP joint)

Poses: G1 relaxed, G2 pinch-index, G3 pinch-middle, G4 fist-with-thumb-out (scroll), G5 fist, G6 open palm,
G7 three-fingers, G8 flat hand (clutch). See `docs/interaction/gesture-vocabulary.md`.
- Pinch enter is < 0.25 and release is > 0.35 (hysteresis). If both pinches are below enter, the
  smaller ratio wins.
- A raw pose becomes the *stable* pose only after `stable_frames` (3) consecutive frames.
- Frames with confidence < `min_confidence` (0.5) are treated as "no hand" for loss counting. They
  never emit actions, and the cursor holds its position.

**D4 – Pointer mapping.** Anchor = palm center (mean of landmarks 0, 5, 9, 13, 17), mirrored.
The One Euro filter (1.0 / 0.007 / 1.0) runs on timestamps. The central `active_region` (0.6) maps
linearly to [0,1]², clamped at the edges. The filter is reset on re-entry to Active, so the cursor
does not drift in from a stale position.

**D5 – Click / double / drag.**
- When G2 becomes stable, the cursor freezes at its pinch-start position for `click_stabilize_ms`
  (100). The pinch-start position is the cursor position `pinch_lookback_frames` (2) frames before
  the stable onset, which compensates for the stable-frame delay.
- Releasing before `drag_hold_ms` (300) sends `Click(left)` at the frozen position.
- A second G2 onset within the system double-click time (`GetDoubleClickTime`, injected) and
  within the OS double-click rectangle is frozen at the **first** click's position. Windows then
  forms the double-click itself, so FR-011 is met.
- Holding to `drag_hold_ms` sends `ButtonDown(left)` at the frozen position. After that, movement
  follows the hand, and the release sends `ButtonUp`.
- G3 is a tap → `Click(right)` with a 300 ms cooldown. G3 cannot start a drag.

**D6 – Scroll (thumb tilt, like a held scroll wheel).**
- While G4 (fist, thumb out) is stable, the cursor is frozen and hand movement is ignored.
- Tilt = angle of the thumb (landmark 2 to 4) above horizontal in the aspect-corrected image,
  `atan2(-dy, |dx|)`, low-pass filtered (~2 Hz One Euro, beta 0). The filter restarts on the first
  raw G4 frame so the start angle is the real thumb angle.
- The start angle (neutral) is taken when G4 becomes stable and keeps following the thumb for
  `scroll_settle_ms` (250) while it settles. After that `rel = tilt - start`.
- Rate: 0 inside `scroll_deadzone_deg` (8); then `scroll_max_rate * x^1.5` with
  `x = (|rel| - dz) / (scroll_full_deg - dz)` capped at 1 (full at 45 deg); thumb up is positive
  (scroll up). The accumulator adds `rate * dt` (dt from frame timestamps, capped at 100 ms) and
  whole multiples of `scroll_step` (30) are emitted as `Scroll(delta)`, so speed does not depend on
  FPS.
- Scrolling runs only while the *raw* pose is still G4 (the thumb moves sharply as the fist
  opens, before the stable pose changes). Ending the pose, pause, loss or low confidence stop it.
- A classic vertical thumbs-up only anchors there; it scrolls only when tilted away.
- Only vertical scrolling is supported.

**D7 – States.** These states are implemented exactly as in `docs/interaction/interaction-model.md`:
- Inactive
- Paused
- Active·Normal
- Active·Clutched
- TrackingLost·HandMissing
- TrackingLost·CameraUnavailable

Clutch is the flat hand G8: on G8 onset the state is Clutched (RA, cursor frozen) until it is
released. Held to `pause_hold_ms` (1500) the flat hand pauses (RA). A fist (G5) in Normal freezes
the cursor and releases held input once but never pauses. Resume requires G6 held for `resume_hold_ms` (1000) in
Paused. The pause and resume cooldown is 1000 ms. Emergency stop shows "Stopped" for 600 ms, then
"Paused".

**D8 – Mode menu (G7).** ModeMenuOpen and E12–E14 are **not implemented** (FR-016). G7 is
recognized as a pose so that it cannot be mistaken for G1. It causes no action and no cursor
movement while held.

**D9 – Primary hand (H1).**
- The hand that completes the resume hold becomes primary.
- On each frame the primary hand is the hand nearest the last primary wrist position, within
  `max_hand_jump` (0.15 of frame width).
- If no hand is within that distance, the frame counts as "primary missing" (it is not swapped
  silently).
- On return from TrackingLost: a single hand is accepted. If several hands are present, the one
  nearest the last known position is accepted.
- Handedness labels are recorded but not trusted for identity, because MediaPipe flips them.

**D10 – Uncertain tracking (H3).** In addition to the confidence gate, a primary-anchor jump
greater than `max_anchor_jump` (0.12/frame) is rejected as a bad frame (counts toward loss). No
action may start until the pose has been stable for `stable_frames` after any rejected frame.

**D11 – Camera (H2).** The capture thread (OpenCV DSHOW, MJPG) keeps the newest frame only:
- `cap.read()` failing or returning no frame for 1 s → `CameraLost`.
- If `VideoCapture.open()` fails while the device is still enumerated, the cause is reported as
  "in use by another app".
- Reopening is retried every 2 s. Success → `CameraBack` → HandMissing → automatic Active when the
  hand returns. This matches the interaction model, which never leaves Paused automatically.
- In Paused, the capture still grabs every frame, but only every third frame is tracked (10 FPS
  cap, ADR/Phase 0).

**D12 – Threads.** There are three threads:
- **Qt main thread**: HUD, cue, tray.
- **Worker thread**: capture-grab → track → `engine.step` → dispatch input events directly to
  `InputBackend`. UI events are posted to Qt via a signal.
- **Hotkey thread**: `RegisterHotKey` + `GetMessage` loop.

Commands reach the worker through a `queue.Queue`. The worker waits at most 50 ms, so commands
are handled even if the camera stalls. EmergencyStop also calls `release_all()` immediately on the
hotkey thread. The `InputBackend` is lock-guarded, tracks pressed buttons, and its `release_all` is
idempotent.

If `Ctrl+Alt+Esc` registration fails, the app shows a `Warning` and the engine refuses Resume
(FR-008). The tray Pause still works.

**D13 – Input & DPI.**
- Call `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` before `QApplication` is created.
- Cursor moves use `SendInput` with `MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK`. The values
  are normalized over the virtual desktop and computed from the primary monitor rect
  (`GetMonitorInfoW`).
- Clicks, buttons, and wheel input also use `SendInput`.
- If an input is ignored by an elevated window, nothing crashes (the limitation is documented in
  `known-limitations.md`).

**D14 – HUD and cursor cue.** These use two PySide6 frameless windows. Flags:
`Tool | WindowStaysOnTopHint | WindowTransparentForInput | WindowDoesNotAcceptFocus` +
`WA_ShowWithoutActivating`, plus `WS_EX_NOACTIVATE | WS_EX_TRANSPARENT | WS_EX_LAYERED` via ctypes
(ADR 0003).
- **Pill**: top-right, text + color per `feedback-hud.md`. It shows up to 4 hints for 3 s on entry
  to Active.
- **Cue**: a 48 px ring that follows the cursor position (from `MoveCursor`, with no polling). Its
  looks:
  - ready ring
  - pinch progress arc (from the pinch ratio between release and enter)
  - click flash (150 ms)
  - drag = filled
  - scroll = vertical arrows
  - clutch = dashed

  The cue is hidden outside Active.

**D15 – Settings.**
- Pydantic `Settings` covers active_region, One Euro params, scroll rate/step, hold times, pinch
  thresholds, cooldowns, min_confidence, stable_frames, and the jump limits. Each field has a range.
- Loading validates field by field. An invalid field falls back to its default, the field name
  goes into a `Warning`, and the app keeps running (FR-025).
- A missing file → defaults are written.
- Emergency hotkey, pause, and ReleaseAll are not fields (FR-020).
- Reload (tray): `ReleaseAll` → new config applied to the engine; the state and mode are kept
  (FR-024a).
- Reset: defaults are rewritten, then reloaded.
- No file watcher.

**D16 – Recording format.** JSONL `format_version: 2`. It is the Phase 0 v1 header/frame lines
plus `{"type":"command","t_ns":..,"cmd":..}` lines, so hotkeys, tray actions, and camera events
replay too. The reader accepts v1 and v2.
- Recording is enabled with `python -m gescrtl --record <name>` → `recordings/<ts>_<name>.jsonl`.
- `python -m gescrtl.replay <file>` prints the event stream. It uses no camera and no OS input.

**D17 – Test fixtures.** Most replay tests use **synthetic** hands. `tests/support/hands.py` builds
21-landmark poses (G1–G7) at a given position, scale, and confidence. A small script DSL
(`hold(G2, 80ms) → move(...) → none(5 frames)`) writes the JSONL. These fixtures are exact and
readable. **Real** recordings (idle, typing, talking, second person, demo task) are added in the
manual session and used for the false-trigger gate and regression tests.

**D18 – Benchmark (H4, FR-032).** `python -m gescrtl.tools.bench`:
- *Replay mode* (`--replay recordings/*.jsonl`) counts consequential actions per scenario. For
  idle/typing/talking scenarios, any count above 0 is a failure.
- *Live mode* (`--live 60s`) reports capture→input p50/p95 delay from `StageTimes`, tracking FPS,
  and process CPU% (psutil). Results go to `docs/measurements/phase1-2-report.md`.

**D19 – Tuning (H5/H6).** Provisional values are tuned in this order:
- confidence
- stable frames
- pinch ratios
- hold times
- cooldowns
- click stabilization

Tuning uses the replay benchmark on the real recordings plus the demo task. The final values
replace the *(provisional)* marks in `safety-policy.md` and become the `Settings` defaults. Any
change that came from Phase 1 usage (activation/pause feel) is noted in the retrospective.

## Project Structure

```text
pyproject.toml                 # deps, ruff, mypy, pytest config; src layout
scripts/fetch_model.ps1        # downloads hand_landmarker.task → models/ (dev-time only)
models/                        # gitignored
src/gescrtl/
├── __main__.py                # python -m gescrtl [--record NAME]
├── app.py                     # wiring: Qt app, threads, backends, settings, exit handlers
├── replay.py                  # python -m gescrtl.replay FILE
├── core/                      # PURE: no cv2/mediapipe/Qt/ctypes/time imports
│   ├── types.py               # HandFrame, Hand, Landmark, Command, Event classes
│   ├── config.py              # CoreConfig (plain dataclass built from Settings)
│   ├── one_euro.py
│   ├── features.py            # anchor, hand size, pinch ratios, extended flags
│   ├── poses.py               # raw pose + stable-pose + pinch hysteresis
│   ├── primary_hand.py        # D9, D10
│   ├── pointer.py             # mapping, stabilization, click/double/drag, scroll, cue
│   ├── state_machine.py       # D7, D8; emits StateChanged/ReleaseAll
│   └── engine.py              # step()/command() orchestration, StageTimes passthrough
├── tracking/
│   ├── camera.py              # D11 capture thread, latest-frame-wins, reconnect
│   └── mediapipe_adapter.py   # → core.types.HandFrame
├── recording/jsonl.py         # writer/reader v1+v2
├── settings/store.py          # pydantic Settings, load/validate/save/reset (D15)
├── platform/
│   ├── interfaces.py          # InputBackend, OverlayBackend, HotkeyBackend, TrayBackend Protocols
│   ├── win_input.py           # SendInput, DPI, monitor rect, double-click time
│   ├── win_hotkeys.py         # RegisterHotKey thread
│   ├── hud.py                 # pill + cursor cue (PySide6)
│   └── tray.py
└── tools/bench.py             # D18
tests/
├── support/hands.py           # synthetic poses + script DSL (D17)
├── unit/                      # one_euro, features, poses, primary_hand, pointer, settings, jsonl
├── replay/                    # one test per gesture / transition / edge case; fixtures generated or real
├── fixtures/*.jsonl           # real recordings (small, landmarks only)
└── test_architecture.py       # core import ban; no imwrite/socket in src
```

**Structure Decision**: single `src/` package. `spikes/feasibility/` is not imported (CLAUDE.md).
Code may be re-derived from the spike but is rewritten with tests.

## Phase 2 Hardening Items (spec FR-033–FR-038, SC-011–SC-013)

H1–H6 map to FR-033–FR-038. They are checked in the same manual session.

| ID | Requirement | Acceptance |
|---|---|---|
| H1 | Primary-hand lock survives a second hand/person (D9) | Replay: a second synthetic hand moving or pinching produces 0 actions. Real "second person" recording: 0 actions from the non-primary hand. |
| H2 | Camera interruption: unplug or another app takes it → "Camera unavailable" ≤ 1 s, RA, automatic recovery (D11) | Manual: unplug/replug, and open the Windows Camera app during Active. Unit: fake capture. |
| H3 | Uncertain tracking: low confidence or a landmark jump → no action, the cursor holds (D10) | Replay: injected low-confidence and jump frames during a pinch/drag → no click, the drag is released after the loss window. |
| H4 | False-trigger benchmark (D18) | ≥ 10 min of real idle + typing + talking recordings → 0 consequential actions (SC-004). |
| H5 | Tune all provisional safety values (D19) | `safety-policy.md` has no *(provisional)* marks; the defaults match it. |
| H6 | Refine activation/pause from Phase 1 use | Retrospective notes the changes; SC-001 is met. |

## Replay Test Coverage (FR-030 / SC-009)

Each row is at least one replay test:
- **Each transition in the Pointer subset of the matrix**: E2–E11, E15–E17 for every implemented
  state.
- **Each gesture behavior**:
  - move
  - clamp at the edges
  - click
  - double-click
  - right-click + cooldown
  - pinch flicker → nothing
  - drag + release
  - drag + loss → ButtonUp, no re-press
  - scroll up/down
  - repeated strokes
  - still hand → no scroll
  - clutch
  - pause hold
  - G7 → nothing
- **Each edge case in the spec**: single-frame flicker, low confidence, second hand, emergency
  stop during a drag, hotkey not registered → Resume refused, and settings reload during a drag →
  RA.
- **Determinism**: every replay is run twice, and the event lists must be equal.

## Validation (one manual session, after implementation)

Run in the user's PowerShell venv:

```powershell
python -m pip install -e ".[dev]"; .\scripts\fetch_model.ps1
ruff check .; mypy src/gescrtl/core; pytest
python -m gescrtl                       # live use
python -m gescrtl --record idle         # also: typing, talking, second-person, demo
python -m gescrtl.tools.bench --replay recordings\*.jsonl
python -m gescrtl.tools.bench --live 60
```

Session checklist:
- US1–US4 acceptance scenarios
- SC-002 task set, timed
- SC-005 48 px target clicks
- SC-006 stop/pause/loss timings
- SC-007 at 100/125/150% scaling
- SC-008 idle CPU
- H2 unplug and Camera-app tests
- SC-010: check `recordings/` holds only `.jsonl`, and run `Get-NetTCPConnection -OwningProcess`
  during the session to confirm there are no connections

Results go to `docs/measurements/phase1-2-report.md` along with a short retrospective.

## Complexity Tracking

| Deviation | Why | Simpler alternative rejected because |
|---|---|---|
| ModeMenuOpen state and E12–E14 from the interaction model are not implemented | Spec FR-016: the mode system belongs to spec 003 | Implementing a menu with only one usable mode adds untested UI with no user value |
| Recording format bumped to v2 (command lines) | Hotkey/tray/camera events must be replayable for transition tests | v1 frame-only recordings cannot reproduce pause/stop/camera transitions |

## Implementation notes (deviations found while building T001–T026)

- **Mirroring**: the tracker adapter mirrors the image, so core landmarks are already in the user's view; the engine has no `mirrored` flag. `HandFrame` carries `aspect` (width/height) because distances must be measured in aspect-corrected space.
- **Pose priority**: a pinch is tested *before* a fist, with a guard that the pinching fingertip is not curled into the palm. Reason: in the Phase 0 recording the user's natural pinch has the other three fingers curled (tip/pip 0.7–0.85), so fist-first would turn clicks into clutches. The guard and the fist/open thresholds are checked on real fist data in the manual session (T055).
- **Cursor freeze (D5)**: the cursor freezes at the first *raw* pinch frame (position `pinch_lookback_frames` earlier), not at the stable onset, and stays frozen for `click_stabilize_ms` after release. `double_click_dist` is a config value (0.02 of the screen); only the double-click *time* comes from the OS.
- **Smoothing units**: One Euro runs on camera-normalized palm coordinates, as in the Phase 0 spike, so `beta = 0.007` is nearly inert there. Revisit in T051 if the cursor feels laggy.
- **Commands**: added `TOGGLE_PAUSE`, `TOGGLE_POWER` and `EXIT`; settings reload is `Engine.apply_config()` instead of a command. `Engine.start()` and `Engine.tick()` were added (initial HUD events; the "Stopped" display timer).
- **Resume re-arming**: after any pause or stop the open-palm resume only counts once the hand has shown another pose or been absent for the loss window, so pausing with an open hand cannot resume itself.
- **Primary hand** (T047's core logic) already lives in `core/primary_hand.py`; T045, T046 and the remaining T047 checks are still open.
- **Gesture change after the first live test**: two-finger scroll was confused with pinching (forming it can put the thumb against the middle finger, which risks a stray right click). Scroll is now **thumbs-up** (G4) and clutch is the **flat hand** (G8). The fist (G5) no longer clutches; it freezes the cursor and, held 1.5 s, pauses, which keeps a gesture path to stop (constitution I). Thumb "out" is measured from the palm center (0.68 hand sizes), and a thumbs-up also needs the thumb tip more than 0.8 hand sizes from the index fingertip; on the Phase 0 recording this rule produced no false thumbs-up in 1031 natural frames.
- **Camera preview** (`platform/preview.py`, tray item or `--preview`): opt-in mirrored live view with the tracked hand, the cursor-area box and a pose readout. It shows frames on screen only. While it is open, Paused tracks every frame instead of every third. Keys: `S` skeleton on/off, `D` readout on/off.
- **Live tuning flags** until the settings file exists (T039): `--region`, `--min-cutoff`, `--beta`.
- **Pause gesture moved to the flat hand** (held 1.5 s) after the second live test; the fist only freezes the cursor.
- **Scroll is now rate control by thumb tilt** (third live test): hand-travel scrolling was awkward. See D6 and spec FR-014. The tilt filter restarts on the first raw G4 frame; without that, the start angle carried a ~2.5 deg error that, through the dead zone and the 1.5 power curve, made up and down scroll speeds differ by about 40%.
- Live tuning flags added: `--scroll-rate`, `--scroll-deadzone`.
