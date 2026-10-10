# ADR 0003: On-screen indicator (HUD) approach

- **Status**: Proposed
- **Date**: 2026-10-10
- **Related**: spec FR-014, FR-011, research R3

## Context
The indicator must be always on top, never take focus, never block clicks, and also provide a tray
icon and, later, a settings UI and mode menu.

## Options Considered
1. **PySide6 (Qt)** frameless always-on-top tool window with click-through styles, plus `QSystemTrayIcon`: one toolkit for HUD, tray, settings, and menu; cross-platform.
2. **Tkinter**: weak transparency and click-through support.
3. **Raw Win32 layered window**: maximum control, high effort, no reusable UI.
4. **Electron / web overlay**: heavy runtime and extra latency.

## Decision
Use PySide6 with `Qt.WindowTransparentForInput`, `WindowStaysOnTopHint`, `Tool`, and
`WA_ShowWithoutActivating`.

## Evidence
Comparison only (research R3); overlay check pending in Phase 1 (`spikes/feasibility/overlay_check.py`
is ready but not yet run on a machine with PySide6).

## Consequences
Adds a Qt dependency to the product and the packaging step. Revisit if click-through or focus
behavior fails the overlay check.
