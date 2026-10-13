# GesCRTL

Webcam hand-gesture control for Windows (mouse, keyboard, presentation, media). Portfolio
project on GitHub, run from source; not distributed as an installed product.

## Where things are

- `Plan.md`: roadmap and spec grouping (§3). `.specify/memory/constitution.md`: rules (v1.3.0).
- `docs/interaction/`: interaction model (states, events), gestures G1–G7, safety policy, HUD.
- `docs/adr/`: decisions. `docs/measurements/feasibility-report.md`: measured numbers.
- `specs/NNN-*/`: one folder per spec. Active spec is in `.specify/feature.json`.
- `spikes/feasibility/`: throwaway Phase 0 spike. Never import it from `src/`; Phase 1 starts fresh.

## Workflow (lean, from Phase 1 on)

- specify → plan (`plan.md` only) → tasks (short) → implement → one manual test session.
- Clarify only if more than 3 open questions. No extra research/data-model/contract files unless needed.
- Code and tests are the record. Keep documents short. Don't re-read large docs unless needed.

## Non-negotiables

- Safety: confidence + stable frames before any click/key; hysteresis and cooldowns;
  ReleaseAll on pause, loss, mode change, exit, or exception; emergency stop `Ctrl+Alt+Esc`
  (goes to Paused); one primary hand only (exception: Keyboard Mode may take a second, same-person
  hand that types with its own pointer and pinch, and nothing else; constitution v1.3.0,
  ADR 0007).
- Testable core: everything after tracking is pure logic (landmark frames + injected clock → events),
  covered by landmark-replay tests (JSONL). Platform code (SendInput, DPI, hotkeys, overlay) lives
  behind interfaces in `platform/`; core never imports it.
- Privacy: frames stay in memory; never write images; no network at runtime.

## Measured baseline (Phase 0, author's laptop)

~30 FPS (camera limit), internal delay p95 32 ms, absolute mapping (central 60% region),
palm-center anchor, One Euro 1.0 / 0.007, loss window 3 frames, Paused at 10 FPS, idle CPU
budget ≤ 5%. Dim light drops the camera to ~10 FPS. Small (24 px) targets are hard: design for ≥ 48 px.

## Stack and environment

Python 3.12, MediaPipe Hand Landmarker (Tasks API, VIDEO mode), OpenCV (DirectShow + MJPG works
on this camera), Win32 `SendInput` via ctypes, PySide6 HUD, Pydantic settings, pytest, Ruff.
Windows 11. The user runs camera/human steps in a separate PowerShell terminal with a venv;
give them exact PowerShell commands. Commit only when asked.
