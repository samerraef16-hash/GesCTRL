# ADR 0002: Method of sending input

- **Status**: Accepted (inject timing measured 2026-10-10)
- **Date**: 2026-10-10
- **Related**: spec FR-014, research R2

## Context
GesCRTL must move the cursor, and later click, scroll, and press keys, with explicit up/down events
so that ReleaseAll is possible, at low latency and with correct display scaling.

## Options Considered
1. **Win32 `SendInput` via `ctypes`**: supported, fast, absolute virtual-desktop positioning, buttons/wheel/keys with explicit up/down, no extra dependency.
2. **`pyautogui`**: default 0.1 s pause per call and a corner fail-safe that conflicts with our safety model.
3. **`pynput`**: workable, but adds a dependency and hides details we need to control.
4. **`mouse_event`**: superseded by `SendInput`.

## Decision
Use `SendInput` with `MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK` and
coordinates normalized to 0–65535, with per-monitor-v2 DPI awareness set at startup.

## Evidence
The `winput.py` self-check on the author's machine passed (per-monitor-v2 DPI, cursor moved to the
screen center within 2 px, primary 1920×1080). Inject p95: 0.41 ms (max 1.2 ms) during the 60 s pointing run (`docs/measurements/feasibility-report.md`). In `spike.py` the real cursor followed the hand with no errors and no visible jitter; it reached all four screen corners.

## Consequences
- Windows blocks input into elevated windows (UIPI) unless GesCRTL is elevated or has `uiAccess`
  (signed binary installed in Program Files).
- The secure desktop (UAC prompts, lock screen, Ctrl+Alt+Del) is unreachable.
- All Win32 code lives in one module so other platforms need only a new adapter.
